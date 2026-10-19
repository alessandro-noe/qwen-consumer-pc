"""decisore_qwen.py — Qwen usato COME modello decisionale: 1 passata, 1 token, probabilita' delle lettere.
Stesso banco di decisore_bench.py (32 richieste, 8 strade). Uso: python decisore_qwen.py <porta> <etichetta>"""
import json, math, statistics, sys, time, urllib.request
from pathlib import Path
src = Path(__file__).with_name("decisore_bench.py").read_text(encoding="utf-8")
ns = {"__file__": __file__}; exec(src.split("NOMI = ")[0].replace("port, label = sys.argv[1], sys.argv[2]", ""), ns)
ROTTE, RICHIESTE = ns["ROTTE"], ns["RICHIESTE"]
port, label = sys.argv[1], sys.argv[2]
LET = "12345678"; chiavi = list(ROTTE)
OUT = Path(__file__).resolve().parent / "runs" / "decisore_bench.json"
OUT.parent.mkdir(exist_ok=True)
res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
for lingua, li in (("it", 0), ("en", 1)):
    opz = "\n".join(f"{LET[i]}) {k}: {ROTTE[k][li]}" for i, k in enumerate(chiavi))
    giuste, ms, fok, fno, errori = 0, [], [], [], []
    for r in RICHIESTE:
        q = (f"Strade possibili:\n{opz}\nRispondi solo con il numero della strada giusta.\n\nRichiesta dell'utente: {r[0]}" if lingua == "it"
             else f"Possible routes:\n{opz}\nAnswer only with the number of the right route.\n\nUser request: {r[1]}")
        b = {"messages": [{"role": "user", "content": q}], "max_tokens": 1, "logprobs": True, "top_logprobs": 20,
             "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
        t = time.time()
        c = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(b).encode(), headers={"Content-Type": "application/json"})))["choices"][0]
        ms.append(1000 * (time.time() - t))
        p = {x["token"].strip(): math.exp(x["logprob"]) for x in c["logprobs"]["content"][0]["top_logprobs"] if x["token"].strip() in LET}
        z = sum(p.values()) or 1
        scelta = max(p, key=p.get) if p else "?"
        fid = p.get(scelta, 0) / z
        ok = scelta in LET and chiavi[LET.index(scelta)] == r[2]
        giuste += ok; (fok if ok else fno).append(fid)
        if not ok: errori.append((r[li][:60], r[2], chiavi[LET.index(scelta)] if scelta in LET else scelta, round(fid, 2)))
    k = f"{label}|strada_{lingua}_descr"
    res[k] = {"precisione": round(giuste / 32, 3), "fiducia_giuste": round(statistics.mean(fok), 2) if fok else None,
              "fiducia_sbagliate": round(statistics.mean(fno), 2) if fno else None, "ms_mediana": round(statistics.median(ms)),
              "ms_max": round(max(ms)), "errori": errori}
    print(k, {x: res[k][x] for x in ("precisione", "fiducia_giuste", "fiducia_sbagliate", "ms_mediana", "ms_max")}, flush=True)
    for e in errori: print("   ", e)
OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
