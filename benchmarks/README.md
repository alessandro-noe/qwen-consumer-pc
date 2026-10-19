# benchmarks

Every script used for the numbers in the main README. Results are written to `benchmarks/runs/` (git-ignored).
The model must be running (port 8090 directly, or 8091 through the proxy).

| Script | What it measures | Usage |
|---|---|---|
| `velocita_fase.py` | generation tok/s, thinking off, 3 coding prompts | `python benchmarks/velocita_fase.py <label>` |
| `agent_bench2.py` | 12 agent tasks with hidden checker | see the top of the file |
| `agent_bench3.py` | 5 hard multi-file tasks with hidden checker (the headline benchmark) | `python benchmarks/agent_bench3.py <label> <port> [task ids]` |
| `stile_controllo.py` | 18 held-out problems, reasoning styles | see the top of the file |
| `spec_bench.py` | speculative decoding (n-gram, MTP) | see the top of the file |
| `prova_rilettura.py` | prompt-reading speed and cache behaviour when thinking is toggled | `python benchmarks/prova_rilettura.py <label>` |
| `prova_smistatore.py` | proxy vs direct on simple questions | see the top of the file |
| `note_bench.py` | compact English notes vs normal Italian notes (token cost, recall) | see the top of the file |
| `decisore_bench.py`, `decisore_qwen.py` | small decision models (and Qwen itself) as routers | see the top of the file |
| `browser_bench.py` | browser executor on the local site `sito_prova/` (includes a hidden prompt-injection trap) | `python benchmarks/browser_bench.py kev\|solo_qwen` |
| `misura_rtk.py` | token savings of RTK on command output | `python benchmarks/misura_rtk.py <pytest folder> <git repo>` |
| `mcp_bench.py` | tool calling in a loop (early benchmark, talks to **Ollama** on port 11434) | see the top of the file |
| `adatta_prova.py` | the model adapts skills for itself (needs `extras/biblioteca_mcp.py`) | `python benchmarks/adatta_prova.py <port> <skill names>` |

`sandbox.py` runs model-written code in a temporary folder for the agent benchmarks. It is **not** a security sandbox: run the benchmarks on a machine you are fine experimenting on.
