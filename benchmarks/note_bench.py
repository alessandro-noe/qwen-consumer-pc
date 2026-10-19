"""
note_bench.py — Qwen capisce le note scritte in forma compatta quanto quelle normali?
10 note x 2 forme (italiano normale / inglese compatto), 2 domande per nota con risposta esatta controllata.
Il modello legge le note insieme (come in memoria/quaderno) e risponde senza ragionamento.
Uso: python note_bench.py <porta>
"""
import json, re, sys, time, urllib.request

port = sys.argv[1]
NOTE = [
    ("Abbiamo deciso di usare la scalata al fallimento: il modello lavora senza ragionamento e lo accende solo dopo due test falliti. Il file da modificare e' sistema/smistatore.py.",
     "decision: failure escalation (reasoning off, on after 2 failed tests)\nfile: sistema/smistatore.py",
     [("Dopo quanti test falliti si accende il ragionamento? Rispondi con un numero.", "2"),
      ("Quale file va modificato per la scalata?", "smistatore.py")]),
    ("Il server di Kev gira sulla porta 9931 e va avviato con l'opzione -lm mlock, altrimenti Windows sposta i suoi pesi fuori dalla RAM e diventa lento.",
     "kev: port 9931, flag -lm mlock (else Windows evicts weights -> slow)",
     [("Su quale porta gira Kev?", "9931"), ("Quale opzione serve per tenere Kev in RAM?", "mlock")]),
    ("Non bisogna mai combinare Ponytail con la scalata: insieme hanno fatto fallire il compito minidb, che altrimenti riesce sempre.",
     "never: Ponytail + escalation (together failed minidb)",
     [("Quale compito e' fallito combinando Ponytail e scalata?", "minidb"), ("Con cosa non va combinato Ponytail?", "scalata|escalation")]),
    ("Il cliente Bianchi vuole il sito pronto entro il 14 novembre, con palette verde salvia e il font Fraunces per i titoli.",
     "client Bianchi: site due 14 Nov, palette sage green, headings font Fraunces",
     [("Entro che giorno di novembre va consegnato il sito? Solo il numero.", "14"), ("Quale font per i titoli?", "Fraunces")]),
    ("Per il backup si usa lo script backup_notte.ps1 che copia la cartella progetti sul disco D alle 3 di notte; tiene le ultime 7 copie.",
     "backup: backup_notte.ps1, copies projects -> D:, 03:00, keeps last 7",
     [("Quante copie tiene il backup? Solo il numero.", "7"), ("Come si chiama lo script di backup?", "backup_notte.ps1")]),
    ("Il bug del carrello era causato da un arrotondamento: i prezzi venivano sommati come float. La correzione usa Decimal nel file cart.py, funzione total().",
     "bug cart: float rounding on price sum -> fix: Decimal in cart.py total()",
     [("Quale tipo numerico risolve il bug del carrello?", "Decimal"), ("In quale funzione e' la correzione?", "total")]),
    ("La chiave per l'API meteo non va mai scritta nel codice: sta nel file .env con il nome METEO_KEY. Il limite gratuito e' di 1000 chiamate al giorno.",
     "weather api key: never in code; .env as METEO_KEY; free limit 1000 calls/day",
     [("Come si chiama la variabile della chiave meteo?", "METEO_KEY"), ("Quante chiamate al giorno nel piano gratuito?", "1000")]),
    ("Il video promozionale deve durare 45 secondi, formato verticale 9:16, musica senza voce, e va esportato con Remotion.",
     "promo video: 45 s, vertical 9:16, music no vocals, export via Remotion",
     [("Quanti secondi dura il video? Solo il numero.", "45"), ("Con quale strumento si esporta il video?", "Remotion")]),
    ("Nel progetto della mod la cartella dei modelli originali e' sola lettura: si lavora solo sulle copie in mod_work/, mai sugli originali.",
     "mod project: original models folder read-only; work only on copies in mod_work/",
     [("In quale cartella si lavora sulle copie?", "mod_work"), ("Si possono modificare gli originali? Rispondi si o no.", "no")]),
    ("La riunione con il commercialista e' martedi alle 10:30; bisogna portare le fatture di settembre e il riepilogo IVA del trimestre.",
     "meeting accountant: Tuesday 10:30; bring September invoices + quarterly VAT summary",
     [("A che ora e' la riunione?", "10:30"), ("Le fatture di quale mese vanno portate?", "settembre|september")]),
]


def chiedi(note, domanda):
    b = {"messages": [{"role": "user", "content": f"Note di lavoro:\n{note}\n\nDomanda: {domanda}\nRispondi in modo breve, in italiano."}],
         "max_tokens": 60, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=300))
    return r["choices"][0]["message"]["content"] or "", r["usage"]["prompt_tokens"]


for forma, idx in (("italiano normale", 0), ("inglese compatto", 1)):
    tutte = "\n\n".join(n[idx] for n in NOTE)   # tutte le note insieme, come una memoria
    giuste, tok, sbagli = 0, 0, []
    for n in NOTE:
        for dom, atteso in n[2]:
            ris, t = chiedi(tutte, dom)
            tok = t
            ok = any(a.lower() in ris.lower() for a in atteso.split("|"))
            giuste += ok
            if not ok:
                sbagli.append((dom, ris.strip()[:60]))
    print(f"{forma:18s} giuste {giuste}/20 | prompt {tok} token", flush=True)
    for s in sbagli:
        print("   ", s)
