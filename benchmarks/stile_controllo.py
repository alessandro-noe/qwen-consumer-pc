"""
stile_ragionamento.py — quale "lingua di ragionamento" rende il modello piu' veloce SENZA perdere intelligenza?

Stessi problemi HumanEval (i 10 che senza ragionamento falliva + 20 di controllo), ragionamento ACCESO,
cambia solo l'istruzione su COME ragionare:
  libero    : nessuna istruzione (riferimento)
  bozza     : Chain of Draft (arXiv 2502.18600) — passi da max 5 parole
  cinese    : ragiona in cinese conciso (ipotesi: meno token per lo stesso contenuto)
  simbolico : notazione compatta (simboli, nomi di variabili, niente frasi)
Si misurano: problemi risolti, token generati (pensiero + risposta), secondi.

Uso: python stile_ragionamento.py <porta> [stili...]
"""
import json, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from datasets import load_dataset

HERE = Path(__file__).resolve().parent
STILI = {
    "libero": "",
    "bozza": ("Think step by step, but only keep a minimum draft for each thinking step, "
              "with 5 words at most per step. "),
    "cinese": "请用非常简洁的中文进行思考（只写关键步骤）。",
    "simbolico": ("Think in compact notation only: symbols (-> = != => for all), variable names, short code "
                  "fragments; no full sentences. "),
    "toml": ("Think only as a short TOML document with these keys and nothing else: "
             "goal, inputs, edge_cases (array), algorithm (array of short steps), check. Keep values terse. "),
    # TOON (github.com/toon-format/toon): key: value, array con lunghezza, tabelle {campi} con righe CSV
    "toon": ("Think only in TOON notation (compact: `key: value`, arrays like `edge_cases[3]: a,b,c`, "
             "tables like `tests[2]{input,expected}:` then one row per line). Use keys goal, edge_cases, "
             "steps, tests, check. No prose. "),
    # MISTI: struttura TOML/TOON + valori in cinese conciso
    "cinese_toml": ("Think only as a short TOML document with keys goal, inputs, edge_cases (array), "
                    "algorithm (array of short steps), check. 所有值请用非常简洁的中文书写。 "),
    "cinese_toon": ("Think only in TOON notation (`key: value`, arrays like `edge_cases[3]: a,b,c`, tables like "
                    "`tests[2]{input,expected}:` then one row per line), keys goal, edge_cases, steps, tests, check. "
                    "所有值请用非常简洁的中文书写。 "),
}
FALLITI = ["HumanEval/91", "HumanEval/93", "HumanEval/109", "HumanEval/115", "HumanEval/127",
           "HumanEval/130", "HumanEval/132", "HumanEval/140", "HumanEval/145", "HumanEval/163"]
IDS = [f"HumanEval/{i}" for i in (10, 26, 32, 39, 64, 75, 81, 89, 108, 118, 120, 126, 129, 141, 147, 151, 154, 160)]  # CONTROLLO: mai visti
port = sys.argv[1]
stili = sys.argv[2:] or list(STILI)
ds = {r["task_id"]: r for r in load_dataset("openai/openai_humaneval")["test"]}
rf = HERE / "runs" / "stile_controllo.json"
res = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}


def prova(row, txt):
    ans = txt.split("</think>")[-1]
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", ans, re.S)
    code = m[-1] if m else ans
    prog = row["prompt"] + "\n    pass\n\n" + code + "\n\n" + row["test"] + f"\ncheck({row['entry_point']})\nprint('OK')\n"
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.py").write_text(prog, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, "-I", "t.py"], cwd=d, capture_output=True, text=True, timeout=20)
            return p.returncode == 0 and "OK" in p.stdout
        except subprocess.TimeoutExpired:
            return False


for stile in stili:
    for tid in IDS:
        key = f"{stile}|{tid}"
        if key in res:
            continue
        p = ("<|im_start|>user\n" + STILI[stile] + "Complete this Python function. Reply with the full function "
             "in one ```python block, no explanation.\n\n" + ds[tid]["prompt"] + "<|im_end|>\n<|im_start|>assistant\n<think>\n")
        body = {"prompt": p, "n_predict": 12000, "temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": 1,
                "stop": ["<|im_end|>"], "cache_prompt": False}
        t0 = time.time()
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}), timeout=3600))
        txt = r["content"]
        res[key] = {"ok": prova(ds[tid], txt), "tokens": r["timings"]["predicted_n"],
                    "sec": round(time.time() - t0, 1), "chiuso": "</think>" in txt, "text": txt}
        rf.parent.mkdir(exist_ok=True)
        rf.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    rows = [v for k, v in res.items() if k.startswith(stile + "|")]
    print(f"{stile:10s} risolti {sum(v['ok'] for v in rows)}/{len(rows)} | token medi {sum(v['tokens'] for v in rows)/len(rows):.0f} "
          f"| secondi medi {sum(v['sec'] for v in rows)/len(rows):.1f} | pensiero chiuso {sum(v['chiuso'] for v in rows)}/{len(rows)}",
          flush=True)
