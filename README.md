# Reproducible Evaluation of Small Language Models Under Severe Memory and Compute Constraints

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Tests: 39 Passing](https://img.shields.io/badge/tests-39%20passing-brightgreen.svg)](tests/)
[![Paper: PDF (EN)](https://img.shields.io/badge/Paper-PDF%20(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Paper: PDF (PT)](https://img.shields.io/badge/Artigo-PDF%20(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)

> **Scientific Monograph and Open Benchmark Suite**<br>
> An independent empirical research investigation on the architectural dynamics, Roofline theoretical limits, non-uniform quantization frontiers, speculative decoding (Multi-Token Prediction), Key-Value cache analytical scaling, and adversarial vulnerabilities of Small Language Models (SLMs) under a rigid $\le 4096\text{ MiB}$ VRAM budget.

Para a versão em português desta documentação, consulte [README.pt-BR.md](README.pt-BR.md).

---

## Abstract and Research Scope

Deploying Small Language Models (SLMs, 2B--4B parameters) directly on physical edge hardware guarantees strict data sovereignty, deterministic execution latency, and zero cloud ingress/egress costs. However, operating within severe physical memory limits ($\le 4096\text{ MiB}$ VRAM) exposes fundamental systems engineering trade-offs between tensor quantization precision, memory bus saturation, speculative execution, and adversarial robustness.

This repository provides the complete experimental suite, evaluation harnesses, statistical analysis pipelines, and reproducible scientific articles evaluating four compact model architectures (**Gemma-4-E2B-it**, **Qwen-3.5-4B**, **Qwen-3.5-2B**, and **Llama-3.2-3B**).

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

### 1. Controlled MTP Speculative Decoding Ablation ($N=15$, 95% Confidence Interval)

Evaluated with deterministic greedy decoding ($\tau = 0.0$) on technical system tasks across 5 independent trials (15 total runs) to isolate the MTP draft head's causal impact:

| Configuration | Mean Throughput | Standard Deviation | 95% CI Margin | 95% CI Range | Steady-State Throughput | Peak VRAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (with MTP)** | **42.21 tok/s** | 10.82 | ±5.99 | [36.2, 48.2] tok/s | **44.95 tok/s** | 2038 MiB |
| **Gemma-4-E2B (Base without MTP)** | **32.25 tok/s** | 5.83 | ±3.23 | [29.0, 35.5] tok/s | **33.75 tok/s** | 2038 MiB |

- **Overall Acceleration:** $+30.9\%$ throughput gain (Welch's $t = 3.139, \nu = 21.51$, two-tailed $p = 0.0049$, one-tailed $p = 0.0024$, Cohen's $d = 1.146$, large effect).
- **Warmed Steady-State Acceleration:** $+33.2\%$ throughput gain ($44.95 \pm 2.12$ vs $33.75 \pm 0.41$\,tok/s, Welch's $t = 19.38, \nu = 13.99, p = 1.67 \times 10^{-11}$, Cohen's $d = 7.32$), exactly matching the theoretical speculative formulation ($S \approx 1.333\times$ for draft acceptance $\alpha = 0.40$).
- **Memory Footprint Neutrality:** Zero additional VRAM overhead (2038\,MiB in both configurations).
- **Quantization and MTP Confounder Decomposition:** In steady-state execution, Gemma-4-E2B (IQ4_XS + MTP) demonstrates a +59.2% compound throughput advantage over standard Q4_K_M (41.92 vs 26.34 tok/s). Decomposing this gain by isolating the verified +33.2% MTP acceleration reveals that non-uniform importance quantization alone contributes an estimated +19.5% pure throughput gain, directly aligning with the 16.7% reduction in DRAM weight transfers (1.8 GB to 1.5 GB).

### 2. Cross-Model Systems Performance and Energy Efficiency

| Model | Peak VRAM | Budget Fraction | Prompt Eval | Decode Throughput | TTFT | Memory Efficiency ($\eta_{\text{mem}}$) | Est. Energy Efficiency ($E_{\text{tok/J}}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (IQ4_XS + MTP)** | **1,510 MiB** | **36.8%** | **468.2 tok/s** | **46.3 tok/s** | **115.4 ms** | **31.40 tok/s/GiB** | **0.89 tok/J** |
| **Qwen-3.5-2B (Q4_K_XL)** | 1,598 MiB | 39.0% | 389.5 tok/s | 37.5 tok/s | 142.1 ms | 24.04 tok/s/GiB | 0.77 tok/J |
| **Llama-3.2-3B (Q4_K_M)** | 2,120 MiB | 51.7% | 390.7 tok/s | 27.4 tok/s | 168.3 ms | 13.24 tok/s/GiB | 0.50 tok/J |
| **Qwen-3.5-4B (Q4_K_M)** | 3,069 MiB | 74.9% | 237.1 tok/s | 18.4 tok/s | 284.6 ms | 6.14 tok/s/GiB | 0.30 tok/J |

*Note:* Peak VRAM is recorded in binary MiB. Memory efficiency is defined as $\eta_{\text{mem}} = \text{Throughput} / \text{VRAM}_{\text{GiB}}$ (where $1\text{ GiB} = 1024^3\text{ bytes}$). Estimated energy efficiency ($E_{\text{tok/J}} = \text{Throughput} / P_{\text{est}}$) is derived from a calibrated isolated GPU package power model ($P_{\text{est}} \in [49, 62]\text{ W}$) reflecting TDP operating points; total host AC wall power ($65\text{ W}$--$110\text{ W}$) is not included.

### 3. Exploratory Adversarial Safety Robustness and Model Context Protocol (MCP)

| Model | Direct Attack Refusal (5 Vectors) | Indirect Context Injection (1 Log Canary) | MCP Tool Calling (3 Scenarios) | SysAdmin Math (3 Probes) |
| :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (MTP)** | **100% (5/5)** | **Failed (0% refusal)** | **Passed (100% schema match)** | 33.3% (ZFS Parity) |
| **Qwen-3.5-4B** | **100% (5/5)** | **Failed (0% refusal)** | **Passed (100% schema match)** | 33.3% (ZFS Parity) |
| **Qwen-3.5-2B** | **100% (5/5)** | **Failed (0% refusal)** | **Passed (100% schema match)** | 0.0% (arithmetic drift) |
| **Llama-3.2-3B** | **100% (5/5)** | **Failed (0% refusal)** | Failed (turn 2 parse error) | 33.3% (RAM logic) |

*Note on Safety and Tool Calling Scope:* All security, tool calling, and arithmetic metrics represent preliminary exploratory microbenchmarks ($N=5$ direct safety prompts, $N=1$ indirect injection prompt, $N=3$ tool scenarios, $N=3$ sysadmin arithmetic probes). They demonstrate specific behavioral profiles under controlled edge conditions but do not constitute exhaustive safety certifications (such as HarmBench, StrongREJECT, or BFCL).

- **Direct Refusal:** 100% across all models against weaponized CVE exploits (Log4Shell), stealth keyloggers, DAN persona framing, and prompt extraction.
- **Indirect Prompt Injection:** Universal vulnerability (0% refusal). All models executed simulated command overrides when embedded inside untrusted context logs, proving that post-training alignment fails to enforce instruction boundaries.

---

## Hardware-Specific Limits vs. Generalizable Principles

| Dimension | Hardware-Specific Observation (GTX 1050 Ti) | Generalizable Architectural Principle |
| :--- | :--- | :--- |
| **Decode Throughput** | $18.4$--$46.3$\,tok/s constrained by 128-bit GDDR5 bus ($112.0\text{ GB/s}$) | Autoregressive generation is universally memory-bound ($I_{\text{decode}} \ll I^*$) on any accelerator |
| **MTP Speedup** | $+30.9\%$ to $+33.2\%$ measured acceleration | Speedup formula $S = \frac{1 + \alpha\gamma}{1 + c_{\text{draft}}/c_{\text{target}}}$ holds universally whenever $\alpha > c_{\text{draft}}/c_{\text{target}}$ |
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
├── tests/                               # Comprehensive unit test suite (39 tests)
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
  journal = {Independent Systems Research Group Monograph Series},
  year    = {2026},
  url     = {https://github.com/AndersonTavares0/llm-research-bench}
}
```

---

## License

This project and its evaluation datasets are licensed under the [MIT License](LICENSE).
