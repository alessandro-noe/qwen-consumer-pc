"""
spec_bench.py — misura velocita' e FEDELTA' della bozza veloce (decodifica speculativa).

Due prompt tipici del lavoro agentico, a temperatura 0 (greedy):
  - "copia": riscrivere un file intero con una correzione (molto testo gia' visto -> la bozza aiuta)
  - "nuovo": scrivere codice nuovo da zero (poco testo gia' visto)
Con greedy la verifica del modello grande rende l'uscita IDENTICA alla generazione normale:
il test lo controlla confrontando il testo con quello della configurazione base.

Uso: python spec_bench.py <etichetta> <porta>      (la prima etichetta "base" fa da riferimento)
"""
import json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "agent_loop.py").read_text(encoding="utf-8")
PROMPTS = {
    "copia": "Rewrite the whole file below, unchanged except: rename `same_error_streak` to `repeat_count` everywhere. "
             "Output only the full file in one ```python block.\n\n```python\n" + src + "\n```",
    "nuovo": "Write a complete Python module implementing a thread-safe LRU cache with TTL expiry, "
             "a decorator to memoize functions with it, and unittest tests. Output only code in one ```python block.",
}
TPL = "<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
label, port = sys.argv[1], sys.argv[2]
rf = HERE / "runs" / "spec_bench.json"
res = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}
for name, p in PROMPTS.items():
    body = {"prompt": TPL.format(p=p), "n_predict": 1500, "temperature": 0, "top_k": 1, "cache_prompt": False,
            "stop": ["<|im_end|>"], **({"ignore_eos": True} if __import__("os").environ.get("IGNORE_EOS") else {})}
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}), timeout=3600))
    t = r["timings"]
    base = res.get(f"base|{name}", {}).get("text")
    same = None if base is None else (r["content"] == base)
    res[f"{label}|{name}"] = {"tok_s": round(t["predicted_per_second"], 1), "n": t["predicted_n"],
                              "draft_n": t.get("draft_n"), "draft_ok": t.get("draft_n_accepted"),
                              "identico_a_base": same, "text": r["content"]}
    print(f"{label:12s} {name:6s} {t['predicted_per_second']:6.1f} tok/s | {t['predicted_n']} token | "
          f"bozza {t.get('draft_n')} accettati {t.get('draft_n_accepted')} | identico a base: {same}", flush=True)
rf.parent.mkdir(exist_ok=True)
rf.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
