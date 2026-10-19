"""
decisore_bench.py — quanto e' bravo un modello DECISIONALE (es. Julia-1) a prendere le decisioni rapide dell'agente?

Due prove, giudicate con risposte giuste note:
  A. STRADA: data una richiesta dell'utente, quale strada prende l'agente (8 opzioni)
  B. ELEMENTO: dato l'albero di una pagina e un passo esplicito, quale elemento cliccare (10-40 elementi)
Varianti: italiano / inglese, opzioni con / senza descrizione.
Misure: precisione, fiducia media quando giusto / sbagliato, Brier (calibrazione), latenza.

Uso: python decisore_bench.py <porta> <etichetta>      (server llama.cpp con il modello decisionale)
"""
import json, random, statistics, sys, time, urllib.request
from pathlib import Path

port, label = sys.argv[1], sys.argv[2]
OUT = Path(__file__).resolve().parent / "runs" / "decisore_bench.json"

ROTTE = {
    "risposta": ("rispondi subito con quello che sai, senza strumenti", "answer directly from knowledge, no tools"),
    "codice": ("scrivi o modifica codice nel progetto", "write or modify code in the project"),
    "debug": ("trova e correggi un errore, un crash o un test che fallisce", "find and fix an error, crash or failing test"),
    "esplora": ("capire come funziona un progetto o dove sta qualcosa nel codice (graphify)", "understand how a project works or where something is in the code"),
    "web": ("cercare informazioni aggiornate su internet", "search the internet for up-to-date information"),
    "file": ("gestire file e cartelle sul PC: spostare, rinominare, cercare, organizzare", "manage files and folders on the PC: move, rename, find, organize"),
    "browser": ("fare azioni su un sito web: cliccare, compilare moduli, navigare", "act on a website: click, fill forms, navigate"),
    "piano": ("compito lungo con molti passi che va prima pianificato", "long multi-step task that must be planned first"),
}
RICHIESTE = [  # (italiano, inglese, rotta giusta)
    ("Quanto fa 17 per 23?", "What is 17 times 23?", "risposta"),
    ("Spiegami cos'e' una closure in Python", "Explain what a closure is in Python", "risposta"),
    ("Che differenza c'e' tra una lista e una tupla?", "What is the difference between a list and a tuple?", "risposta"),
    ("Traduci 'buongiorno' in giapponese", "Translate 'good morning' into Japanese", "risposta"),
    ("Scrivi una funzione che valida un indirizzo email", "Write a function that validates an email address", "codice"),
    ("Aggiungi un pulsante di logout alla pagina del profilo", "Add a logout button to the profile page", "codice"),
    ("Crea uno script che converte i CSV in JSON", "Create a script that converts CSV files to JSON", "codice"),
    ("Aggiungi la paginazione all'endpoint /utenti", "Add pagination to the /users endpoint", "codice"),
    ("Il test test_carrello fallisce con AssertionError, sistemalo", "The test test_cart fails with AssertionError, fix it", "debug"),
    ("L'app va in crash quando apro le impostazioni", "The app crashes when I open the settings", "debug"),
    ("Ho un KeyError in report.py alla riga 40", "I get a KeyError in report.py at line 40", "debug"),
    ("Il server restituisce errore 500 sul login", "The server returns error 500 on login", "debug"),
    ("Dove viene calcolato lo sconto in questo progetto?", "Where is the discount computed in this project?", "esplora"),
    ("Come funziona il loop agentico di agent_loop.py?", "How does the agent loop in agent_loop.py work?", "esplora"),
    ("Chi chiama la funzione salva_ordine?", "Who calls the save_order function?", "esplora"),
    ("Fammi una panoramica dell'architettura del progetto", "Give me an overview of the project architecture", "esplora"),
    ("Qual e' l'ultima versione di llama.cpp uscita?", "What is the latest released version of llama.cpp?", "web"),
    ("Che tempo fa domani a Milano?", "What is the weather tomorrow in Milan?", "web"),
    ("Cerca le novita' di Unreal Engine di questa settimana", "Find this week's Unreal Engine news", "web"),
    ("Quanto costa oggi una RTX 5090?", "How much does an RTX 5090 cost today?", "web"),
    ("Sposta tutte le foto del Download nella cartella Immagini", "Move all photos from Downloads into the Pictures folder", "file"),
    ("Rinomina i file .txt della cartella note aggiungendo la data", "Rename the .txt files in the notes folder adding the date", "file"),
    ("Trova i file piu' grandi di 1 GB sul disco", "Find the files larger than 1 GB on the disk", "file"),
    ("Organizza la cartella Documenti per anno", "Organize the Documents folder by year", "file"),
    ("Compila il modulo di contatto sul sito del fornitore", "Fill in the contact form on the supplier website", "browser"),
    ("Apri GitHub e metti una stella al repository di graphify", "Open GitHub and star the graphify repository", "browser"),
    ("Accedi al pannello del router e guarda i dispositivi collegati", "Log into the router panel and check the connected devices", "browser"),
    ("Scarica dal sito della banca l'estratto conto di settembre", "Download the September statement from the bank website", "browser"),
    ("Crea un gioco 2D completo con menu, livelli e salvataggi", "Build a complete 2D game with menu, levels and save files", "piano"),
    ("Migra tutto il progetto da Flask a FastAPI con i test", "Migrate the whole project from Flask to FastAPI with tests", "piano"),
    ("Prepara il pacchetto open source con installer, documentazione e test", "Prepare the open source package with installer, docs and tests", "piano"),
    ("Costruisci un sistema RAG sui miei documenti con interfaccia web", "Build a RAG system over my documents with a web interface", "piano"),
]

