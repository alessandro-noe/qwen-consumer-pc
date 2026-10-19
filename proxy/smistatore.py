"""
smistatore.py — il modello DECISIONALE (Kev-4B) davanti a Qwen.

OpenCode -> smistatore (8091) -> llama-server Qwen (8090)
                 |
                 +-> Kev (9931, /v1/systemone): quale strada per questa richiesta?

Per ogni NUOVA richiesta dell'utente (ultimo messaggio = user):
  - Kev sceglie la strada tra 8 (descrizioni sempre date: senza, -30/-50 punti di precisione).
  - fiducia >= SOGLIA:
      risposta  -> Qwen risponde SENZA ragionamento (enable_thinking=false): il risparmio vero
      altre     -> nota breve in coda al messaggio: quale agente / skill usare
  - fiducia bassa o Kev spento -> passa tutto invariato (decide Qwen).
La nota viene riattaccata IDENTICA a ogni richiesta successiva: il prefisso resta uguale e la cache di
llama.cpp non si rompe. Il proxy non esegue mai azioni: decide solo come chiedere a Qwen.

Uso: python proxy/smistatore.py     (variabili: QWEN_URL, KEV_URL, SMISTA_SOGLIA, SMISTA_PORTA)
"""
import hashlib, json, os, re, sys, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

QWEN = os.environ.get("QWEN_URL", "http://127.0.0.1:8090")
KEV = os.environ.get("KEV_URL", "http://127.0.0.1:9931")
SOGLIA = float(os.environ.get("SMISTA_SOGLIA", "0.30"))
PORTA = int(os.environ.get("SMISTA_PORTA", "8091"))
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memoria", "smistatore.log")

ROTTE = {
    "risposta": "rispondi subito con quello che sai, senza strumenti",
    "codice": "scrivi o modifica codice nel progetto",
    "debug": "trova e correggi un errore, un crash o un test che fallisce",
    "esplora": "capire come funziona un progetto o dove sta qualcosa nel codice",
    "web": "cercare informazioni aggiornate su internet",
    "file": "gestire file e cartelle sul PC: spostare, rinominare, cercare, organizzare",
    "browser": "fare azioni su un sito web: cliccare, compilare moduli, navigare",
    "piano": "compito lungo con molti passi che va prima pianificato",
}
NOTE = {
    "risposta": "rispondi direttamente, senza strumenti.",
    "codice": "usa la skill cerca-prima, poi scrivi, poi la skill verifica.",
    "debug": "usa l'agente correttore: prima kael.memoria_cerca, poi kael.verifica.",
    "esplora": "usa l'agente esploratore e graphify prima di leggere i file.",
    "web": "serve un'informazione aggiornata: cercala, non rispondere a memoria.",
    "file": "operazioni su file: mostra cosa farai prima; niente cancellazioni senza conferma.",
    "browser": "azioni su un sito: ogni invio, pagamento o cancellazione chiede conferma all'utente.",
    "piano": "compito lungo: usa prima l'agente pianificatore.",
}
note_fissate = {}  # hash del testo utente -> nota (riattaccata identica: cache di llama.cpp intatta)
SCALATA = os.environ.get("SMISTA_SCALATA") == "1"
CON_NOTE = os.environ.get("SMISTA_NOTE", "1") == "1"
K_FILE = os.environ.get("SMISTA_K_FILE")          # stesso percorso di MOE_ESEC_FILE del motore
K_VELOCE = int(os.environ.get("SMISTA_K_VELOCE", "6"))


def scrivi_k(k):
    tmp = K_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(k))
    os.replace(tmp, K_FILE)  # il motore legge sempre un file completo
SCALA_DOPO = int(os.environ.get("SMISTA_SCALA_DOPO", "2"))
# segnali di fallimento VERI: banco ([exit=N]), Kael, Python, PowerShell (anche in italiano), npm/pip, test, HTTP.
# Tarati sui 126 comandi reali di una sessione OpenCode: 30 riconosciuti contro 27 con exit != 0 (il vecchio ne vedeva 7).
FALLITO = re.compile(r"\[exit=[1-9]|FALLISCE|STOP:|Traceback \(most recent call last\)"
                     r"|FullyQualifiedErrorId|\+ CategoryInfo|CommandNotFoundException|ParameterBindingException"
                     r"|non .{0,3}riconosciuto come nome|is not recognized as (the name|an internal)"
                     r"|^(ERROR|Error|error)(:| \d)|npm ERR!|\b[1-9]\d* failed\b|FAILED \(|exit code:? ?[1-9]|Exit code: [1-9]"
                     r"|No matching distribution|Could not find a version|\(404\)|404 Not Found", re.M)
