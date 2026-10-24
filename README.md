# Reproducible Evaluation of Small Language Models Under Severe Memory and Compute Constraints

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Tests: 56 Passing](https://img.shields.io/badge/tests-56%20passing-brightgreen.svg)](tests/)
[![Governance](https://img.shields.io/badge/governance-contributing%20%7C%20security-blue.svg)](CONTRIBUTING.md)
[![Paper: PDF (EN)](https://img.shields.io/badge/Paper-PDF%20(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Paper: PDF (PT)](https://img.shields.io/badge/Artigo-PDF%20(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)

> **Scientific Monograph and Open Benchmark Suite**<br>
> An empirical research investigation on the architectural dynamics, Roofline theoretical limits, non-uniform quantization frontiers, speculative decoding (Multi-Token Prediction), Key-Value cache analytical scaling, and adversarial vulnerabilities of Small Language Models (SLMs) under a rigid $\le 4096\text{ MiB}$ VRAM budget.

**Author:** Anderson Tavares (Undergraduate Student in Software Engineering and Data Science)<br>
**Project Repository:** [https://github.com/AndersonTavares0/llm-research-bench](https://github.com/AndersonTavares0/llm-research-bench)

Para a versão em português desta documentação, consulte [README.pt-BR.md](README.pt-BR.md).

---

## Abstract and Research Scope

Deploying Small Language Models (SLMs, 2B--4B parameters) directly on physical edge hardware guarantees strict data sovereignty, deterministic execution latency, and zero cloud ingress/egress costs. However, operating within severe physical memory limits ($\le 4096\text{ MiB}$ VRAM) exposes fundamental systems engineering trade-offs between tensor quantization precision, memory bus saturation, speculative execution, and adversarial robustness.

This repository provides the complete experimental suite, evaluation harnesses, statistical analysis pipelines, and reproducible scientific articles evaluating seven compact model configurations (**Qwen-2.5-0.5B**, **SmolLM2-1.7B**, **Gemma-4-E2B [MTP]**, **Gemma-4-E2B [Q4_K_M]**, **Qwen-3.5-2B**, **Llama-3.2-3B**, and **Qwen-3.5-4B**).

### Research Questions (RQs) and Hypotheses

1. **RQ1 (Speculative Decoding via MTP):** To what extent does Multi-Token Prediction (MTP) speculative decoding amortize DRAM bandwidth bottlenecks in sub-3B parameter models on memory-bound hardware without dedicated draft models?
   - *Hypothesis $H_1$:* Reusing latent transformer representations via auxiliary linear prediction heads achieves a statistically significant throughput speedup ($S \ge 1.25\times, p < 0.01$, Cohen's $d > 0.8$) without increasing physical VRAM consumption.
2. **RQ2 (Quantization Frontiers and Bus Traffic):** How do non-uniform importance matrix quantizations (`IQ4_XS`) compare against standard block quantizations (`Q4_K_M`) in memory bus saturation and decode throughput on architectures lacking native INT4 tensor arithmetic acceleration?
3. **RQ3 (Key-Value Cache Analytical Limits):** What are the analytical and empirical memory boundaries for context scaling ($L \in [256, 32768]$) under a strict $4096\text{ MiB}$ physical limit, and at what sequence lengths does cache quantization become strictly mandatory?
4. **RQ4 (Adversarial Robustness and Agentic Isolation):** Do compact parameter budgets create an asymmetry between direct attack refusal (exploits, jailbreaks) and indirect context-borne prompt injections through external tools (Model Context Protocol)?

---

## Reference Edge Experimental Testbed

The experimental platform was selected as a **reference edge testbed** representing entry-level and legacy edge accelerators:

- **GPU:** NVIDIA GeForce GTX 1050 Ti (4096\,MiB GDDR5, 128-bit bus, $112.0\text{ GB/s}$ theoretical bandwidth, 75W TDP, Compute Capability 6.1 / Pascal GP107).
- **Host System:** AMD Ryzen 5 3600 (6 cores, 12 threads @ 3.6 GHz base), 16 GiB DDR4 3200 MT/s RAM.
- **Isolated Sandbox:** Dedicated minimal Linux container (Debian 12, kernel 6.8, 2 vCPUs, 4.0 GiB RAM, 512 MiB swap) with direct PCI passthrough, eliminating operating system desktop compositing and background VRAM contention.
- **Inference Runtime:** `llama-server` (commit b4120+) with Flash Attention and cuBLAS offloading.
- **Telemetry Pipeline:** Continuous asynchronous hardware sampling via native C bindings to `libnvidia-ml.so.1` (NVML) at 250\,ms intervals (4 Hz), logging VRAM allocation, GPU core clock, junction temperature, and power draw.

---

## Empirical Benchmark Findings

### 1. Controlled MTP Speculative & Quantization Ablation ($N=10$, 95% Student's $t$ CI)

Evaluated with deterministic greedy decoding ($\tau = 0.0$, `seed=42`) on the physical NVIDIA GeForce GTX 1050 Ti:

| Configuration | Mean Throughput | Std Dev | 95% CI Range | Speedup vs Baseline | Welch's $t$-test ($p$-value) | Peak VRAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B [Q4_K_M Base]** | **26.92 tok/s** | ±0.23 | [26.76, 27.09] tok/s | Baseline ($C_1$) | — | 1996.7 MiB |
| **Gemma-4-E2B [IQ4_XS Base]** | **34.51 tok/s** | ±0.29 | [34.30, 34.72] tok/s | **+28.2%** (Quantization) | $t = 65.41, p = 5.67 \times 10^{-18}$ | 1800.7 MiB |
| **Gemma-4-E2B [IQ4_XS + MTP]** | **43.35 tok/s** | ±0.57 | [42.94, 43.75] tok/s | **+25.6%** (MTP mechanism) | $t = 43.72, p = 7.12 \times 10^{-16}$ | 2036.7 MiB |
| *Compound Comparison ($C_3$ vs $C_1$)* | — | — | — | **+61.0%** (Compound) | $t = 84.50, p = 5.88 \times 10^{-18}$ | +40.0 MiB |

- **Effect Decomposition:** Holding decoding constant, IQ4_XS weight compression provides a $+28.2\%$ throughput gain. Holding quantization constant in IQ4_XS, MTP speculative decoding delivers a $+25.6\%$ associated speedup ($43.35 \pm 0.57$ vs $34.51 \pm 0.29$\,tok/s, $t = 43.72$, Cohen's $d = 19.55$). The compound configuration speedup is $+61.03\%$ ($t = 84.50$, Cohen's $d = 37.79$).
- **Draft Acceptance Dynamics:** Runtime telemetry logged empirical draft acceptance rate $\alpha = 52.8\%$ (65 tokens accepted out of 123 generated), with mean accepted block length $\bar{L} = 2.05$ tokens per validation pass.
- **VRAM Allocation Dynamics:** The additional VRAM allocation associated with the MTP mechanism is $+236.0\text{ MiB}$ ($C_3$ vs $C_2$, 2036.7 vs 1800.7 MiB) for Q8_0 draft heads, speculative KV cache, and verification buffers. This yields a net $+40.0\text{ MiB}$ difference relative to baseline $C_1$ (2036.7 vs 1996.7 MiB) because the $196.0\text{ MiB}$ weight compression savings of IQ4_XS offset 83% of the MTP draft head footprint.

### 2. Cross-Model Empirical Performance on Physical GTX 1050 Ti ($N=10$, $\tau=0.0$)

| Model and Quantization | Parameters (B) | Peak VRAM (MiB) | Budget (% 4 GiB) | Prefill (tok/s) | Decode (tok/s) | TTFT (ms) | Memory Efficiency (tok/s/GiB) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B-Q4_K_M** | 0.49 | 620.7 | 15.2% | 237.1 ± 449.3 | **97.5 ± 0.6** | **12.1 ± 5.0** | **160.8** |
| **SmolLM2-1.7B-Q4_K_M** | 1.71 | 2902.7 | 70.9% | 103.3 ± 176.0 | 47.8 ± 0.1 | 25.5 ± 14.3 | 16.9 |
| **Gemma-4-E2B [MTP IQ4_XS]** | 2.30 | 2036.7 | 49.7% | 62.2 ± 18.5 | **43.4 ± 0.6** | 480.4 ± 1286.7 | 21.8 |
| **Gemma-4-E2B [IQ4_XS base]** | 2.00 | 1800.7 | 44.0% | 79.2 ± 32.4 | 34.5 ± 0.3 | 88.0 ± 49.0 | 19.6 |
| **Gemma-4-E2B [Q4_K_M base]** | 2.00 | 1996.7 | 48.7% | 65.5 ± 7.7 | 26.9 ± 0.2 | 116.1 ± 116.3 | 13.8 |
| **Qwen-3.5-2B-Q4_K_XL** | 1.95 | 1580.7 | 38.6% | 126.5 ± 108.8 | 37.6 ± 0.1 | 49.9 ± 20.3 | 24.4 |
| **Llama-3.2-3B-Q4_K_M** | 3.21 | 3074.7 | 75.1% | 59.6 ± 101.1 | 27.6 ± 0.0 | 43.5 ± 23.1 | 9.2 |
| **Qwen-3.5-4B-Q4_K_M** | 4.02 | 3140.7 | 76.7% | 49.3 ± 46.5 | 18.6 ± 0.1 | 129.8 ± 45.3 | 6.1 |

*Note:* Peak VRAM recorded in binary MiB ($1024^2$ bytes) via native NVML ctypes calls; includes weights, active KV cache, and 256 MiB CUDA driver allocation. Confidence intervals are bounded non-negative for physical latency and throughput. Memory efficiency is defined as $\eta_{\text{mem}} = \text{Throughput} / \text{VRAM}_{\text{GiB}}$.

### 3. Defensive Safety Robustness, Algorithmic Bias, and Parallel Tokenizer Fertility ($N=10$, $\tau=0.0$)

| Model | Over-Refusal (FPR %) | Indirect Injection (ASR %) | Delimiter Breach (ASR %) | Tool Guardrail (ASR %) | BBQ/Stereo Neutrality | Portuguese Fertility (tok/w) | English Fertility (tok/w) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B** | **0.0%** | **0.0%** | 50.0% | 100.0% | 66.7% | 1.74 | **1.10** |
| **SmolLM2-1.7B** | **0.0%** | **0.0%** | 50.0% | **0.0%** | 33.3% | 2.33 | **1.10** |
| **Gemma-4-E2B [MTP]** | **0.0%** | **0.0%** | 100.0% | 100.0% | **100.0%** | **1.35** | **1.10** |
| **Gemma-4-E2B [Q4_K_M]** | **0.0%** | 50.0% | 50.0% | 100.0% | **100.0%** | **1.35** | **1.10** |
| **Qwen-3.5-2B** | **0.0%** | 50.0% | 100.0% | 100.0% | 66.7% | 1.37 | **1.10** |
| **Llama-3.2-3B** | **0.0%** | **0.0%** | 50.0% | 100.0% | 66.7% | 1.74 | **1.10** |
| **Qwen-3.5-4B** | **0.0%** | 100.0% | 100.0% | 100.0% | 66.7% | 1.37 | **1.10** |

*Note:* In tool calling scenarios, 100% ASR reflects that the model generated valid JSON schema tool invocations containing the injected malicious parameters; all invocations were intercepted and blocked by the evaluation harness (`BLOCKED_BY_HARNESS`) with full serialized payload logged in `raw_response`.

### 4. Verified Model Provenance and Cryptographic Hashes (SHA-256)

| Model Identifier | File Name | Size (MiB) | Context | Verified SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| `qwen2.5-0.5b` | `qwen2.5-0.5b-instruct-q4_k_m.gguf` | 379.3 | 16,384 | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` |
| `smollm2-1.7b` | `smollm2-1.7b-instruct-q4_k_m.gguf` | 1009.1 | 16,384 | `decd2598bc2c8ed08c19adc3c8fdd461ee19ed5708679d1c54ef54a5a30d4f33` |
| `gemma4:Q4KM` | `gemma4-e2b-q4km.gguf` | 1351.9 | 16,384 | `6dd7ac24fe13a238898e16e253ebc7a72fa27fb83f2658c2f6c241df3af5937d` |
| `gemma4:MTP` | `gemma-4-E2B-it-IQ4_XS.gguf` | 1185.6 | 16,384 | `c149620926221669c4941ae6dac259953cc729c48e4a4edb69e9807b782fd1e3` |
| `gemma4:E2B` | `mtp-gemma-4-E2B-it-Q8_0.gguf` | 1225.6 | 16,384 | `9eba819938efccfd6044f8af84e3bbfddc639a2bcf32ebc36420e6a649191919` |
| `qwen3.5:2B` | `Qwen3.5-2B-UD-Q4_K_XL.gguf` | 1331.2 | 16,384 | `9f7b15d04cf2d5878c8122a7c181dbc09f050cd66080ce3374576e734ccb0910` |
| `llama3.2:3B` | `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | 1925.9 | 16,384 | `6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff` |
| `qwen3.5:4B` | `Qwen3.5-4B-Q4_K_M.gguf` | 2458.2 | 16,384 | `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4` |

### 4. Architectural Feasibility Survey and Physical Limits Under 4 GiB VRAM

| Candidate Model | Vendor / License | Parameters (B) | Weights Q4_K_M (MiB) | KV Cache 4k (FP16) | Total VRAM (4k Context) | Physical Status on GTX 1050 Ti |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B** | Alibaba (Apache-2.0) | 0.49 | 469 | 112 MiB | 837 MiB | **Evaluated:** Full feasibility (20.4% ceiling) |
| **Qwen-2.5-1.5B** | Alibaba (Apache-2.0) | 1.54 | 986 | 224 MiB | 1,466 MiB | **Feasible:** High headroom for 16k context |
| **SmolLM2-1.7B** | HuggingFace (Apache) | 1.71 | 1,007 | 192 MiB | 1,455 MiB | **Evaluated:** High memory efficiency |
| **Granite-3.1-2B** | IBM (Apache-2.0) | 2.50 | 1,580 | 320 MiB | 2,156 MiB | **Feasible:** Native long context support |
| **Phi-4-mini-3.8B** | Microsoft (Gated) | 3.82 | 2,510 | 512 MiB | 3,278 MiB | **Non-Executable:** Gated repository (HTTP 401) |
| **Gemma-3-1B** | Google (Gemma) | 1.20 | 880 | 384 MiB | 1,520 MiB | **Feasible:** Low static allocation |
| **Gemma-3-4B** | Google (Gemma) | 4.30 | 2,950 | 1,152 MiB | 4,358 MiB | **Physical Block:** OOM under FP16 KV (4358 MiB); requires Q4_0 KV (3494 MiB) |

## Hardware-Specific Limits vs. Generalizable Principles

| Dimension | Hardware-Specific Observation (GTX 1050 Ti) | Generalizable Architectural Principle |
| :--- | :--- | :--- |
| **Decode Throughput** | $18.4$--$46.3$\,tok/s constrained by 128-bit GDDR5 bus ($112.0\text{ GB/s}$) | Autoregressive generation is universally memory-bound ($I_{\text{decode}} \ll I^*$) on any accelerator |
| **MTP Speedup** | $+25.6\%$ associated speedup under constant quantization ($+28.2\%$ from IQ4_XS quantization, $+61.0\%$ compound) | Speedup formula $S = \frac{1 + \sum \alpha^k}{1 + \mathcal{O}_{\text{draft}}}$ holds whenever draft acceptance exceeds overhead |
| **KV Cache Scaling** | OOM triggered at $>8\text{k}$ context for 4B models in 4 GiB VRAM | Uncompressed KV cache scales strictly as $\mathcal{O}(L)$; context scaling requires cache quantization |
| **Alignment Boundary** | 0% refusal against log-embedded canary payload | RLHF/DPO fails architecturally to isolate system instructions from untrusted tool context tokens |

---

## Repository Architecture

```
llm-research-bench/
├── configs/
│   ├── experiment_matrix.yaml           # Systematic experimental parameters
│   └── models.ini                       # Inference runtime profiles
├── datasets/
│   ├── gsm8k_50.json                    # Mathematical reasoning evaluation subset
│   ├── arc_challenge_50.json            # Scientific reasoning evaluation subset
│   ├── safety_prompts.json              # Direct adversarial evaluation prompts
│   ├── reasoning_prompts.json           # Quantitative technical benchmarks
│   └── agentic_tools.json               # JSON Schema tool definitions
├── results/
│   ├── controlled_experiments/          # Empirical trace logs from N=15 ablation runs
│   ├── system_performance/              # Asynchronous NVML telemetry CSVs and JSONs
│   ├── model_quality/                   # Adversarial and agentic benchmark records
│   └── benchmark_comprehensive_results.json # Consolidated raw empirical dataset
├── reports/
│   ├── figures/                         # Vector PDF figures generated from real data
│   ├── en-US/                           # English academic monograph (report_en-US.tex / .pdf)
│   └── pt-BR/                           # Portuguese academic monograph (report_pt-BR.tex / .pdf)
├── src/llm_research_bench/
│   ├── evaluators/                      # Modular evaluation suite
│   │   ├── base_evaluator.py            # Abstract BaseEvaluator interface
│   │   ├── safety_evaluator.py          # StrongREJECT/HarmBench rubric evaluator
│   │   ├── code_evaluator.py            # HumanEval+/MBPP+ sandboxed AST executor
│   │   ├── math_evaluator.py            # GSM8K/MATH-500 numerical evaluator
│   │   ├── agent_evaluator.py           # BFCL/AgentDojo schema & canary evaluator
│   │   ├── long_context_evaluator.py    # RULER needle-in-a-haystack evaluator
│   │   └── knowledge_evaluator.py       # TruthfulQA/MMLU-Pro choice & trap evaluator
│   ├── systems/                         # Hardware and memory analytical profilers
│   │   ├── kv_cache_profiler.py         # KV cache memory & OOM boundary calculator
│   │   └── concurrency_profiler.py      # Concurrency scaling & queuing profiler
│   ├── ablation_runner.py               # Controlled ablation harness with N repetitions
│   ├── quant_runner.py                  # Quantization impact measurement runner
│   ├── telemetry_collector.py           # Native NVML ctypes telemetry sampler (250 ms loop)
│   ├── statistical_analysis.py          # SciPy inferential engine (Welch t-test, Cohen d)
│   ├── statistical_engine.py            # Student's t 95% confidence interval engine
│   ├── generate_figures.py              # Publication-grade vector PDF chart generator
│   └── mcp_server.py                    # Standard JSON-RPC 2.0 stdio MCP server
├── tests/                               # Comprehensive unit test suite (56 tests)
└── pyproject.toml                       # Python package configuration
```

---

## Reproducing the Experiments

### 1. Installation

```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
pip install matplotlib scipy numpy
```

### 2. Run Test Suite

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Run Controlled MTP Ablation

```bash
python src/llm_research_bench/ablation_runner.py --base-url http://127.0.0.1:18081 --repetitions 5
```

### 4. Regenerate Vector Charts

```bash
python src/llm_research_bench/generate_figures.py
```

### 5. Compile LaTeX Scientific Papers

```bash
# Using Tectonic (zero dependencies, self-contained)
tectonic reports/en-US/report_en-US.tex
tectonic reports/pt-BR/report_pt-BR.tex
```

---

## Citation

If you use this benchmark suite, empirical data, or methodology in your research, please cite:

```bibtex
@article{tavares2026slmbench,
  title   = {Reproducible Evaluation of Small Language Models Under Severe Memory and Compute Constraints: Architectural Dynamics, Quantization Frontiers, Speculative Decoding, and Adversarial Vulnerabilities on a Reference Edge Testbed},
  author  = {Tavares, Anderson},
  journal = {Open Technical Report and Benchmark Monograph},
  year    = {2026},
  url     = {https://github.com/AndersonTavares0/llm-research-bench}
}
```

---

## License

This project and its evaluation datasets are licensed under the [MIT License](LICENSE).