NOMI = ["Save", "Cancel", "Delete", "Edit", "Search", "Login", "Logout", "Settings", "Profile", "Help", "Next", "Back",
        "Submit", "Download", "Upload", "Share", "Print", "Refresh", "Close", "Open", "Add to cart", "Checkout", "Subscribe",
        "Contact us", "Privacy policy", "Terms", "Home", "Products", "About", "Blog", "Export", "Import", "Filter", "Sort",
        "Archive", "Restore", "Copy link", "Rename", "Move", "Duplicate"]
RUOLI = ["button", "link"]


def pagine(n=24, seed=3):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        k = rnd.choice([10, 15, 20, 30, 40])
        nomi = rnd.sample(NOMI, k)
        els = {f"e{j+1}": (rnd.choice(RUOLI), nm) for j, nm in enumerate(nomi)}
        giusto = rnd.choice(list(els))
        out.append((els, giusto))
    return out


def chiedi(body):
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/systemone",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=300))
    return r["answers"]["q"], 1000 * (time.time() - t)


def misura(nome, prove):
    giuste, fid_ok, fid_no, brier, ms, errori = 0, [], [], [], [], []
    for body, atteso in prove:
        a, t = chiedi(body)
        ok = a["choice"] == atteso
        giuste += ok; ms.append(t)
        if not ok: errori.append((body["state"][-90:], atteso, a["choice"], round(a["confidence"], 2)))
        (fid_ok if ok else fid_no).append(a["confidence"])
        brier.append(sum((p - (1.0 if o == atteso else 0.0)) ** 2 for o, p in a["probabilities"].items()))
    r = {"precisione": round(giuste / len(prove), 3), "n": len(prove),
         "fiducia_giuste": round(statistics.mean(fid_ok), 2) if fid_ok else None,
         "fiducia_sbagliate": round(statistics.mean(fid_no), 2) if fid_no else None,
         "brier": round(statistics.mean(brier), 3), "ms_mediana": round(statistics.median(ms)),
         "ms_max": round(max(ms)), "errori": errori}
    print(f"{label:10s} {nome:28s} precisione {r['precisione']:.0%} ({giuste}/{len(prove)}) | fiducia ok {r['fiducia_giuste']} "
          f"sbagliate {r['fiducia_sbagliate']} | Brier {r['brier']} | {r['ms_mediana']} ms (max {r['ms_max']})", flush=True)
    return r


res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
# A. STRADA
for lingua, li in (("it", 0), ("en", 1)):
    for descr in (True, False):
        crit = {k: (v[li] if descr else None) for k, v in ROTTE.items()}
        istr = ("Quale strada deve prendere l'agente per questa richiesta?" if lingua == "it"
                else "Which route should the agent take for this request?")
        prove = [({"state": (f"Richiesta dell'utente: {r[0]}" if lingua == "it" else f"User request: {r[1]}"),
                   "questions": {"q": {"type": "choice", "instructions": istr, "criteria": crit}}}, r[2]) for r in RICHIESTE]
        res[f"{label}|strada_{lingua}_{'descr' if descr else 'etich'}"] = misura(f"strada {lingua} {'con descr.' if descr else 'solo etichette'}", prove)
# B. ELEMENTO (passo esplicito, inglese)
prove = []
for els, giusto in pagine():
    stato = "Page elements:\n" + "\n".join(f"{k} {r} '{n}'" for k, (r, n) in els.items())
    passo = f"Next step: click the '{els[giusto][1]}' {els[giusto][0]}. Which element?"
    prove.append(({"state": stato, "questions": {"q": {"type": "choice", "instructions": passo,
                   "criteria": {k: f"{r} '{n}'" for k, (r, n) in els.items()}}}}, giusto))
res[f"{label}|elemento_en"] = misura("elemento (10-40, esplicito)", prove)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