stato_scalata = {}


def testo(m):
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def chiave(t):
    return hashlib.sha1(t.encode("utf-8", "ignore")).hexdigest()


def attacca(m, nota):
    agg = f"\n\n[smistatore: {nota}]"
    if isinstance(m.get("content"), list):
        m["content"] = m["content"] + [{"type": "text", "text": agg}]
    else:
        m["content"] = (m.get("content") or "") + agg


def chiedi_kev(richiesta):
    body = {"state": f"Richiesta dell'utente: {richiesta[-2000:]}",
            "questions": {"q": {"type": "choice", "instructions": "Quale strada deve prendere l'agente per questa richiesta?",
                                "criteria": ROTTE}}}
    req = urllib.request.Request(f"{KEV}/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    a = json.load(urllib.request.urlopen(req, timeout=10))["answers"]["q"]
    return a["choice"], float(a["confidence"])


def registra(**kv):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), **kv}, ensure_ascii=False) + "\n")
    except OSError:
        pass


GUARDIA = os.environ.get("SMISTA_GUARDIA", "1") == "1"
PASSATO = re.compile(r"PASSA \(exit 0\)|^(?![^\n]*failed)[^\n]*\b\d+ passed\b|^OK\s*$", re.M)
RICERCA = {"websearch", "webfetch", "web_search", "web_fetch"}
SCRITTURA = {"write_file", "write", "edit", "patch", "apply_patch", "multiedit"}


def guardia(msgs):
    """Guardiano del turno corrente (idee da Hermes Agent, MIT): (1) dopo una verifica superata senza modifiche
    successive suggerisce di chiudere; (2) la stessa chiamata ripetuta senza modifiche in mezzo -> avviso alla 3a,
    stop alla 5a. Le note dipendono solo dai messaggi, quindi si riattaccano identiche: la cache resta valida."""
    ultimo_user = max((i for i, m in enumerate(msgs) if m.get("role") == "user"), default=-1)
    risultati = {m.get("tool_call_id"): m for m in msgs[ultimo_user + 1:] if m.get("role") == "tool"}
    conta, ricerche = {}, 0
    for m in msgs[ultimo_user + 1:]:
        if m.get("role") != "assistant":
            continue
        for c in m.get("tool_calls") or []:
            f = c.get("function", {}) if isinstance(c, dict) else {}
            nome, args = f.get("name", ""), f.get("arguments", "")
            ris = risultati.get(c.get("id"))
            if nome in SCRITTURA:
                conta, ricerche = {}, 0  # una modifica azzera: ripetere i test dopo un cambio e' lavoro vero
                continue
            ricerche = ricerche + 1 if nome in RICERCA else 0
            if ricerche in (8, 15) and ris is not None:  # ricerche a raffica senza agire (visto nell'uso vero: ~25 di fila)
                attacca(ris, f"{ricerche} ricerche web di fila senza agire: fermati, riassumi cosa hai trovato e prova la "
                             "strada piu' promettente, oppure chiedi all'utente")
            firma = nome + "|" + (args if isinstance(args, str) else json.dumps(args, sort_keys=True))
            conta[firma] = conta.get(firma, 0) + 1
            if ris is None:
                continue
            if conta[firma] == 3:
                attacca(ris, f"hai gia' fatto questa stessa chiamata ({nome}) 3 volte senza modifiche in mezzo: cambia strategia")
            elif conta[firma] >= 5:
                attacca(ris, "STOP: chiamata ripetuta 5 volte. Fermati e riassumi all'utente cosa hai provato e cosa manca")
            if PASSATO.search(testo(ris)):  # dipende solo da questo messaggio: la nota resta identica (cache ok)
                attacca(ris, "verifica superata. Se il compito richiesto e' completo, dai ORA la risposta finale: "
                             "niente altre verifiche, controlli o pulizie")


