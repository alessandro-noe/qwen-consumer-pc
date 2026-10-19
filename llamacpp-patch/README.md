# llamacpp-patch — optional, experimental

**You do not need this patch** to run the model at ~39 tok/s: the recipe uses stock llama.cpp.

`agente-locale.patch` applies to llama.cpp commit `620d2225c` (build b11669); other versions are untested.
Every change is marked with the comment `agente-locale` and is **off unless its environment variable is set**.

| Variable | What it does | Measured result |
|---|---|---|
| `MOE_HYBRID=1` + `MOE_CACHE_PIN=<file>` | hybrid MoE for small GPUs: "hot" experts chosen by measured impact are pinned in VRAM once, the others run on the CPU (`id = -1` = skip on GPU) | +8% / +21% tok/s with experts in RAM and ~6 GB of pinned experts; **-21%** on the 16 GB PC vs automatic placement |
| `MOE_COLD_TOPK=7` | on hybrid layers the CPU computes only the first 7 cold choices of the router | 22.0/29.1 → 24.3/33.7 tok/s on a simulated weaker PC; agent quality not verified |
| `MOE_CPU_TOPK=K` | fewer experts on RAM layers (generation only) | +18% (K=7) to +25% (K=6) tok/s, but hard tasks took **2x** longer. Not recommended |
| `MOE_ESEC_K=K` / `MOE_ESEC_FILE` | all experts while reading and thinking, K experts after `</think>` | +16–20% tok/s, but hard tasks took 2–4x longer. Not recommended |
| `MOE_CONF_K` / `MOE_CONF_TAU` | cut experts only when the router is confident | works, no useful gain |

Apply with:
```
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
git checkout 620d2225c
git apply ../llamacpp-patch/agente-locale.patch
```
then build with CUDA as described in the llama.cpp docs. Details (Italian): [docs/it/RAPPORTO.md](../docs/it/RAPPORTO.md), [docs/it/INVENZIONI.md](../docs/it/INVENZIONI.md).
