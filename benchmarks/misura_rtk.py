"""misura_rtk.py — token dell'output dei comandi: normale vs filtrato da RTK (rtk-oss 1.0.1).
Conta con il tokenizzatore vero di Qwen (/tokenize di llama-server). Controlla anche che l'informazione utile resti.
Uso: python misura_rtk.py <cartella con 3 test pytest che falliscono> <un repository git qualsiasi (misurato: Strata)>
     (rtk.exe da RTK_EXE o dal PATH)"""
import json, os, subprocess, sys, urllib.request
RTK = os.environ.get("RTK_EXE", "rtk.exe")
env = dict(os.environ, RTK_TELEMETRY_DISABLED="1")
PROVA = sys.argv[1]; STRATA = sys.argv[2]
CASI = [  # (nome, cartella, comando, parole che devono restare)
    ("pytest con 3 errori", PROVA, ["pytest"], ["test_dividi_zero", "ZeroDivisionError", "test_media_vuota", "test_media", "3 failed"]),
    ("git log -20", STRATA, ["git", "log", "-20"], []),
    ("git status", STRATA, ["git", "status"], []),
    ("ls -la src", STRATA, ["ls", "-la", "src"], []),
    ("grep -rn MtpDrafter", STRATA, ["grep", "-rn", "MtpDrafter", "src", "include"], ["mtp.hpp"]),
]
def tok(t):
    r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/tokenize", data=json.dumps({"content": t}).encode(),
                               headers={"Content-Type": "application/json"}))
    return len(json.load(r)["tokens"])
def esegui(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    return p.stdout + p.stderr
tot_a = tot_b = 0
for nome, cwd, cmd, tieni in CASI:
    a = esegui(cmd, cwd); b = esegui([RTK] + cmd, cwd)
    ta, tb = tok(a), tok(b); tot_a += ta; tot_b += tb
    persi = [w for w in tieni if w in a and w not in b]
    print(f"{nome:24s} {ta:6d} -> {tb:5d} token ({100 * (ta - tb) / max(ta, 1):5.1f}% in meno)" + (f"  PERSO: {persi}" if persi else ""))
print(f"TOTALE {tot_a} -> {tot_b} ({100 * (tot_a - tot_b) / tot_a:.1f}% in meno)")
