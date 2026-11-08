# SLM-Limits: LLM Research Bench

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CI](https://github.com/AndersonTavares0/llm-research-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/AndersonTavares0/llm-research-bench/actions/workflows/ci.yml)
[![WCAG 2.2 AA](https://img.shields.io/badge/Accessibility-WCAG_2.2_AA-006D77.svg)](website/)
[![Technical Report (EN)](https://img.shields.io/badge/Technical_Report-PDF_(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Relatório Técnico (PT)](https://img.shields.io/badge/Relat%C3%B3rio_T%C3%A9cnico-PDF_(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)
[![Language: English](https://img.shields.io/badge/Language-English-green.svg)](README.md)
[![Idioma: Português](https://img.shields.io/badge/Idioma-Portugu%C3%AAs-blue.svg)](README.pt-BR.md)

> **Empirical Exploration of Small Language Models (SLMs) Under Severe Hardware Constraints ($\le 4096\text{ MiB}$ VRAM)**<br/>
> An open-source scientific testbed and benchmarking suite investigating inference throughput, VRAM allocation envelopes, speculative decoding (MTP), KV cache scaling, and defensive safety behavior on edge-class physical silicon (NVIDIA GeForce GTX 1050 Ti 4 GB GDDR5).

**Author:** Anderson Tavares (Undergraduate in Software Engineering & Data Science)<br/>
**Project Repository:** [https://github.com/AndersonTavares0/llm-research-bench](https://github.com/AndersonTavares0/llm-research-bench)<br/>
**Interactive Research Platform:** [http://localhost:3000](http://localhost:3000) (Next.js 16 / ECharts / WCAG 2.2 AA)<br/>
**Language:** **English** | [Versão em Português](README.pt-BR.md)

---

> [!NOTE]
> **Scientific Integrity & Disclaimer**<br/>
> This repository is an independent research project focused on reproducible empirical systems engineering. While all experiments adhere to strict monotonic timing, hardware isolation, cryptographic provenance, and fail-closed statistical validation, **this work is not a peer-reviewed journal publication**. Results reflect observed physical behavior on a dedicated Pascal GPU testbed. Historical observations, analytical bounds, and verified measurements are labeled separately according to the project's evidence hierarchy. See [Scientific Integrity & Evidence Hierarchy](#5-methodology-limitations--evolution) and [Research Charter](docs/research/research-charter.md).

---

## Table of Contents

- [1. Overview & Research Scope](#1-overview--research-scope)
- [2. System Architecture & Workflow](#2-system-architecture--workflow)
- [3. Empirical Findings & Research Frontiers](#3-empirical-findings--research-frontiers)
- [4. Getting Started, CLI & Web Platform](#4-getting-started-cli--web-platform)
- [5. Methodology, Limitations & Evolution](#5-methodology-limitations--evolution)

---

## 1. Overview & Research Scope

### What Is SLM-Limits?

**SLM-Limits** is an empirical research bench designed to evaluate **Small Language Models (SLMs, 0.5B to 4B parameters)** executing on legacy, resource-constrained consumer accelerators ($\le 4096\text{ MiB}$ VRAM). Rather than relying on cloud APIs or enterprise-grade datacenter GPUs (A100/H100), this project probes the exact operational limits of running local models directly on physical edge hardware.

### Why the 4 GB GTX 1050 Ti?

The **NVIDIA GeForce GTX 1050 Ti (Pascal GP107, 4096 MiB GDDR5, 128-bit bus, 112 GB/s bandwidth, 75W TDP)** serves as a strict, unforgiving physical boundary:

1. **Rigid Physical VRAM Ceiling:** At 4096 MiB, static model weights consume 15% to 77% of total device memory. Key-Value (KV) cache headroom is constrained, quickly triggering Out-of-Memory (OOM) halts or PCIe memory fallback without aggressive quantization.
2. **Zero Tensor Cores:** The GP107 microarchitecture lacks dedicated matrix accelerators (Tensor Cores). FP16 compute executes at a 1:64 throughput penalty. Consequently, single-batch autoregressive decode is strictly memory-bandwidth bound ($112\text{ GB/s}$).
3. **Realistic Commodity Edge Silicon:** Millions of deployed industrial edge devices, medical appliances, and local workstations operate on Pascal/Turing-era consumer GPUs without hyperscaler cloud connectivity.

### Core Research Questions (RQs)

The research program investigates four interdependent dimensions:

- **Quantization Dynamics:** How do importance-matrix non-uniform quantizations (`IQ4_XS`) compare against standard block formats (`Q4_K_M`) in generation speed and VRAM overhead?
- **Speculative Acceleration:** Can Multi-Token Prediction (MTP) deliver practical throughput gains on memory-bound GPUs without requiring dedicated draft models?
- **KV Cache Physics & Context Degradation:** At what context length does KV cache allocation trigger memory collapse under FP16 vs Q8_0 quantization?
- **Defensive Robustness & Safety:** Can resource-constrained SLMs reliably parse structured formats, execute authorized tool envelopes, and resist context injection attacks?

---

## 2. System Architecture & Workflow

The SLM-Limits architecture is structured into four decoupled layers, ensuring strict hardware isolation, deterministic execution, and complete reproducibility from raw silicon telemetry to publication-grade dissemination.

```mermaid
flowchart TD
    subgraph L1["Layer 1: Physical Hardware & Sandbox Substrate"]
        GPU["NVIDIA GeForce GTX 1050 Ti<br/>4096 MiB GDDR5 · 112 GB/s · 75W TDP"]
        PVE["Proxmox VE Container CT 108<br/>Debian 12 Minimal · Headless · Direct PCI Passthrough"]
        NVML["Hardware Telemetry Monitor<br/>NVML ctypes probe · 250 ms sampling (VRAM, Temp, Drift)"]
        GPU --- PVE
        PVE --- NVML
    end

    subgraph L2["Layer 2: Inference & Serving Engines"]
        LLAMA["llama.cpp Runtime (Pinned b12024)<br/>cuBLAS Offload · llama-server & llama-bench"]
        QUANTS["Quantization Frontiers<br/>Q4_K_M · IQ4_XS · Q8_0 KV Cache"]
        SPEC["Speculative Decoding Engine<br/>Multi-Token Prediction (MTP) Draft Heads"]
        LLAMA --- QUANTS
        LLAMA --- SPEC
    end

    subgraph L3["Layer 3: Evaluation Tracks & Scientific Harnesses"]
        TRACK_A["Track A: Systems & Telemetry<br/>Prefill / Decode tok/s · TTFT · KV Slope · Concurrency"]
        TRACK_B["Track B: Quality & Capability<br/>ARC-Challenge · HellaSwag · GSM8K · IFEval Strict"]
        TRACK_C["Track C: Context & Structured Decoding<br/>Grammar JSON Schema (30/30) · Native Tools · Fertility"]
        TRACK_D["Track D: Defensive Cybersecurity<br/>CWE-10 Triage · NVD 2.0 CVE Advisory · AppSec Harness"]
    end

    subgraph L4["Layer 4: Data Provenance, Artifacts & Dissemination"]
        PROV["Cryptographic Provenance<br/>SHA-256 Hashes · Declarative Manifests"]
        TIER["Strict Evidence Hierarchy<br/>[MEASURED] · [PARTIAL] · [ANALYTICAL] · [READY]"]
        REPORTS["Dual LaTeX Monographs<br/>20p EN / 30p PT compiled via Tectonic"]
        WEB["Interactive Research Dashboard<br/>Next.js 16 · Tailwind · ECharts · WCAG 2.2 AA"]
    end

    L1 -->|Physical Telemetry Traces| L2
    L2 -->|Deterministic Generation (τ = 0.0)| L3
    L3 -->|Raw Evaluation Microdata| L4
```

### Architectural Layer Breakdown

#### 1. Physical Hardware & Sandbox Substrate
- **Isolated Execution Environment:** Experiments run within a minimal Debian 12 Proxmox VE Container (`CT 108`) with exclusive PCI passthrough. No X11 display server, compositor, or desktop background processes run on the host, preventing host VRAM contamination.
- **Asynchronous Telemetry Probe (`telemetry_collector.py`):** Queries native NVML via C-types at 250 ms intervals, logging peak VRAM allocation, memory drift, die temperature, and GPU Boost 3.0 thermal throttling events ($1695 \to 1607\text{ MHz}$).

#### 2. Inference & Serving Engines
- **Pinned Runtime:** Evaluated against `llama.cpp` pinned release `b12024` with native cuBLAS acceleration.
- **Dual Inference Pathways:**
  - *Official Campaign Pipeline (`campaign.py`):* Declarative YAML execution driving `llama-bench` and EleutherAI `lm-eval` with automatic artifact manifest generation.
  - *Telemetry & Microbenchmark Harnesses (`src/llm_research_bench/`):* Micro-profiling TTFT, per-token latency percentiles, KV cache slope, and concurrent slot allocation.

#### 3. Evaluation Tracks
- **Track A (Systems Telemetry):** Throughput scaling, memory bus demand modeling, and concurrency degradation across 1 to 4 parallel slots.
- **Track B (Zero-Shot Capability):** Standardized quality tasks (ARC-Challenge, HellaSwag, GSM8K Flex, IFEval prompt-strict).
- **Track C (Context Dynamics & Tool Calling):** JSON Schema grammar adherence ($30/30$ vs $18/30$ unconstrained), native OpenAI-compatible tool envelopes, and multilingual tokenization fertility.
- **Track D (Defensive Cybersecurity):** Static CWE vulnerability triage, NVD 2.0-verified CVE advisory classification, and role-gated application security guardrails (`defensive_harness.py`).

#### 4. Data Provenance & Dissemination
- **SHA-256 Provenance Verification:** Every evaluated model GGUF file and dataset row is hashed and verified against `datasets/model_provenance.json`.
- **Publication & Visualization:** Findings compile into dual LaTeX monographs (`reports/`) and an accessible, interactive Next.js research portal (`website/`).

---

## 3. Empirical Findings & Research Frontiers

### Master Comparison Table (GTX 1050 Ti Primary Testbed)

All configurations evaluated under single-host greedy sampling ($\tau = 0.0$, $\text{seed} = 42$) on the reference NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, 112 GB/s):

| Model | Architecture | Quantization | Peak VRAM | 4GB Budget | Decode Speed | Steady TTFT | Quality Index | Memory Efficiency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Qwen2.5:0.5B** | Qwen2.5 (0.49B) | `Q4_K_M` | **620.7 MiB** | 15.2% | **97.5 tok/s** | **12.1 ms** | 30.5% | **160.8 tok/s/GiB** |
| **SmolLM2:1.7B** | LLaMA (1.71B) | `Q4_K_M` | 1184.2 MiB | 28.9% | 52.1 tok/s | 78.4 ms | 39.8% | 45.0 tok/s/GiB |
| **Gemma-4:E2B** | Gemma 2 (2.00B) | `IQ4_XS` + **MTP** | 1510.0 MiB | 36.8% | 46.3 tok/s | 115.4 ms | 52.0% | 31.4 tok/s/GiB |
| **Qwen3.5:2B** | Qwen (1.95B) | `Q4_K_XL` | 1598.0 MiB | 39.0% | 37.5 tok/s | 142.1 ms | 45.3% | 24.0 tok/s/GiB |
| **Llama-3.2:3B** | Llama 3.2 (3.21B) | `Q4_K_M` | 2120.0 MiB | 51.7% | 27.4 tok/s | 168.3 ms | 49.0% | 13.2 tok/s/GiB |
| **Qwen3.5:4B** | Qwen (4.02B) | `Q4_K_M` | 3069.0 MiB | 74.9% | 18.4 tok/s | 284.6 ms | **54.0%** | 6.1 tok/s/GiB |

> [!NOTE]
> *Quality Index* represents the arithmetic mean of zero-shot accuracy across ARC-Challenge, HellaSwag, GSM8K (Flex), and IFEval (Prompt-Strict). *Memory Efficiency* measures decode throughput per GiB of allocated VRAM ($\text{tok/s} / \text{GiB}$).

### Controlled Architectural Ablations (Gemma-4-E2B)

Sequential controlled observations on a fixed 2B architecture measured the isolated effects of non-uniform quantization and Multi-Token Prediction (MTP):

```
Throughput (tok/s):
  Baseline Q4_K_M:        [==========================]  26.92 tok/s
  Quantization IQ4_XS:    [==================================]  34.51 tok/s (+28.2%)
  Quant + MTP Speculative:[============================================]  43.35 tok/s (+61.0%)

VRAM Footprint (MiB):
  Baseline Q4_K_M:        [========================================] 1996.7 MiB
  Quantization IQ4_XS:    [====================================]     1800.7 MiB (-196.0 MiB)
  Quant + MTP Speculative:[=========================================] 2036.7 MiB (+40.0 MiB net)
```

- **Quantization Effect:** Importance-matrix `IQ4_XS` reduced static tensor footprint by **196.0 MiB** while boosting decode throughput by **+28.2%** due to lower memory bus traffic.
- **Speculative MTP Effect:** Enabling dual-head MTP draft speculative generation added **+25.6% throughput** ($34.51 \to 43.35\text{ tok/s}$) with an operational buffer cost of **+236.0 MiB**.
- **Net Synergy:** The memory reduction from `IQ4_XS` absorbed **83%** of the MTP memory overhead, producing a net throughput speedup of **+61.0%** for only **+40.0 MiB** of total VRAM.

### KV Cache Physics & Context Limits (H1 Campaign)

- **Memory Slope:** Empirical KV cache consumption scales at **$113.0\text{ KiB/token}$** under FP16 vs **$60.3\text{ KiB/token}$** under `q8_0` quantization.
- **3.8k Safe Horizon:** For 3B models in `Q4_K_M` (weights: ~2.5 GiB), unquantized FP16 KV cache exhausts remaining headroom by ~3,800 tokens, precipitating CUDA OOM. Activating `q8_0` KV cache reduces peak VRAM by **19.6%**, preserving needle retrieval fidelity ($30/30$).

### Structured Outputs & Tool Calling Reliability

- **Constrained vs Unconstrained Decoding:** Grammar-enforced JSON Schema decoding achieved **$30/30$** ($100\%$) schema adherence vs **$18/30$** ($60\%$) for generic `json_object` mode ($12/0$ discordant pairs, McNemar exact $p = 0.000488$).
- **Native vs Mediated Tool Calling:** Native OpenAI-compatible tool envelopes achieved **$18/18$** valid invocations, whereas prompt-mediated JSON tool extraction degraded to $2\text{--}8/18$.

### Multilingual Tokenization Fertility

Evaluating 12 parallel texts across Portuguese, Mandarin, and English revealed severe vocabulary compression disparities:
- **SmolLM2 (49k vocab):** Portuguese fertility ratio of **$2.40\times$** and Mandarin ratio of **$4.59\times$** relative to English, compressing non-English effective context capacity to under $22\%$.
- **Qwen2.5 (151k vocab):** Maintained balanced multilingual fertility ($1.15\times$ for Portuguese, $1.42\times$ for Mandarin), preserving context budget.

### Defensive Cybersecurity Research Track

A dedicated defensive research track implements deterministic offline evaluations without running unauthorized code:
- **Static CWE Triage (v2):** 10 balanced cases covering CWE-78 (command injection), CWE-89 (SQLi), CWE-79 (XSS), CWE-22 (path traversal), CWE-798 (hardcoded credentials), and negative controls.
- **CVE Advisory Vulnerability Triage (v1):** 6 realistic vulnerability advisories mapped against synthetic host software inventories, independently verified with NVD 2.0 and MITRE data.
- **AppSec Chatbot Enforcement Harness (`defensive_harness.py`):** Multi-tenant mock environment evaluating role-gated authorization envelopes to prevent prompt injection and unauthorized API execution.

---

## 4. Getting Started, CLI & Web Platform

### Prerequisites

- **OS:** Linux (Debian 12 / Ubuntu 22.04 LTS recommended)
- **Python:** 3.10+
- **Node.js:** v18+ & `pnpm` (for the interactive web dashboard)
- **Optional Hardware:** NVIDIA GPU with proprietary driver (for live NVML telemetry; mock modes available for offline testing)

### Installation

```bash
# Clone the repository
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e .
```

### Running the Test Suite

```bash
# Run 270+ verified unit, integration, and statistical regression tests
python -m pytest tests/
```

### Running the Interactive Web Platform

The project includes an interactive Next.js 16 research portal featuring Pareto frontier exploration, live telemetry charts, and model comparison matrices:

```bash
# Navigate to website directory
cd website

# Install dependencies and launch development server
pnpm install
pnpm dev
# Or run production build
pnpm build && pnpm start -p 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser. Fully WCAG 2.2 AA accessible across light and dark modes.

### Compiling Technical Monographs

Both publication-grade monographs can be compiled from source using [Tectonic](https://tectonic-typesetting.github.io/):

```bash
# English Monograph (reports/en-US/report_en-US.pdf)
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US

# Portuguese Monograph (reports/pt-BR/report_pt-BR.pdf)
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
```

---

## 5. Methodology, Limitations & Evolution

### Scientific Evidence Hierarchy

To prevent overclaiming, this repository strictly classifies all evidence into five standardized tiers:

- `[MEASURED]`: Empirically recorded microdata collected directly on the physical hardware testbed with full NVML telemetry and monotonic timing.
- `[PARTIAL]`: Valid empirical data collected under pilot protocols or incomplete sample suites.
- `[ANALYTICAL]`: Theoretical derivations, Roofline bounds, or mathematical cache formulas ($B_{\text{demand}} = S_{\text{weights}} \times \text{Throughput}$).
- `[READY]`: Test suites, benchmarks, and defensive harnesses that are fully implemented and deterministically tested, but awaiting hardware execution.
- `[UNKNOWN]`: Hypotheses or configurations not yet investigated on this platform.

### Methodological Boundaries

- **Single-Host Descriptive Observations:** All measurements were collected on a single GTX 1050 Ti host. Repeated queries within a run reflect operational consistency, not independent hardware replicates. Hardware-level inferential statistics (e.g. Welch's t-test) fail closed until multi-machine randomized runs are conducted.
- **Thermal Drift:** Sustained benchmarking raises die temperature from $44^\circ\text{C}$ to $74^\circ\text{C}$, triggering NVIDIA GPU Boost 3.0 downclocking ($-5.2\%$). Automated cooldown periods are enforced between experimental batches.
- **No Hyperscaler Inference:** Results strictly evaluate edge hardware behavior; they do not apply to data-center accelerators with Tensor Cores or high-bandwidth HBM memory.

### Research Charter & Roadmap

The complete research roadmap, including the 22 formal Research Questions (RQs) and experimental priorities (P0–P3), is documented in [`docs/research/research-charter.md`](docs/research/research-charter.md).

---

## Citation & License

If you use this benchmark methodology, dataset, or telemetry traces in your research, please cite:

```bibtex
@article{tavares2026slmlimits,
  title   = {SLM-Limits: Reproducible Evaluation of Small Language Models Under Severe Memory and Compute Constraints},
  author  = {Tavares, Anderson},
  journal = {Open Technical Report and Benchmark Monograph},
  year    = {2026},
  url     = {https://github.com/AndersonTavares0/llm-research-bench}
}
```

This project is open-source software licensed under the **[MIT License](LICENSE)**.

---
*Independent research initiative by Anderson Tavares. Not affiliated with, sponsored by, or endorsed by NVIDIA, Google, Meta, or Alibaba.*
