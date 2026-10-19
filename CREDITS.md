# Credits and third-party licenses

| Piece | Author | License | How it is used here |
|---|---|---|---|
| [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | Qwen | qwen-community-1.0 | the model (not included) |
| [GSQ-RCO Q2_0 GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) ([GSQ paper](https://arxiv.org/abs/2604.18556)) | ISTA-DASLab | Apache-2.0 (per the repository) | quantized weights to download (not included) |
| [Uncensored / abliterated GGUF](https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF) | SC117 | Apache-2.0 (per the repository) | quantized weights to download (not included) |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | ggml-org and contributors | MIT | inference engine; `llamacpp-patch/` contains our optional changes to it |
| [Kev-4B GGUF](https://huggingface.co/ggml-org/Kev-4B-GGUF) | ggml-org | Apache-2.0 | optional decision model (not included) |
| [OpenCode](https://github.com/anomalyco/opencode) | anomalyco | see their repository | coding agent used in the tests (install separately) |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Nous Research | MIT | ideas for the proxy's guard (rewritten, no code copied) |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | DietrichGebert | MIT | `minimo` skill (shortened) |
| [ECC](https://github.com/affaan-m/ECC) | Affaan Mustafa | MIT | agent/skill profile (shortened), see `opencode/.opencode/LICENSE-ECC.txt` |
| [RTK](https://github.com/rtk-ai/rtk) | rtk-ai | Apache-2.0 | `rtk_locale.ts` plugin (rewritten); `rtk.exe` is downloaded separately |
| [colibri](https://github.com/JustVugg/colibri) | JustVugg | see their repository | used to trace router decisions and measure per-expert impact (not included) |
| [Strata](https://github.com/Niko1221/Strata) | Niko1221 | see their repository | prior work on the same model, read for comparison (not included) |

Skills from other authors that the optional skill library (`extras/biblioteca_mcp.py`) indexes stay on the user's PC: they are not part of this repository.
