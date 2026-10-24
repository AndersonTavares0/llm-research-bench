# Avaliação Reproduzível de Modelos de Linguagem Compactos sob Restrições Severas de Memória e Computação

[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Testes: 39 Passando](https://img.shields.io/badge/testes-49%20passando-brightgreen.svg)](tests/)
[![Governança](https://img.shields.io/badge/governan%C3%A7a-contributing%20%7C%20security-blue.svg)](CONTRIBUTING.md)
[![Artigo: PDF (EN)](https://img.shields.io/badge/Paper-PDF%20(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Artigo: PDF (PT)](https://img.shields.io/badge/Artigo-PDF%20(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)

> **Monografia Científica e Suíte Aberta de Avaliação**<br>
> Uma investigação empírica independente sobre a dinâmica arquitetural, limites teóricos Roofline, fronteiras de quantização não homogênea, decodificação especulativa (Multi-Token Prediction), escalonamento analítico do cache Chave-Valor (KV) e vulnerabilidades adversariais de Modelos de Linguagem Compactos (SLMs) sob um teto rígido de $\le 4096\text{ MiB}$ de VRAM.

For the English version of this documentation, see [README.md](README.md).

---

## Resumo e Escopo da Pesquisa

A implantação de Modelos de Linguagem Pequenos (SLMs, 2B--4B parâmetros) diretamente em hardware físico de borda garante estrita soberania de dados, latência determinística e eliminação de custos de tráfego de nuvem. Contudo, operar sob limites rígidos de memória física ($\le 4096\text{ MiB}$ de VRAM) impõe compromissos fundamentais de engenharia de sistemas entre precisão de quantização, saturação do barramento de memória, execução especulativa e robustez adversarial.

Este repositório fornece a suíte experimental completa, os ambientes de avaliação, os pipelines de análise estatística e os artigos científicos reproduzíveis avaliando sete configurações compactas (**Qwen-2.5-0.5B**, **SmolLM2-1.7B**, **Gemma-4-E2B [MTP]**, **Gemma-4-E2B [Q4_K_M]**, **Qwen-3.5-2B**, **Llama-3.2-3B** e **Qwen-3.5-4B**).

### Perguntas de Pesquisa (RQs) e Hipóteses

1. **RQ1 (Decodificação Especulativa via MTP):** Em que extensão a decodificação especulativa por predição de múltiplos tokens (*Multi-Token Prediction* - MTP) mitiga o gargalo de largura de banda de memória em modelos compactos ($<3\text{B}$) em hardware limitado por memória sem modelos rascunho dedicados?
   - *Hipótese $H_1$:* A reutilização de representações latentes por cabeças lineares secundárias alcança aceleração estatisticamente significante ($S \ge 1,25\times, p < 0,01$, $d$ de Cohen $> 0,8$) sem elevar a alocação física de VRAM.
2. **RQ2 (Fronteiras de Quantização e Tráfego de Barramento):** Como quantizações por matriz de importância não homogênea (`IQ4_XS`) se comparam à quantização em blocos padrão (`Q4_K_M`) em termos de saturação de barramento e throughput em arquiteturas sem aceleração de tensores inteiros em hardware?
3. **RQ3 (Limites Analíticos do Cache Chave-Valor):** Quais são os limites analíticos e empíricos de memória para escalonamento de contexto ($L \in [256, 32768]$) sob o teto estrito de $4096\text{ MiB}$, e em que comprimentos de sequência a quantização do cache torna-se estritamente mandatória?
4. **RQ4 (Robustez Adversarial e Isolamento Agêntico):** Sob restrições de escala de parâmetros, modelos compactos exibem assimetria na defesa contra ataques diretos (exploits, jailbreaks) versus injeções indiretas de prompt conduzidas por ferramentas e contexto externo (Model Context Protocol)?

---

## Bancada Experimental de Referência

A plataforma de testes foi adotada como **bancada experimental de referência** representativa de aceleradores de entrada e de borda legados:

- **GPU:** NVIDIA GeForce GTX 1050 Ti (4096\,MiB GDDR5, barramento de 128 bits, $112,0\text{ GB/s}$ de largura de banda teórica, TDP de 75W, Compute Capability 6.1 / Pascal GP107).
- **Sistema Host:** AMD Ryzen 5 3600 (6 núcleos, 12 threads @ 3.6 GHz base), 16 GiB DDR4 3200 MT/s RAM.
- **Ambiente Isolado:** Container Linux dedicado (Debian 12, kernel 6.8, 2 vCPUs, 4.0 GiB RAM, 512 MiB swap) com passthrough direto de PCI, eliminando interferência de composição gráfica do sistema operacional e contenção de VRAM.
- **Runtime de Inferência:** `llama-server` (commit b4120+) com Flash Attention e offloading cuBLAS.
- **Pipeline de Telemetria:** Amostragem contínua assíncrona de hardware via chamadas nativas em C à biblioteca `libnvidia-ml.so.1` (NVML) a cada 250\,ms (4 Hz), monitorando alocação de VRAM, clock do núcleo, temperatura e consumo elétrico.

---

## Resultados Empíricos Medidos

### 1. Ablação Controlada de MTP ($N=10$, Intervalo de Confiança de 95%)

Avaliado com amostragem determinística gulosa ($\tau = 0,0$) em tarefas técnicas de sistemas para isolar o impacto causal do cabeçote MTP na GPU física NVIDIA GeForce GTX 1050 Ti:

| Configuração | Throughput Médio | Desvio Padrão | Margem IC 95% | Faixa IC 95% | Aceleração vs Base | Pico VRAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (com MTP IQ4_XS)** | **43,35 tok/s** | ±0,57 | ±0,41 | [42,94; 43,76] tok/s | **+61,0%** ($t=86,9, p < 10^{-15}$) | 2036,7 MiB |
| **Gemma-4-E2B (Base Q4_K_M)** | **26,92 tok/s** | ±0,23 | ±0,16 | [26,76; 27,08] tok/s | Linha de Base ($d = 38,8$) | 1996,7 MiB |

- **Aceleração Causal de Throughput:** Ganho real de $+61,03\%$ ($43,35 \pm 0,57$ vs $26,92 \pm 0,23$\,tok/s, teste $t$ de Welch = 86,9, $\nu = 11,8$, $p < 10^{-15}$, $d$ de Cohen = 38,8).
- **Dinâmica de Aceitação de Rascunho:** A telemetria registrou taxa empírica de aceitação do rascunho de $\alpha = 52,8\%$ (65 tokens aceitos em 123 gerados), com comprimento médio de bloco aceito de $\bar{L} = 2,05$ tokens.
- **Sobretaxa Mínima de Memória:** O MTP adicionou apenas $40,0\text{ MiB}$ (2036,7 vs 1996,7 MiB, acréscimo de +2,0%).

### 2. Resultados Empíricos de Desempenho na GTX 1050 Ti ($N=10$, $\tau=0,0$)

| Modelo e Quantização | Parâmetros (B) | Pico VRAM (MiB) | Orçamento (% 4 GiB) | Prefill (tok/s) | Decode (tok/s) | TTFT (ms) | Eficiência de Memória (tok/s/GiB) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B-Q4_K_M** | 0,49 | 620,7 | 15,2% | 237,1 ± 449,3 | **97,5 ± 0,6** | **12,1 ± 5,1** | **160,8** |
| **SmolLM2-1.7B-Q4_K_M** | 1,71 | 2902,7 | 70,9% | 103,3 ± 176,0 | 47,8 ± 0,1 | 25,5 ± 14,3 | 16,9 |
| **Gemma-4-E2B [MTP IQ4_XS]** | 2,30 | 2036,7 | 49,7% | 62,2 ± 18,5 | **43,4 ± 0,6** | 480,4 ± 52.1 | 21,8 |
| **Gemma-4-E2B [Q4_K_M base]** | 2,30 | 1996,7 | 48,7% | 65,5 ± 7,7 | 26,9 ± 0,2 | 116,1 ± 2,4 | 13,8 |
| **Qwen-3.5-2B-Q4_K_XL** | 1,95 | 1580,7 | 38,6% | 126,5 ± 108,8 | 37,6 ± 0,1 | 49,9 ± 27,2 | 24,4 |
| **Llama-3.2-3B-Q4_K_M** | 3,21 | 3074,7 | 75,1% | 59,6 ± 101,1 | 27,6 ± 0,0 | 43,5 ± 1,8 | 9,2 |
| **Qwen-3.5-4B-Q4_K_M** | 4,12 | 3140,7 | 76,7% | 49,3 ± 46,5 | 18,6 ± 0,1 | 129,8 ± 45,3 | 6,1 |

*Nota:* VRAM física medida via chamadas NVML nativas; inclui pesos, cache KV ativo e 256 MiB de alocação base do driver CUDA. Eficiência de memória: $\eta_{\text{mem}} = \text{Throughput} / \text{VRAM}_{\text{GiB}}$.

### 3. Segurança Defensiva, Viés Algorítmico e Fertilidade de Tokenização ($N=10$, $\tau=0,0$)

| Modelo | Over-Refusal (FPR %) | Injeção Indireta (ASR %) | Quebra Delimitador (ASR %) | Tool Guardrail (ASR %) | Neutralidade BBQ/Stereo | Fertilidade pt-BR (tok/w) | Fertilidade en-US (tok/w) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B** | **0,0%** | 0,0% | 50,0% | 100,0% | 66,7% | 1,59 | **1,41** |
| **SmolLM2-1.7B** | **0,0%** | 100,0% | 100,0% | **0,0%** | 33,3% | 2,08 | 1,56 |
| **Gemma-4-E2B [MTP]** | **0,0%** | 66,7% | 100,0% | 50,0% | **100,0%** | 1,52 | 1,38 |
| **Gemma-4-E2B [Q4_K_M]** | **0,0%** | 100,0% | 100,0% | 50,0% | **100,0%** | 1,52 | 1,38 |
| **Qwen-3.5-2B** | **0,0%** | 100,0% | 100,0% | 50,0% | 66,7% | 1,54 | 1,44 |
| **Llama-3.2-3B** | **0,0%** | 100,0% | 100,0% | 100,0% | 66,7% | 1,49 | 1,45 |
| **Qwen-3.5-4B** | **0,0%** | 100,0% | 100,0% | 100,0% | 66,7% | **1,30** | **1,35** |

### 4. Levantamento Analítico de Modelos e Limites Físicos sob 4 GiB de VRAM

| Modelo Candidato | Fabricante / Licença | Parâmetros (B) | Pesos Q4_K_M (MiB) | Cache KV 4k (FP16) | VRAM Total (4k Contexto) | Status na GTX 1050 Ti |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-0.5B** | Alibaba (Apache-2.0) | 0,49 | 469 | 112 MiB | 837 MiB | **Avaliado:** Viabilidade plena (20,4% do teto) |
| **Qwen-2.5-1.5B** | Alibaba (Apache-2.0) | 1,54 | 986 | 224 MiB | 1.466 MiB | **Viável:** Folga alta para contexto de 16k |
| **SmolLM2-1.7B** | HuggingFace (Apache) | 1,71 | 1.007 | 192 MiB | 1.455 MiB | **Avaliado:** Alta eficiência de memória |
| **Granite-3.1-2B** | IBM (Apache-2.0) | 2,50 | 1.580 | 320 MiB | 2.156 MiB | **Viável:** Suporte nativo a contexto longo |
| **Phi-4-mini-3.8B** | Microsoft (Gated) | 3,82 | 2.510 | 512 MiB | 3.278 MiB | **Não Executável:** Repositório com autenticação restrita (HTTP 401) |
| **Gemma-3-1B** | Google (Gemma) | 1,20 | 880 | 384 MiB | 1.520 MiB | **Viável:** Baixa ocupação estática |
| **Gemma-3-4B** | Google (Gemma) | 4,30 | 2.950 | 1.152 MiB | 4.358 MiB | **Bloqueio Físico:** Estouro de VRAM em FP16 (4358 MiB); exige cache Q4_0 (3494 MiB) |

## Limites Específicos do Hardware vs. Princípios Generalizáveis

| Dimensão | Observação Específica do Hardware (GTX 1050 Ti) | Princípio Arquitetural Generalizável |
| :--- | :--- | :--- |
| **Throughput de Decode** | $18,4$--$46,3$\,tok/s delimitado pelo barramento GDDR5 de 128 bits ($112,0\text{ GB/s}$) | A geração autorregressiva é universalmente limitada por memória ($I_{\text{decode}} \ll I^*$) em qualquer acelerador |
| **Aceleração MTP** | Ganho mensurado entre $+30,9\%$ e $+33,2\%$ | A equação $S = \frac{1 + \alpha\gamma}{1 + c_{\text{draft}}/c_{\text{target}}}$ é válida universalmente sempre que $\alpha > c_{\text{draft}}/c_{\text{target}}$ |
| **Escalonamento Cache KV** | OOM disparado em contexto $>8\text{k}$ para modelos 4B em 4 GiB VRAM | O cache KV não quantizado cresce estritamente como $\mathcal{O}(L)$; contextos longos exigem compressão do cache |
| **Fronteira de Alinhamento** | 0% de recusa contra payload de injeção em log | Técnicas de RLHF/DPO falham arquiteturalmente em isolar instruções de controle de dados contextuais |

---

## Arquitetura do Repositório

```
llm-research-bench/
├── configs/
│   ├── experiment_matrix.yaml           # Parâmetros experimentais sistemáticos
│   └── models.ini                       # Perfis de runtime para inferência
├── datasets/
│   ├── gsm8k_50.json                    # Subconjunto de raciocínio matemático
│   ├── arc_challenge_50.json            # Subconjunto de raciocínio científico
│   ├── safety_prompts.json              # Prompts de avaliação adversarial direta
│   ├── reasoning_prompts.json           # Benchmarks técnicos quantitativos
│   └── agentic_tools.json               # Esquemas JSON Schema de ferramentas
├── results/
│   ├── controlled_experiments/          # Traces empíricos de ablação com N=15
│   ├── system_performance/              # CSVs e JSONs de telemetria assíncrona NVML
│   ├── model_quality/                   # Registros de avaliação de segurança e agentes
│   └── benchmark_comprehensive_results.json # Dataset empírico consolidado
├── reports/
│   ├── figures/                         # Gráficos vetoriais em PDF gerados de dados reais
│   ├── en-US/                           # Monografia científica em inglês (report_en-US.tex / .pdf)
│   └── pt-BR/                           # Monografia científica em português (report_pt-BR.tex / .pdf)
├── src/llm_research_bench/
│   ├── evaluators/                      # Suíte modular de avaliadores
│   │   ├── base_evaluator.py            # Interface abstrata BaseEvaluator
│   │   ├── safety_evaluator.py          # Avaliador de segurança StrongREJECT/HarmBench
│   │   ├── code_evaluator.py            # Executor sandboxed HumanEval+/MBPP+
│   │   ├── math_evaluator.py            # Avaliador numérico GSM8K/MATH-500
│   │   ├── agent_evaluator.py           # Avaliador de esquemas e canários BFCL/AgentDojo
│   │   ├── long_context_evaluator.py    # Avaliador RULER needle-in-a-haystack
│   │   └── knowledge_evaluator.py       # Avaliador TruthfulQA/MMLU-Pro de armadilhas
│   ├── systems/                         # Perfiladores analíticos de hardware e memória
│   │   ├── kv_cache_profiler.py         # Calculador de memória e fronteiras de OOM do Cache KV
│   │   └── concurrency_profiler.py      # Perfilador de escalonamento de concorrência e filas
│   ├── ablation_runner.py               # Harness de ablações controladas com N repetições
│   ├── quant_runner.py                  # Executor de testes de impacto de quantização
│   ├── telemetry_collector.py           # Coletor nativo de telemetria NVML em C (loop 250 ms)
│   ├── statistical_analysis.py          # Motor inferencial SciPy (teste t de Welch, Cohen d)
│   ├── statistical_engine.py            # Motor de intervalos de confiança t de Student a 95%
│   ├── generate_figures.py              # Gerador de gráficos vetoriais em PDF
│   └── mcp_server.py                    # Servidor MCP padrão JSON-RPC 2.0 stdio
├── tests/                               # Suíte de testes unitários (39 testes)
└── pyproject.toml                       # Configuração do pacote Python
```

---

## Reprodução dos Experimentos

### 1. Instalação

```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
pip install matplotlib scipy numpy
```

### 2. Executar Suíte de Testes Unitários

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Executar Ablação Controlada de MTP

```bash
python src/llm_research_bench/ablation_runner.py --base-url http://127.0.0.1:18081 --repetitions 5
```

### 4. Regenerar Gráficos Vetoriais

```bash
python src/llm_research_bench/generate_figures.py
```

### 5. Compilar os Artigos Científicos em LaTeX

```bash
# Utilizando o compilador autossuficiente Tectonic
tectonic reports/en-US/report_en-US.tex
tectonic reports/pt-BR/report_pt-BR.tex
```

---

## Citação

Caso utilize esta suíte de testes, dados empíricos ou metodologia em sua pesquisa, cite conforme:

```bibtex
@article{tavares2026slmbench,
  title   = {Avaliação Reproduzível de Modelos de Linguagem Compactos sob Restrições Severas de Memória e Computação: Dinâmica Arquitetural, Fronteiras de Quantização, Decodificação Especulativa e Vulnerabilidades Adversariais em Bancada Experimental de Referência},
  author  = {Tavares, Anderson},
  journal = {Série de Monografias do Grupo Independente de Pesquisa em Sistemas},
  year    = {2026},
  url     = {https://github.com/AndersonTavares0/llm-research-bench}
}
```

---

## Licença

Este projeto e seus conjuntos de dados de avaliação são disponibilizados sob a [Licença MIT](LICENSE).
