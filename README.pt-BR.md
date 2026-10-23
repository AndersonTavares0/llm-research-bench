# LLM Research Bench: Pesquisa Experimental sob Restrições Severas de VRAM

[![Licença: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Hardware: GTX 1050 Ti](https://img.shields.io/badge/Hardware-NVIDIA%20GTX%201050%20Ti%204GB-green.svg)](https://www.nvidia.com)

*Para a versão em Inglês, consulte o [README.md](README.md).*

Uma suíte científica e reprodutível de benchmarking e experimentação que investiga como Modelos de Linguagem Pequenos (SLMs, 2B–4B parâmetros), estratégias de quantização e decodificação especulativa se comportam sob restrições físicas de memória de vídeo ($\le 4096$ MiB de VRAM).

Executado em uma GPU NVIDIA GeForce GTX 1050 Ti dedicada (4GB GDDR5, Compute Capability 6.1) em contêiner Proxmox VE LXC (CT 108).

---

## 🔬 Hipóteses Centrais da Pesquisa

- **H1:** A decodificação especulativa com Multi-Token Prediction (MTP) supera o gargalo de largura de banda de memória da arquitetura Pascal ($112\text{ GB/s}$) em $>100\%$ em relação à geração autorregressiva tradicional.
- **H2:** A quantização agressiva (`IQ4_XS` / `Q4_K`) preserva estritamente a conformidade com esquemas de chamada de função agêntica (JSON Schema), mas compromete a precisão de raciocínio aritmético em múltiplas etapas.
- **H3:** Modelos densos de 4B parâmetros ocupam $>74\%$ do orçamento de 4GB de VRAM, demandando janelas de contexto restritas ou quantização do cache KV para prevenir falhas por falta de memória (OOM).
- **H4:** O alinhamento de segurança contra jailbreaks clássicos (DAN, solicitação de exploits) independe da escala de parâmetros na faixa de 2B a 4B quando o fine-tuning de segurança na origem é bem executado.
- **H5:** A confiabilidade no encadeamento de ferramentas agênticas (ex.: Pulse / MCP) depende da capacidade de sintetizar continuações de contexto, onde modelos menores frequentemente falham ao analisar retornos anteriores de ferramentas.

---

## 📊 Síntese dos Resultados Empíricos

| Modelo | Parâmetros | Quantização | Pico de VRAM | Prompt Eval | Geração | Recusa de Segurança | Agência Pulse/MCP | Raciocínio Técnico |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemma-4-E2B (MTP)** | 2.0B | `IQ4_XS` + `Q8_0` MTP | **1.510 MiB (36,8%)** | **468,2 tok/s** | **46,3 tok/s** | **83,3%** | **Aprovado (100%)** | 33,3% |
| **Qwen-3.5-2B** | 2.0B | `Q4_K_XL` | 1.598 MiB (39,0%) | 389,5 tok/s | 37,5 tok/s | **83,3%** | **Aprovado (100%)** | 0,0% |
| **Llama-3.2-3B** | 3.0B | `Q4_K_M` | 2.120 MiB (51,7%) | 390,7 tok/s | 27,4 tok/s | **83,3%** | Reprovado (Cen. 2) | 33,3% |
| **Qwen-3.5-4B** | 4.0B | `Q4_K_M` | 3.069 MiB (74,9%) | 237,1 tok/s | 18,4 tok/s | **83,3%** | **Aprovado (100%)** | 33,3% |

---

## 📁 Estrutura do Repositório

```
llm-research-bench/
├── configs/
│   └── experiment_matrix.yaml           # Matriz experimental e hiperparâmetros
├── datasets/                            # Prompts de segurança, raciocínio e chamada de ferramentas
├── results/
│   ├── system_performance/              # Vazão, alocação de VRAM e TTFT (CSV + JSON)
│   ├── model_quality/                   # Segurança, execução agêntica e raciocínio (CSV + JSON)
│   └── benchmark_comprehensive_results.json # Tráfego empírico consolidado
├── reports/
│   ├── pt-BR/                           # Código-fonte LaTeX e PDF em Português
│   └── en-US/                           # Código-fonte LaTeX e PDF em Inglês
├── src/llm_research_bench/              # Pacote Python de processamento e benchmarking
├── tests/                               # Bateria de testes unitários
└── pyproject.toml                       # Especificação do pacote e dependências
```

---

## 🚀 Como Executar

### 1. Instalação do Ambiente
```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
```

### 2. Validação com Testes Unitários
```bash
python -m unittest discover tests
```

### 3. Compilação dos Relatórios Científicos
Utilizando o motor [Tectonic](https://tectonic-typesetting.github.io/):
```bash
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US
```

---

## 📜 Relatórios Científicos Completos

- **Documento em Português:** [`reports/pt-BR/report_pt-BR.pdf`](reports/pt-BR/report_pt-BR.pdf)
- **Documento em Inglês:** [`reports/en-US/report_en-US.pdf`](reports/en-US/report_en-US.pdf)
- Cópias diretas em PDF estão disponíveis na Área de Trabalho do operador.

## ⚖️ Licença
Distribuído sob os termos da licença [MIT](LICENSE).