def smista(dati):
    msgs = dati.get("messages") or []
    if msgs and msgs[-1].get("role") == "user":
        t = testo(msgs[-1])
        k = chiave(t)
        if k not in note_fissate and t.strip():
            t0 = time.time()
            try:
                strada, fid = chiedi_kev(t)
            except Exception as e:  # Kev spento o errore: nessun intervento
                registra(errore=str(e)[:200])
                strada, fid = None, 0.0
            ms = round(1000 * (time.time() - t0))
            nota = NOTE[strada] if strada in NOTE and fid >= SOGLIA else None
            if nota and strada != "risposta" and not CON_NOTE:  # nel banco le note sui compiti hanno fatto danno
                nota = None
            note_fissate[k] = (strada, nota)
            registra(strada=strada, fiducia=round(fid, 2), ms=ms, applicata=bool(nota), richiesta=t[:120])
        strada, nota = note_fissate.get(k, (None, None))
        if strada == "risposta" and nota:
            dati.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
    if SCALATA and msgs and "enable_thinking" not in dati.get("chat_template_kwargs", {}):
        # scalata: dentro un compito Qwen parte SENZA ragionamento; dopo SCALA_DOPO fallimenti verificati
        # (test/esecuzione) nel turno corrente lo accende. Il segnale viene dai risultati veri, non dal modello.
        ultimo_user = max((i for i, m in enumerate(msgs) if m.get("role") == "user"), default=-1)
        falliti = sum(1 for m in msgs[ultimo_user + 1:] if m.get("role") == "tool" and FALLITO.search(testo(m)))
        acceso = falliti >= SCALA_DOPO
        dati.setdefault("chat_template_kwargs", {})["enable_thinking"] = acceso
        if acceso != stato_scalata.get(ultimo_user):
            stato_scalata[ultimo_user] = acceso
            registra(scalata="ragionamento acceso" if acceso else "veloce", falliti=falliti)
    if K_FILE and msgs:
        # scalata degli ESPERTI (motore nostro, MOE_ESEC_FILE): K veloce finche' non c'e' un fallimento vero,
        # poi tutti gli esperti; al secondo fallimento si accende anche il ragionamento (sopra)
        ultimo_user = max((i for i, m in enumerate(msgs) if m.get("role") == "user"), default=-1)
        falliti = sum(1 for m in msgs[ultimo_user + 1:] if m.get("role") == "tool" and FALLITO.search(testo(m)))
        scrivi_k(K_VELOCE if falliti == 0 else 0)
    if GUARDIA and msgs:
        guardia(msgs)
    for m in msgs:  # riattacca le note identiche su tutta la conversazione
        if m.get("role") == "user":
            s = note_fissate.get(chiave(testo(m)))
            if s and s[1]:
                attacca(m, s[1])
    return dati


# --- scambio automatico del modello (stile llama-swap): un nome nella lista -> un file GGUF; acceso uno alla volta
RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELLI = {
    "flashnext-uncensored": r"models\flashnext_q2_0_abl\Q2_0\Qwen3.8-Flash-Next-GSQ-RCO-abliterated-Q2_0-00001-of-00002.gguf",
    "flashnext-normale": r"models\flashnext_q2_0\Q2_0\Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf",
}
SERVER = os.environ.get("LLAMA_SERVER", os.path.join(RADICE, "llama", "llama-server.exe"))
ARGOMENTI = ["-lm", "mmap", "-lzm", "on", "--port", "8090", "-c", "65536", "-np", "1", "-b", "2048", "-ub", "2048"]
import subprocess, threading
_scambio = threading.Lock()


def modello_acceso():
    try:
        nome = json.load(urllib.request.urlopen(f"{QWEN}/v1/models", timeout=5))["models"][0]["name"]
    except Exception:
        return None
    return next((k for k, v in MODELLI.items() if os.path.basename(v) in nome.replace("/", "\\")), None)


