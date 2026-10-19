"""
biblioteca_mcp.py — tutte le skill (dell'utente e dei plugin di Claude Code) a costo di contesto quasi zero.

Il modello non si porta dietro 132 descrizioni (~9.500 token): chiama skill_cerca(compito).
  1. BM25 sulle descrizioni trova ~15 candidate;
  2. Kev (modello decisionale, /v1/systemone, ~0,3 s) sceglie la migliore o "nessuna";
  3. torna il testo della skill scelta (piu' l'elenco dei suoi file di supporto).
Senza Kev acceso usa solo BM25 (con una soglia).

Uso: python extras/biblioteca_mcp.py   (server MCP stdio)   |   python extras/biblioteca_mcp.py prova "testo"
"""
from __future__ import annotations
import json, math, os, re, sys, urllib.request
from collections import Counter
from pathlib import Path

_H = Path.home()
RADICI = [Path(__file__).resolve().parent.parent / "opencode" / ".opencode" / "skills",   # le nostre (vincono)
          _H / ".claude" / "skills", _H / ".claude" / "plugins",                           # skill di Claude Code
          _H / ".config" / "opencode" / "skills"]                                         # skill globali OpenCode
RADICI += [Path(p) for p in os.environ.get("BIBLIOTECA_RADICI", "").split(";") if p.strip()]  # cartelle tue in piu'
KEV = os.environ.get("KEV_URL", "http://127.0.0.1:9931")
MAX_TESTO = 12000  # caratteri restituiti al massimo (le skill lunghe rimandano ai loro file)


def _indice():
    skill = {}
    for radice in RADICI:
        for p in radice.rglob("SKILL.md") if radice.exists() else []:
            t = p.read_text(encoding="utf-8", errors="ignore")
            fm = t.split("---")[1] if t.startswith("---") and t.count("---") >= 2 else ""
            n = re.search(r"^name:\s*(.+)$", fm, re.M)
            d = re.search(r"^description:\s*(.+(?:\n[ \t]+.+)*)", fm, re.M)
            nome = (n.group(1).strip().strip('"') if n else p.parent.name)
            desc = re.sub(r"\s+", " ", d.group(1)).strip().strip('"').lstrip(">-| ") if d else ""
            skill.setdefault(nome, {"nome": nome, "descrizione": desc[:600], "percorso": str(p)})
    return list(skill.values())


SKILL = _indice()
_TOK = lambda s: re.findall(r"[a-z0-9àèéìòù]{2,}", s.lower())
_DOCS = [_TOK(s["nome"].replace("-", " ") + " " + s["descrizione"]) for s in SKILL]
_DF = Counter(w for d in _DOCS for w in set(d))
_AVG = sum(map(len, _DOCS)) / max(len(_DOCS), 1)


