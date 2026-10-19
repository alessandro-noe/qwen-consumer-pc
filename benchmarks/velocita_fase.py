"""velocita_fase.py — tok/s in fase di ESECUZIONE (ragionamento spento) per confrontare MOE_ESEC_K."""
import json, sys, urllib.request
PROMPT = ["Scrivi in Python una classe LRUCache con get e put O(1) e i test unittest.",
          "Write a Python function that parses ISO 8601 durations like P3DT4H5M and returns seconds, with tests.",
          "Implementa un piccolo parser di espressioni aritmetiche con precedenza e parentesi, in Python."]
v = []
for p in PROMPT:
    b = {"messages": [{"role": "user", "content": p}], "max_tokens": 700, "temperature": 0,
         "chat_template_kwargs": {"enable_thinking": False}}
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
        data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=600))
    v.append(r["timings"]["predicted_per_second"])
print(f"{sys.argv[1]:12s} tok/s: " + " / ".join(f"{x:.1f}" for x in v) + f"  media {sum(v)/len(v):.1f}", flush=True)