def assicura_modello(voluto):
    """Se il client chiede un modello diverso da quello acceso, spegne l'attuale e accende quello giusto."""
    if voluto not in MODELLI:
        return
    with _scambio:
        if modello_acceso() == voluto:
            return
        registra(scambio=f"accendo {voluto}")
        subprocess.run(["powershell", "-NoProfile", "-c",
                        "Get-CimInstance Win32_Process -Filter \"name='llama-server.exe'\" | "
                        "? { $_.CommandLine -match '--port 8090' } | % { Stop-Process -Id $_.ProcessId -Force }"])
        time.sleep(3)
        os.makedirs(os.path.join(RADICE, "runs"), exist_ok=True)
        log = open(os.path.join(RADICE, "runs", "srv_scambio.log"), "w")
        subprocess.Popen([SERVER, "-m", os.path.join(RADICE, MODELLI[voluto])] + ARGOMENTI, cwd=RADICE,
                         stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000)  # senza finestra
        for _ in range(120):
            time.sleep(3)
            try:
                if b"ok" in urllib.request.urlopen(f"{QWEN}/health", timeout=3).read():
                    registra(scambio=f"{voluto} pronto")
                    return
            except Exception:
                pass
        registra(scambio=f"{voluto}: avvio non riuscito, vedi runs/srv_scambio.log")


ultimo_uso = [time.time()]
SPEGNI_DOPO = int(os.environ.get("SMISTA_SPEGNI_MIN", "30")) * 60  # 0 = mai


def _custode():
    """Spegne il modello dopo SPEGNI_DOPO secondi senza richieste: libera scheda video e RAM (si riaccende da solo)."""
    while SPEGNI_DOPO > 0:
        time.sleep(60)
        if time.time() - ultimo_uso[0] > SPEGNI_DOPO and modello_acceso() is not None and not _scambio.locked():
            with _scambio:
                subprocess.run(["powershell", "-NoProfile", "-c",
                                "Get-CimInstance Win32_Process -Filter \"name='llama-server.exe'\" | "
                                "? { $_.CommandLine -match '--port 8090' } | % { Stop-Process -Id $_.ProcessId -Force }"])
                registra(scambio=f"modello spento dopo {SPEGNI_DOPO // 60} min senza uso")


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _inoltra(self, metodo):
        corpo = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if metodo == "POST" else None
        if metodo == "GET" and self.path.rstrip("/").endswith("/v1/models"):  # la lista mostra tutti i modelli
            out = json.dumps({"object": "list", "data": [{"id": k, "object": "model", "owned_by": "locale"}
                                                          for k in MODELLI]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if corpo and self.path.endswith("/chat/completions"):
            try:
                dati = json.loads(corpo)
                ultimo_uso[0] = time.time()
                try:  # misura del prompt: quanto pesa ogni parte (per tenerlo corto, come il budget di Agent Zero)
                    sist = [m for m in dati.get("messages", []) if m.get("role") == "system"]
                    with open(os.path.join(os.path.dirname(LOG), "ultimo_prompt.json"), "w", encoding="utf-8") as f:
                        json.dump({"system_caratteri": sum(len(testo(m)) for m in sist),
                                   "system": [testo(m) for m in sist],
                                   "strumenti": sorted(((t.get("function", {}).get("name"), len(json.dumps(t)))
                                                        for t in dati.get("tools") or []), key=lambda x: -x[1]),
                                   "strumenti_caratteri": len(json.dumps(dati.get("tools") or []))},
                                  f, ensure_ascii=False, indent=1)
                except Exception:
                    pass
                assicura_modello(dati.get("model", "") or "flashnext-uncensored")
                corpo = json.dumps(smista(dati)).encode()
            except Exception as e:
                registra(errore_smista=str(e)[:200])
        req = urllib.request.Request(QWEN + self.path, data=corpo, method=metodo,
                                     headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=3600)
        except urllib.error.HTTPError as e:
            r = e
        self.send_response(r.status)
        for h, v in r.headers.items():
            if h.lower() not in ("content-length", "transfer-encoding", "connection"):
                self.send_header(h, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        while True:
            pezzo = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
            if not pezzo:
                break
            self.wfile.write(b"%x\r\n%s\r\n" % (len(pezzo), pezzo))
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")

    def do_POST(self):
        self._inoltra("POST")

    def do_GET(self):
        self._inoltra("GET")


if __name__ == "__main__":
    print(f"smistatore su :{PORTA} -> Qwen {QWEN}, Kev {KEV}, soglia {SOGLIA}", flush=True)
    threading.Thread(target=_custode, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORTA), Proxy).serve_forever()
