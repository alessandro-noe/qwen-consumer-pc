"""
kael_mcp.py — il livello NOSTRO sopra il modello locale, come server MCP (stdio).

Tre idee del progetto agente-locale, in codice deterministico (il modello non decide da solo):
  1. MEMORIA DEGLI ERRORI VERIFICATI (RAG): un errore entra in memoria SOLO se il comando
     di test che dimostra la correzione passa davvero. Niente "ricordi" non provati.
  2. VERIFICA: i test decidono se un lavoro e' finito, non il modello.
  3. FRENO ANTI-LOOP (regola di Kael): lo stesso errore 3 volte di fila -> STOP, chiedi all'umano.

Strumenti: memoria_cerca, memoria_salva, verifica, regole.
Uso con OpenCode/Claude/qualsiasi client MCP:  python extras/kael_mcp.py
"""
from __future__ import annotations
import hashlib, json, math, re, subprocess, time
from collections import Counter
from pathlib import Path
from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
MEM = HERE / "memoria" / "errori.jsonl"
MEM.parent.mkdir(exist_ok=True)
STOP_DOPO = 3
mcp = FastMCP("kael")
_ultimi: dict[str, tuple[str, int]] = {}      # cartella -> (impronta ultimo errore, quante volte di fila)

REGOLE = """REGOLE (obbligatorie):
1. Prima di correggere un errore, chiama memoria_cerca con il messaggio d'errore: forse e' gia' stato risolto.
2. Non dire mai "fatto": chiama verifica con il comando dei test. Il lavoro e' finito solo se verifica dice PASSA.
3. Se verifica risponde STOP, fermati e chiedi all'umano: hai ripetuto lo stesso errore 3 volte.
4. Quando risolvi un errore non banale, chiama memoria_salva con il comando di test che lo dimostra."""


