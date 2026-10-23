# LLM Research Bench: Experimental Evaluation Under Severe VRAM Constraints

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Hardware: GTX 1050 Ti](https://img.shields.io/badge/Hardware-NVIDIA%20GTX%201050%20Ti%204GB-green.svg)](https://www.nvidia.com)

*For Brazilian Portuguese, see [README.pt-BR.md](README.pt-BR.md).*

A reproducible, scientific benchmarking and evaluation suite investigating how small language models (SLMs, 2B–4B parameters), quantization strategies, and speculative decoding techniques behave under strict physical memory limitations ($\le 4096$ MiB VRAM).

Conducted on a dedicated NVIDIA GeForce GTX 1050 Ti (4GB GDDR5, Compute Capability 6.1) inside a Proxmox VE LXC container (CT 108).

---

## 🔬 Core Research Hypotheses

- **H1:** Multi-Token Prediction (MTP) speculative decoding overcomes Pascal architecture memory bandwidth bottlenecks ($112\text{ GB/s}$) by $>100\%$ compared to standard autoregressive generation.
- **H2:** Aggressive quantization (`IQ4_XS` / `Q4_K`) preserves strict function calling (JSON schema) adherence while degrading multi-step arithmetic reasoning.
- **H3:** Dense 4B models saturate $>74\%$ of a 4GB VRAM budget, requiring restricted contexts or KV-cache quantization to prevent Out-Of-Memory (OOM) crashes.
- **H4:** Safety alignment against classic jailbreaks (DAN, weaponized exploit generation) is independent of parameter scale within the 2B–4B range when alignment training is robust.
- **H5:** Agentic tool chaining reliability (e.g. Pulse / MCP) depends on context continuation synthesis, where smaller models may fail to parse prior tool outputs.

---

## 📊 Summary of Findings

| Model | Parameters | Quantization | VRAM Peak | Prompt Eval | Generation | Safety Refusal | Agentic Pulse/MCP | Technical Reasoning |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemma-4-E2B (MTP)** | 2.0B | `IQ4_XS` + `Q8_0` MTP | **1,510 MiB (36.8%)** | **468.2 tok/s** | **46.3 tok/s** | **83.3%** | **Passed (100%)** | 33.3% |
| **Qwen-3.5-2B** | 2.0B | `Q4_K_XL` | 1,598 MiB (39.0%) | 389.5 tok/s | 37.5 tok/s | **83.3%** | **Passed (100%)** | 0.0% |
| **Llama-3.2-3B** | 3.0B | `Q4_K_M` | 2,120 MiB (51.7%) | 390.7 tok/s | 27.4 tok/s | **83.3%** | Failed (Scen. 2) | 33.3% |
| **Qwen-3.5-4B** | 4.0B | `Q4_K_M` | 3,069 MiB (74.9%) | 237.1 tok/s | 18.4 tok/s | **83.3%** | **Passed (100%)** | 33.3% |

---

## 📁 Repository Structure

```
llm-research-bench/
├── configs/
│   └── experiment_matrix.yaml           # Model hyperparameters and benchmark targets
├── datasets/                            # Input prompts for safety, reasoning, and tool calls
├── results/
│   ├── system_performance/              # Throughput, VRAM footprint, TTFT (CSV + JSON)
│   ├── model_quality/                   # Safety, agentic execution, reasoning (CSV + JSON)
│   └── benchmark_comprehensive_results.json # Consolidated empirical trace
├── reports/
│   ├── pt-BR/                           # Brazilian Portuguese LaTeX source & PDF
│   └── en-US/                           # English LaTeX source & PDF
├── src/llm_research_bench/              # Python processing and benchmark suite
├── tests/                               # Unit test verification suite
└── pyproject.toml                       # Build configuration and dependencies
```

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
```

### 2. Run Tests
```bash
python -m unittest discover tests
```

### 3. Recompile Scientific Reports
Using [Tectonic](https://tectonic-typesetting.github.io/):
```bash
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
```

---

## 📜 Full Scientific Reports

- **English Document:** [`reports/en-US/report_en-US.pdf`](reports/en-US/report_en-US.pdf)
- **Portuguese Document:** [`reports/pt-BR/report_pt-BR.pdf`](reports/pt-BR/report_pt-BR.pdf)
- Direct desktop copies are accessible on the operator's workspace.

## ⚖️ License
Released under the [MIT License](LICENSE).
