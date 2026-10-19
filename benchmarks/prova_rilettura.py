"""prova_rilettura.py — perche' Qwen rilegge lento? (1) velocita' di lettura di un prompt nuovo, (2) cache con interruttore del ragionamento."""
import json, sys, time, urllib.request, random
def chiedi(msgs, think, max_t=1):
    b = {"messages": msgs, "max_tokens": max_t, "temperature": 0, "chat_template_kwargs": {"enable_thinking": think}}
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
        data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=900))
    t = r["timings"]; return t["prompt_n"], t["prompt_ms"] / 1000
from pathlib import Path
_R = Path(__file__).resolve().parent.parent
codice = (_R / "proxy" / "smistatore.py").read_text(encoding="utf-8") + (_R / "extras" / "kael_mcp.py").read_text(encoding="utf-8")
seme = str(random.random())  # prompt sempre nuovo: niente cache
n, s = chiedi([{"role": "user", "content": seme + "\n" + codice[:30000] + "\nRiassumi in una riga."}], False)
print(f"{sys.argv[1]}: lettura di {n} token nuovi in {s:.1f} s = {n/s:.0f} tok/s")
base = [{"role": "system", "content": "Sei un assistente."}, {"role": "user", "content": seme + codice[:12000] + "\nDimmi ok."}]
chiedi(base, True)
n1, s1 = chiedi(base + [{"role": "assistant", "content": "ok"}, {"role": "user", "content": "e ora?"}], True)
n2, s2 = chiedi(base + [{"role": "assistant", "content": "ok"}, {"role": "user", "content": "e ora?"}, {"role": "assistant", "content": "ok"}, {"role": "user", "content": "ancora"}], False)
print(f"{sys.argv[1]}: passo successivo stesso interruttore -> riletti {n1} token ; cambiando ragionamento on->off -> riletti {n2} token")
