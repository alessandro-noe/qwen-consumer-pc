"""prova_smistatore.py — stessa domanda diretta a Qwen (8090) e attraverso lo smistatore (8091): tempo, token, risposta."""
import json, time, urllib.request
DOMANDE = [("Quanto fa 17 per 23? Dammi solo il numero.", "391"),
           ("Qual e' la capitale dell'Australia? Una parola.", "canberra"),
           ("In Python, che tipo restituisce len()? Una parola.", "int"),
           ("Quanti secondi ci sono in 3 ore? Solo il numero.", "10800"),
           ("Traduci 'buongiorno' in inglese. Solo la traduzione.", "good morning"),
           ("Che differenza c'e' tra lista e tupla in Python? Una frase.", "mut")]
def chiedi(porta, q):
    b = {"messages": [{"role": "user", "content": q}], "max_tokens": 4000, "temperature": 0}
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{porta}/v1/chat/completions",
        data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=600))
    return time.time() - t, r["usage"]["completion_tokens"], (r["choices"][0]["message"].get("content") or "")
tot = {8090: [0, 0, 0], 8091: [0, 0, 0]}
for q, atteso in DOMANDE:
    for porta in (8090, 8091):
        s, n, txt = chiedi(porta, q)
        ok = atteso in txt.lower().replace(".", "").replace(",", "")
        tot[porta][0] += s; tot[porta][1] += n; tot[porta][2] += ok
        print(f"{porta} {s:5.1f}s {n:5d} tok {'OK ' if ok else 'NO '} {q[:40]!r} -> {txt.strip()[:50]!r}", flush=True)
for p, (s, n, k) in tot.items():
    print(f"TOTALE {p}: {s:.1f}s, {n} token, giuste {k}/{len(DOMANDE)}")
