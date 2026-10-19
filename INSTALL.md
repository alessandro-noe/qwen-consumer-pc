# Install guide (Windows)

Time: ~30 minutes plus the model download (~66 GB per version). Everything runs locally: no subscription, no data sent anywhere.

*Italiano: [docs/it/GUIDA_INSTALLAZIONE.md](docs/it/GUIDA_INSTALLAZIONE.md).*

## 0. What you need

| | Minimum tested |
|---|---|
| GPU | NVIDIA 16 GB (tested: RTX 4080 SUPER), recent driver |
| RAM | 32 GB (64 GB is faster) |
| Disk | ~110 GB free on an SSD (the model reads a table from disk while it works: NVMe recommended) |
| Software | Python 3.11+, Git; Node.js for OpenCode |

## 1. Get this repository

```
git clone https://github.com/alessandro-noe/qwen-consumer-pc
cd qwen-consumer-pc
pip install -r requirements.txt
```

## 2. llama.cpp (the engine)

From the official [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) download the **Windows x64 CUDA** build
(tested: build **b11669**, commit `620d2225c`) and, if the release ships it separately, the **cudart** archive.
Extract everything into the `llama\` folder of this repository, so that `llama\llama-server.exe` exists.

> Newer builds should work. You need the options `-lm mmap` and `-lzm on` (lazy reading of the n-gram table from disk).
> The patch in `llamacpp-patch/` is **not** needed.

## 3. The model (pick one or both)

| Version | Hugging Face repository | Put it in |
|---|---|---|
| Normal (~39 tok/s) | [`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), subfolder `Q2_0` | `models\flashnext_q2_0\Q2_0\` |
| Uncensored / abliterated (~35 tok/s) | [`SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`](https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF), subfolder `Q2_0` | `models\flashnext_q2_0_abl\Q2_0\` |

Each version is **two files** (`...-00001-of-00002.gguf` ~38 GB and `...-00002-of-00002.gguf` 28.8 GB).
The second file (the n-gram table) is **identical** in both versions: if you want both, download it once and create a hard link
(`mklink /H <new> <existing>`) instead of using another 28.8 GB.

Check the SHA-256 hashes shown on the Hugging Face file pages.

Optional:
- **Kev-4B** (small decision model, used only by the optional routing notes and the browser executor in `extras/`):
  [`ggml-org/Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF), file `Kev-4B-Q4_K_M.gguf` → `models\decisionali\`.
  With 32 GB RAM keep it **off** in normal use: running it makes prompt reading of the big model 2–3x slower (measured).
- **Vision** (image input): `mmproj-Qwen3.8-Flash-Next-BF16.gguf` from the ISTA-DASLab repository → `models\flashnext_vista\`.

## 4. OpenCode (optional agent)

```
npm i -g @opencode/cli
```
(tested with version 2.0.32). Any other OpenAI-compatible client works too.

## 5. Setup

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```
The script:
1. checks that `llama\llama-server.exe` and at least one model exist;
2. writes `opencode.json` with the paths of your PC (models, Kael, skill library, agent rules) and copies `opencode\.opencode` to `.opencode`;
3. **asks** whether to start the proxy with Windows (recommended: it uses no GPU until you send a request).

## 6. Use

1. Start the proxy: `scripts\start_proxy.cmd` (skip if you enabled autostart).
2. Open a terminal in the repository folder and type `opencode`.
3. In the model list search for **"flash"**: "Flash-Next 125B uncensored" or "normal".
4. Write. The first time the model starts by itself (~40 s); the first answer of a new conversation reads OpenCode's
   system prompt (~30–90 s), then it is fast.
5. After 30 idle minutes the model stops and frees VRAM and RAM.

Any OpenAI-compatible program can use `http://127.0.0.1:8091/v1` (models `flashnext-uncensored`, `flashnext-normale`).
To run the model without the proxy, use `scripts\start_model_normal.cmd` or `scripts\start_model_uncensored.cmd` (port 8090).

## 7. Options (environment variables of the proxy)

| Variable | What it does | Default |
|---|---|---|
| `SMISTA_SCALATA=1` | thinking off, turned on after 2 real failures | on in `start_proxy.cmd` |
| `SMISTA_SCALA_DOPO` | how many failures before thinking turns on | 2 |
| `SMISTA_GUARDIA=0` | disables the guard (repeated calls, search loops, "stop when tests pass") | on |
| `SMISTA_SPEGNI_MIN` | idle minutes before the model is stopped (0 = never) | 30 |
| `SMISTA_NOTE` | routing notes from Kev-4B (`1` = on) | off in `start_proxy.cmd` |
| `SMISTA_PORTA` | proxy port | 8091 |
| `QWEN_URL` / `KEV_URL` | llama-server / Kev addresses | `http://127.0.0.1:8090` / `:9931` |
| `LLAMA_SERVER` | path of `llama-server.exe` | `llama\llama-server.exe` |
| `BIBLIOTECA_RADICI` | extra skill folders for the skill library, separated by `;` | — |
| `RTK_EXE` | path of `rtk.exe` ([RTK](https://github.com/rtk-ai/rtk)) to shorten git/ls/grep output | on `PATH` |

## 8. Measure your own PC

```
python benchmarks\velocita_fase.py my_pc            # tokens/s (model on port 8090)
python benchmarks\agent_bench3.py my_pc 8091        # 5 hard tasks with hidden checker, through the proxy
```
Results go to `benchmarks\runs\`. Sharing them in an issue helps map other GPUs and RAM sizes.

## Common problems

- **The first message is very slow**: that is the cold read of OpenCode's system prompt. Later turns reuse the cache.
  Do not keep Kev or other models running: they take RAM away from the disk cache.
- **CUDA out of memory**: close games and other GPU programs, or reduce the context (`-c 32768`).
- **The model does not appear in OpenCode**: start OpenCode *inside* the repository folder (that is where `opencode.json` is).
- **`cudart` / DLL errors**: extract the cudart archive of the same llama.cpp release into `llama\`, or install the CUDA Toolkit
  (the start scripts add `%CUDA_PATH%\bin` to `PATH` when it is set).