def _bm25(q, k1=1.5, b=0.75):
    qt, N, out = _TOK(q), len(_DOCS), []
    for i, d in enumerate(_DOCS):
        tf, s = Counter(d), 0.0
        for w in qt:
            if tf[w]:
                idf = math.log(1 + (N - _DF[w] + 0.5) / (_DF[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / _AVG))
        out.append((s, i))
    return sorted(out, reverse=True)


def _kev(compito, candidati):
    crit = {SKILL[i]["nome"]: SKILL[i]["descrizione"][:300] for _, i in candidati}
    crit["nessuna"] = "nessuna di queste skill serve davvero per questo compito"
    body = {"state": f"Compito: {compito[:1500]}",
            "questions": {"q": {"type": "choice", "instructions": "Which skill is the right one for this task?",
                                "criteria": crit}}}
    req = urllib.request.Request(f"{KEV}/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    a = json.load(urllib.request.urlopen(req, timeout=20))["answers"]["q"]
    return a["choice"], float(a["confidence"])


def cerca(compito: str, n: int = 15):
    cand = [(s, i) for s, i in _bm25(compito)[:n] if s > 0]
    if not cand:
        return None, 0.0, "bm25"
    try:
        scelta, fid = _kev(compito, cand)
        return (None if scelta == "nessuna" else scelta), fid, "kev"
    except Exception:
        s, i = cand[0]
        return (SKILL[i]["nome"] if s >= 4.0 else None), s, "bm25"


ADATTATE = Path(__file__).resolve().parent.parent / "skill_adattate"   # versioni scritte da Qwen per se'


def _impronta(p):
    import hashlib
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()[:12]


def _adattata(nome):
    """La versione adattata vale solo se l'originale non e' cambiato dopo (impronta uguale)."""
    s = next(x for x in SKILL if x["nome"] == nome)
    a = ADATTATE / nome / "SKILL.md"
    if a.exists() and f"origine_impronta: {_impronta(s['percorso'])}" in a.read_text(encoding="utf-8", errors="ignore"):
        return a.read_text(encoding="utf-8", errors="ignore")
    return None


def _testo(nome):
    s = next(x for x in SKILL if x["nome"] == nome)
    p = Path(s["percorso"])
    mia = _adattata(nome)
    if mia:
        return f"SKILL {nome} (TUA versione adattata; originale in {p.parent})\n\n{mia}"
    t = p.read_text(encoding="utf-8", errors="ignore")
    altri = [str(f.relative_to(p.parent)) for f in p.parent.rglob("*") if f.is_file() and f.name != "SKILL.md"][:40]
    if len(t) > MAX_TESTO:
        t = t[:MAX_TESTO] + "\n[... skill troncata: leggi il resto dal file]"
    return (f"SKILL {nome}  (cartella: {p.parent})\n" + (f"file di supporto: {', '.join(altri)}\n" if altri else "") + "\n" + t
            + f"\n\n[Dopo averla usata: segui la skill `adatta-skill` e salva la tua versione con skill_salva_adattata(\"{nome}\", testo).]")


if len(sys.argv) > 2 and sys.argv[1] == "prova":
    print(len(SKILL), "skill indicizzate")
    print(cerca(" ".join(sys.argv[2:])))
    sys.exit()

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("biblioteca")


@mcp.tool()
def skill_cerca(compito: str) -> str:
    """Trova la skill giusta per il compito tra tutte quelle disponibili (~130: design web, animazioni, video,
    SEO, Cloudflare, sviluppo plugin, revisione codice...) e ne restituisce le istruzioni complete.
    Usala all'inizio di ogni compito non banale. Puo' rispondere che nessuna skill serve."""
    nome, fid, via = cerca(compito)
    if not nome:
        return "Nessuna skill adatta: procedi con le tue capacita'."
    return _testo(nome) + f"\n\n[scelta da {via}, fiducia {fid:.2f}]"


@mcp.tool()
def skill_salva_adattata(nome: str, testo: str) -> str:
    """Salva la TUA versione adattata di una skill (scritta seguendo la skill `adatta-skill`): inglese compatto,
    solo strumenti che hai davvero, con un passo di verifica. La prossima volta skill_cerca ti dara' questa."""
    s = next((x for x in SKILL if x["nome"] == nome), None)
    if s is None:
        return f"Skill '{nome}' sconosciuta: usa il nome esatto restituito da skill_cerca."
    if len(testo) < 200 or len(testo) > 8000:
        return "NON SALVATA: la versione adattata deve essere tra 200 e 8000 caratteri."
    d = ADATTATE / nome
    d.mkdir(parents=True, exist_ok=True)
    intest = (f"---\nname: {nome}\ndescription: {s['descrizione'][:300]}\nmetadata:\n  origine: {s['percorso']}\n"
              f"  origine_impronta: {_impronta(s['percorso'])}\n  adattata_da: qwen-locale\n---\n")
    (d / "SKILL.md").write_text(intest + testo.strip() + "\n", encoding="utf-8")
    return f"SALVATA: {d / 'SKILL.md'} ({len(testo)} caratteri, originale {Path(s['percorso']).stat().st_size} byte)."


@mcp.tool()
def skill_elenco(filtro: str = "") -> str:
    """Elenco dei nomi delle skill (opzionale: solo quelle che contengono `filtro`)."""
    nomi = sorted(s["nome"] for s in SKILL if filtro.lower() in (s["nome"] + s["descrizione"]).lower())
    return f"{len(nomi)} skill: " + ", ".join(nomi)


if __name__ == "__main__":
    mcp.run()
