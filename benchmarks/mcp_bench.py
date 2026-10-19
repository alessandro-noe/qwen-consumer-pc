"""
mcp_bench.py — banco per l'uso di TOOL (stile MCP).

Gli strumenti MCP arrivano al modello come definizioni di funzione: qui usiamo
il tool-calling nativo di Ollama (stesso formato). Il modello deve CHIAMARE gli
strumenti giusti con gli argomenti giusti, in un loop, per finire il compito.

Misuriamo:
  - usa davvero i tool? (o risponde a mente, come ha gia' sbagliato?)
  - chiama lo strumento giusto con argomenti validi?
  - finisce il compito? (verifica oggettiva su stato finale / risposta)

Ambiente sicuro: workspace in cartella temporanea, run_python nella sandbox.
"""
from __future__ import annotations
import json
import tempfile
import urllib.request
from pathlib import Path

import subprocess
import sys
from sandbox import run_python

MODEL = "hf.co/empero-ai/Qwen3.8-27B-Ridge-GGUF"
URL = "http://127.0.0.1:11434/api/chat"

# --- definizioni tool (stesso schema che userebbe un server MCP) ---
TOOLS = [
    {"type": "function", "function": {
        "name": "calc", "description": "Valuta un'espressione aritmetica Python e ne ritorna il valore.",
        "parameters": {"type": "object", "properties": {"expr": {"type": "string"}}, "required": ["expr"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "Scrive testo in un file del workspace.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}}, "required": ["name", "content"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Legge il contenuto di un file del workspace.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "run_python", "description": "Esegue un file .py del workspace e ritorna stdout/stderr.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "finish", "description": "Termina il compito e fornisce la risposta finale.",
        "parameters": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}}},
]


class Workspace:
    """Esegue le chiamate tool in una cartella temporanea isolata."""
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.used: list[str] = []
        self.final: str | None = None

    def call(self, name: str, args: dict) -> str:
        self.used.append(name)
        try:
            if name == "calc":
                return str(eval(str(args["expr"]), {"__builtins__": {}}, {}))
            if name == "write_file":
                (self.tmp / args["name"]).write_text(str(args["content"]), encoding="utf-8")
                return "scritto"
            if name == "read_file":
                return (self.tmp / args["name"]).read_text(encoding="utf-8")
            if name == "run_python":
                # esegue DENTRO il workspace: i file prodotti (es. sorted.txt)
                # restano disponibili ai passi successivi e al checker finale.
                try:
                    p = subprocess.run([sys.executable, args["name"]],
                                       cwd=self.tmp, capture_output=True,
                                       text=True, timeout=30)
                    out = (p.stdout or "")[-800:]
                    err = (p.stderr or "")[-800:]
                    return f"[exit={p.returncode}]\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
                except subprocess.TimeoutExpired:
                    return "[TIMEOUT dopo 30s]"
            if name == "finish":
                self.final = str(args.get("answer", ""))
                return "fine"
            return f"strumento sconosciuto: {name}"
        except Exception as e:
            return f"ERRORE tool {name}: {e}"


def run_task(goal: str, max_steps: int = 10) -> dict:
    with tempfile.TemporaryDirectory(prefix="mcp_") as d:
        ws = Workspace(Path(d))
        messages = [
            {"role": "system", "content":
             "Sei un agente. Usa SEMPRE gli strumenti per agire e calcolare: non "
             "calcolare a mente. Quando il compito e' finito chiama `finish`."},
            {"role": "user", "content": goal},
        ]
        bad_calls = 0
        for _ in range(max_steps):
            payload = {"model": MODEL, "messages": messages, "stream": False,
                       "think": False, "tools": TOOLS, "options": {"num_ctx": 8192}}
            req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                body = json.loads(r.read().decode())
            msg = body["message"]
            messages.append(msg)
            calls = msg.get("tool_calls") or []
            if not calls:
                # nessun tool: il modello ha risposto a mente -> chiudiamo
                ws.final = ws.final or (msg.get("content") or "")
                break
            for c in calls:
                fn = c["function"]["name"]
                raw = c["function"].get("arguments", {})
                args = raw if isinstance(raw, dict) else json.loads(raw or "{}")
                obs = ws.call(fn, args)
                messages.append({"role": "tool", "tool_name": fn, "content": obs})
            if ws.final is not None:
                break
        return {"final": ws.final, "used": ws.used,
                "used_any_tool": bool(ws.used), "bad_calls": bad_calls, "ws": Path(d)}
