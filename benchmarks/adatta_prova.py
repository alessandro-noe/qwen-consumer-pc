"""
adatta_prova.py — Qwen adatta da solo skill complesse seguendo .opencode/skills/adatta-skill, e le salva.
Misura: dimensione prima/dopo (token), e quanti punti chiave dell'originale sopravvivono (parole "never/mai",
nomi di comandi e librerie). Uso: python adatta_prova.py <porta> nome1 nome2 ...
"""
import json, re, sys, time, urllib.request
from pathlib import Path

port, nomi = sys.argv[1], sys.argv[2:]
BASE = Path(__file__).resolve().parent.parent
src = (BASE / "extras" / "biblioteca_mcp.py").read_text(encoding="utf-8")
ns = {"__file__": str(BASE / "extras" / "biblioteca_mcp.py")}
exec(src.split("if len(sys.argv) > 2")[0], ns)
exec("def skill_salva_adattata" + src.split("@mcp.tool()\ndef skill_salva_adattata")[1].split("@mcp.tool()")[0], ns)
REGOLE = (BASE / "opencode" / ".opencode" / "skills" / "adatta-skill" / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[2]


def post(path, body, timeout=1800):
    return json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=timeout))


def tok(t):
    return len(post("/tokenize", {"content": t})["tokens"])


def chiavi(t):
    """Punti che una buona versione adattata deve conservare: divieti e nomi tecnici."""
    divieti = re.findall(r"(?im)^.*\b(never|do not|don't|avoid|mai|non usare)\b.*$", t)
    nomi = set(re.findall(r"`([^`\n]{3,40})`", t))
    return divieti, nomi


for nome in nomi:
    s = next(x for x in ns["SKILL"] if x["nome"] == nome)
    orig = Path(s["percorso"]).read_text(encoding="utf-8", errors="ignore")
    if len(orig) > 60000:
        orig = orig[:60000]
    prompt = (f"{REGOLE}\n\n=== ORIGINAL SKILL `{nome}` ===\n{orig}\n=== END ===\n\n"
              "Write ONLY the adapted skill text (no front-matter, no comments before or after).")
    t0 = time.time()
    r = post("/v1/chat/completions", {"messages": [{"role": "user", "content": prompt}], "temperature": 0.6,
                                      "top_p": 0.95, "max_tokens": 8000, "chat_template_kwargs": {"enable_thinking": __import__("os").environ.get("PENSA", "0") == "1"}})
    testo = (r["choices"][0]["message"]["content"] or "").strip()
    sec = time.time() - t0
    div, nm = chiavi(orig)
    tenuti_nomi = sum(1 for n in nm if n.lower() in testo.lower())
    print(f"\n### {nome}: originale {tok(orig)} token -> adattata {tok(testo)} token, in {sec:.0f} s "
          f"(ragionamento+scrittura {r['usage']['completion_tokens']} token)")
    print(f"    nomi tecnici tra `...` conservati: {tenuti_nomi}/{len(nm)} | divieti nell'originale: {len(div)}")
    print("   ", ns["skill_salva_adattata"](nome, testo))
