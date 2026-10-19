# What is new and what is not (honest comparison with prior work)

Literature search done on 2026-10-18. "New" here means "we did not find the same thing", not "certainly never done".
All our numbers come from **few tasks** (5 hard, 12 normal, 18 held-out problems) on **one PC**: they are **preliminary**.

## 1. Running Qwen3.8-Flash-Next 125B on 16 GB VRAM + 32 GB RAM — known method, new numbers

- **Known:** [Strata](https://github.com/Niko1221/Strata) is a dedicated inference engine for exactly this model on consumer hardware.
  By its own numbers it runs Q2_0 at 60–94 tok/s with 47–64 GB RAM and, with 32 GB RAM, recommends only its "Coder" variant.
  We read it, we did not run it.
- **Known:** the llama.cpp method (experts in RAM, per-layer table memory-mapped from disk) is documented by other llama.cpp users
  (for example 24 GB VRAM + 32 GB RAM: 25–27 tok/s; 32 GB VRAM + 96 GB RAM: 52 tok/s).
- **Here:** ~39 tok/s with 16 GB VRAM + 32 GB RAM, unpruned model, stock llama.cpp. We did not find published numbers for this combination.

## 2. Failure-triggered thinking (thinking turned on only after real failures) — partly known

- **Known:** switching to a "slow" mode when an agent gets stuck or fails — **SwiftSage** (Lin et al., NeurIPS 2023,
  [arXiv:2305.17390](https://arxiv.org/abs/2305.17390)), with two different models, in text environments.
- **Proposed for coding agents** in *Prompt-Induced Waste in Coding Agents* ([arXiv:2608.01347](https://arxiv.org/abs/2608.01347), 2026):
  there, "evidence-driven escalation" could **not be measured** because their baseline never failed.
- Thinking switches exist (for example Qwen's `enable_thinking`), but they are usually set by hand.
- **Here:** one model; a proxy flips the switch by counting **real** failures in tool results (tests, exit codes, Python/PowerShell errors);
  and a **positive measured result**: 5/5 hard tasks in ~28 minutes on average (4 runs) vs 68 with thinking always on.

## 3. "Democratic" router, and "faster tokens, slower work" — partly known

- **Known:** reducing active experts hurts quality — *Training-Free Halving of Activated Experts*
  ([arXiv:2609.04575](https://arxiv.org/abs/2609.04575)), *Harder Tasks Need More Experts* ([arXiv:2403.07652](https://arxiv.org/abs/2403.07652)),
  *Not All Experts are Equal* ([arXiv:2402.14800](https://arxiv.org/abs/2402.14800)).
- **Here:** on a 512-expert / top-10 MoE, the top 6 experts carry only ~76% of the routing weight (median over 56,304 decisions);
  and the end-to-end measurement that 6–7 experts instead of 10 give +16–25% tokens/s but **2–4x more time to finish a task**.

## 4. A second model in RAM slows the first one — known mechanism, practical measurement

- **Known:** memory pressure evicts the page cache that memory-mapped weights depend on ([justine.lol/mmap](https://justine.lol/mmap/)).
- **Here:** a 4B decision model kept in RAM makes the big model read prompts 2–3x slower (143 vs 317–441 tok/s).

## 5. Kael: an error memory that accepts only fixes proven by a test — mostly known

- *What Should Coding Agents Remember? Selective Retrieval of Validated Repair Experience* (NeurIPS 2026) and work on memory abstention.
  Our difference (the test is re-run at save time) is small. Kael lives in `extras/`.

## Ideas taken from others (with license) and adapted

- Guard (repeated calls, "stop when tests pass", search loops): inspired by [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT), rewritten.
- "Minimal code" rule: [Ponytail](https://github.com/DietrichGebert/ponytail) (MIT).
- Minimal agent/skill profile: [ECC](https://github.com/affaan-m/ECC) (MIT).
- Command output filter: [RTK](https://github.com/rtk-ai/rtk) (Apache-2.0).
- Batch size 2048 for MoE offload: Hugging Face guidance on MoE offloading.
