# Contributing to llm-research-bench

Thank you for your interest in contributing to **llm-research-bench**, an open scientific research suite evaluating Small Language Models (SLMs) under severe memory and compute constraints ($\le 4096\text{ MiB}$ VRAM).

This project follows an evidence-first, reproducible methodology. All empirical claims, analytical bounds, and statistical derivations must be verifiable against raw datasets, code implementations, or authoritative academic literature.

---

## 1. Governance and Maintainer Model

This repository is maintained by an **individual maintainer** (@AndersonTavares0). As a solo-maintained research project:
- Pull requests are reviewed and merged directly by the maintainer.
- Branch protection requires automated CI checks (`test` and `compile-reports`) to be green before merging into `main`.
- We welcome external contributions, issue reports, model evaluations, and benchmark extensions that adhere to our scientific and ethical guidelines.

---

## 2. Code of Conduct

All contributors and participants are expected to adhere to the [Code of Conduct](CODE_OF_CONDUCT.md) (Contributor Covenant v2.1). Please read it before participating.

---

## 3. Development Workflow

### Prerequisites
- Python 3.10+ (tested on 3.11 and 3.14)
- Git
- [Tectonic](https://tectonic-typesetting.github.io/) LaTeX engine (for compiling scientific monographs)

### Setting Up the Environment

```bash
# Clone the repository
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### Running Tests

We enforce a strict 100% test pass requirement. Run both test runners before submitting any code:

```bash
# Standard library unittest
python -m unittest discover -s tests -p "test_*.py" -v

# Pytest (mirrors GitHub Actions CI runner)
python -m pytest tests/ -v
```

### Compiling Scientific Monographs

Whenever editing monograph sources in `reports/`, compile and inspect both languages:

```bash
# Portuguese monograph
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR

# English monograph
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US
```
Ensure zero compilation errors and zero layout overflow (`Overfull \hbox`).

---

## 4. Proposing New Models or Benchmarks

When proposing new Small Language Models for inclusion:
1. **Model Criteria:** Dense or MoE models that fit within a 4 GiB VRAM envelope (typically $\le 4\text{B}$ parameters in Q4_K_M/IQ4 quantizations).
2. **Official Sources:** Cite official Hugging Face repositories, permissive licenses (MIT, Apache 2.0, Gemma, Llama Community), and verified GGUF architecture support in `llama.cpp`.
3. **No Fabricated Benchmarks:** If physical hardware benchmarks have not been executed, the model must be cataloged in `configs/experiment_matrix.yaml` and `configs/models.ini` under the candidate catalog with analytical memory formulas, clearly distinguished from laboratory measurements.
4. **Issue Template:** Use the [Model Addition Template](.github/ISSUE_TEMPLATE/model_addition.yml).

---

## 5. Security and Ethical Research

This project adheres to the [Security Policy](SECURITY.md). All adversarial safety evaluations, jailbreak robustness probes, and injection benchmarks must use **synthetic, isolated, and authorized test cases**. Never execute exploits or penetration payloads against live production infrastructure or third-party networks.

---

## 6. Pull Request Process

1. Create a dedicated feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```
2. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: ...` for new capabilities
   - `fix: ...` for bug fixes
   - `docs: ...` for documentation or monograph updates
   - `test: ...` for test additions
3. Verify that `git diff --check` reports zero whitespace errors.
4. Push your branch and open a Pull Request using the [PR Template](.github/PULL_REQUEST_TEMPLATE.md).
5. Ensure all automated CI checks (`test` and `compile-reports`) pass.