def _parole(t: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", t.lower())


def _carica() -> list[dict]:
    if not MEM.exists():
        return []
    return [json.loads(l) for l in MEM.read_text(encoding="utf-8").splitlines() if l.strip()]


def _esegui(comando: str, cartella: str, timeout: int = 180):
    try:
        p = subprocess.run(comando, shell=True, cwd=cartella or None, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout + "\n" + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT dopo {timeout}s"


@mcp.tool()
def regole() -> str:
    """Le regole di lavoro da seguire sempre. Leggile all'inizio di ogni compito."""
    return REGOLE


def _firma(testo: str) -> dict:
    """Firma di un errore: tipi di eccezione, file .py e funzioni citate nel traceback."""
    return {
        "eccezioni": set(re.findall(r"\b([A-Z]\w*(?:Error|Exception|Exit|Interrupt))\b", testo)),
        "file": {f.replace("\\", "/").split("/")[-1] for f in re.findall(r"[\w./\\-]+\.py", testo)},
        "funzioni": set(re.findall(r"\bin (\w+)\b", testo)) - {"module"},
    }


SOGLIA = 0.45          # cancello: sotto questa pertinenza Kael si astiene


@mcp.tool()
def memoria_cerca(problema: str, k: int = 3, riverifica: bool = False) -> str:
    """Cerca nella memoria degli errori GIA' RISOLTI E VERIFICATI quelli PERTINENTI a `problema`
    (meglio se con il messaggio d'errore / traceback). Tre stadi:
      1. candidati per parole (BM25);
      2. RIORDINO per firma dell'errore (stesso tipo di eccezione, stesso file, stessa funzione);
      3. CANCELLO: se nessun candidato e' abbastanza pertinente, risponde che non c'e' niente
         (meglio nessun ricordo che un ricordo sbagliato).
    Con riverifica=True riesegue il test di ogni ricordo proposto e scarta quelli che non passano piu'."""
    voci = _carica()
    if not voci:
        return "Memoria vuota: nessun errore verificato salvato finora."
    ris = _cerca(voci, problema, k)
    if not ris:
        return "Nessun errore verificato PERTINENTE in memoria (cancello: pertinenza sotto soglia). Procedi senza ricordi."
    out = []
    for p, i, motivi in ris:
        v = voci[i]
        stato = ""
        if riverifica:
            code, _ = _esegui(v["comando_test"], v.get("cartella", ""))
            if code != 0:
                out.append(f"- (scartato: il test del ricordo '{v['problema'][:60]}' non passa piu', exit {code})")
                continue
            stato = ", riverificato ora"
        out.append(f"- PROBLEMA: {v['problema']}\n  CAUSA: {v['causa']}\n  SOLUZIONE: {v['soluzione']}\n"
                   f"  (pertinenza {p:.2f}: {motivi}; verificato con `{v['comando_test']}` il {v['data']}{stato})")
    return "\n".join(out)


def _cerca(voci: list, problema: str, k: int):
    """-> [(pertinenza 0..1, indice, motivi)] dopo BM25 + riordino per firma + cancello."""
    docs = [Counter(_parole(v["problema"] + " " + v["causa"])) for v in voci]
    docs = [Counter(_parole(v["problema"] + " " + v["causa"])) for v in voci]
    N = len(docs); avgdl = sum(sum(d.values()) for d in docs) / N
    df = Counter(w for d in docs for w in d)
    q = _parole(problema)
    def bm25(d):
        dl = sum(d.values()); s = 0.0
        for w in q:
            if w in d:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * d[w] * 2.2 / (d[w] + 1.2 * (0.25 + 0.75 * dl / avgdl))
        return s
    grezzi = [(bm25(d), i) for i, d in enumerate(docs)]
    massimo = max(s for s, _ in grezzi) or 1.0
    fq = _firma(problema)
    ris = []
    for s, i in sorted(grezzi, reverse=True)[:max(k * 4, 10)]:
        if s <= 0:
            continue
        fv = _firma(voci[i]["problema"] + " " + voci[i]["causa"])
        p, motivi = 0.5 * s / massimo, [f"parole {s / massimo:.2f}"]
        for chiave, peso in (("eccezioni", 0.3), ("file", 0.1), ("funzioni", 0.1)):
            if fq[chiave] and fv[chiave]:
                if fq[chiave] & fv[chiave]:
                    p += peso; motivi.append({"eccezioni": "stessa eccezione", "file": "stesso file", "funzioni": "stessa funzione"}[chiave])
                elif chiave == "eccezioni":
                    p -= 0.3; motivi.append("eccezione diversa")
        if p >= SOGLIA:
            ris.append((min(p, 1.0), i, ", ".join(motivi)))
    return sorted(ris, reverse=True)[:k]


@mcp.tool()
def memoria_salva(problema: str, causa: str, soluzione: str, comando_test: str, cartella: str = "") -> str:
    """Salva un errore risolto nella memoria (scrivi problema/causa/soluzione in inglese compatto, `chiave: valore`).
    Il server ESEGUE `comando_test` in `cartella`:
    la voce viene salvata solo se il test passa (memoria di soli errori verificati)."""
    code, out = _esegui(comando_test, cartella)
    if code != 0:
        return f"NON SALVATO: il test non passa (exit {code}). Una memoria non verificata non entra.\n{out[-800:]}"
    voce = {"problema": problema, "causa": causa, "soluzione": soluzione, "comando_test": comando_test,
            "cartella": cartella, "data": time.strftime("%Y-%m-%d %H:%M")}
    with MEM.open("a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    return f"SALVATO e verificato (test passato). Voci in memoria: {len(_carica())}."


@mcp.tool()
def verifica(comando: str, cartella: str = "") -> str:
    """Esegue i test (`comando`, es. 'python -m pytest -q') in `cartella` e dice se il lavoro e' finito.
    Risponde PASSA, FALLISCE (con l'output) oppure STOP se lo stesso errore si ripete 3 volte di fila."""
    code, out = _esegui(comando, cartella)
    if code == 0:
        _ultimi.pop(cartella, None)
        return f"PASSA (exit 0). Il lavoro e' verificato.\n{out[-400:]}"
    coda = "\n".join(out.splitlines()[-3:])
    impronta = hashlib.sha1(re.sub(r"0x[0-9a-f]+|\d+\.\d+s", "", coda).encode()).hexdigest()[:12]
    prima, volte = _ultimi.get(cartella, ("", 0))
    volte = volte + 1 if impronta == prima else 1
    _ultimi[cartella] = (impronta, volte)
    if volte >= STOP_DOPO:
        return (f"STOP: lo stesso errore si e' ripetuto {volte} volte di fila. Fermati e chiedi all'umano "
                f"invece di riprovare uguale.\n{out[-800:]}")
    return (f"FALLISCE (exit {code}, stesso errore {volte}/{STOP_DOPO}). Cerca prima in memoria_cerca "
            f"con questo errore.\n{out[-1500:]}")


if __name__ == "__main__":
    mcp.run()
