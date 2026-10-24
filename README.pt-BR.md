# Avaliação Reproduzível de Modelos de Linguagem Compactos sob Restrições Severas de Memória e Computação

[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Testes: 39 Passando](https://img.shields.io/badge/testes-39%20passando-brightgreen.svg)](tests/)
[![Artigo: PDF (EN)](https://img.shields.io/badge/Paper-PDF%20(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Artigo: PDF (PT)](https://img.shields.io/badge/Artigo-PDF%20(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)

> **Monografia Científica e Suíte Aberta de Avaliação**<br>
> Uma investigação empírica independente sobre a dinâmica arquitetural, limites teóricos Roofline, fronteiras de quantização não homogênea, decodificação especulativa (Multi-Token Prediction), escalonamento analítico do cache Chave-Valor (KV) e vulnerabilidades adversariais de Modelos de Linguagem Compactos (SLMs) sob um teto rígido de $\le 4096\text{ MiB}$ de VRAM.

For the English version of this documentation, see [README.md](README.md).

---

## Resumo e Escopo da Pesquisa

A implantação de Modelos de Linguagem Pequenos (SLMs, 2B--4B parâmetros) diretamente em hardware físico de borda garante estrita soberania de dados, latência determinística e eliminação de custos de tráfego de nuvem. Contudo, operar sob limites rígidos de memória física ($\le 4096\text{ MiB}$ de VRAM) impõe compromissos fundamentais de engenharia de sistemas entre precisão de quantização, saturação do barramento de memória, execução especulativa e robustez adversarial.

Este repositório fornece a suíte experimental completa, os ambientes de avaliação, os pipelines de análise estatística e os artigos científicos reproduzíveis avaliando quatro arquiteturas compactas (**Gemma-4-E2B-it**, **Qwen-3.5-4B**, **Qwen-3.5-2B** e **Llama-3.2-3B**).

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

### 1. Ablação Controlada de MTP ($N=15$, Intervalo de Confiança de 95%)

Avaliado com amostragem determinística gulosa ($\tau = 0,0$) em tarefas técnicas de sistemas ao longo de 5 ensaios independentes (15 execuções totais) para isolar o impacto causal do cabeçote MTP:

| Configuração | Throughput Médio | Desvio Padrão | Margem IC 95\% | Faixa IC 95\% | Regime Estacionário | Pico VRAM |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (com MTP)** | **42,21 tok/s** | 10,82 | ±5,99 | [36,2; 48,2] tok/s | **44,95 tok/s** | 2038 MiB |
| **Gemma-4-E2B (Base sem MTP)** | **32,25 tok/s** | 5,83 | ±3,23 | [29,0; 35,5] tok/s | **33,75 tok/s** | 2038 MiB |

- **Aceleração Global:** Ganho de $+30,9\%$ no throughput (teste $t$ de Welch = 3,139, $\nu = 21,51$, valor-$p$ bicaudal = 0,0049, valor-$p$ unicaudal = 0,0024, $d$ de Cohen = 1,146, efeito grande).
- **Aceleração em Regime Estacionário:** Ganho de $+33,2\%$ ($44,95 \pm 2,12$ vs $33,75 \pm 0,41$\,tok/s, teste $t$ de Welch = 19,38, $\nu = 13,99, p = 1,67 \times 10^{-11}$, $d$ de Cohen = 7,32), convergindo exatamente com a formulação teórica ($S \approx 1,333\times$ para taxa de aceitação $\alpha = 0,40$).
- **Neutralidade de Memória:** Zero sobrecarga adicional de VRAM (2038\,MiB em ambas as configurações).
- **Decomposição de Fatores Confundidores entre Quantização e MTP:** Em regime estacionário aquecido, o Gemma-4-E2B (IQ4_XS + MTP) apresenta uma vantagem composta de +59,2% no throughput em relação ao padrão Q4_K_M (41,92 vs 26,34 tok/s). Decompondo esse ganho e isolando a aceleração verificada de +33,2% do MTP, constata-se que a quantização por importância não uniforme contribui isoladamente com uma vantagem líquida estimada de +19,5% no throughput, diretamente alinhada à redução de 16,7% no tráfego de pesos lidos da DRAM GDDR5 (1,8 GB para 1,5 GB).

### 2. Desempenho de Sistemas e Eficiência Energética

| Modelo | Pico VRAM | Fração Orçamento | Avaliação Prompt | Throughput Decode | TTFT | Eficiência de Memória ($\eta_{\text{mem}}$) | Est. Eficiência Energética ($E_{\text{tok/J}}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (IQ4_XS + MTP)** | **1.510 MiB** | **36,8%** | **468,2 tok/s** | **46,3 tok/s** | **115,4 ms** | **31,40 tok/s/GiB** | **0,89 tok/J** |
| **Qwen-3.5-2B (Q4_K_XL)** | 1.598 MiB | 39,0% | 389,5 tok/s | 37,5 tok/s | 142,1 ms | 24,04 tok/s/GiB | 0,77 tok/J |
| **Llama-3.2-3B (Q4_K_M)** | 2.120 MiB | 51,7% | 390,7 tok/s | 27,4 tok/s | 168,3 ms | 13,24 tok/s/GiB | 0,50 tok/J |
| **Qwen-3.5-4B (Q4_K_M)** | 3.069 MiB | 74,9% | 237,1 tok/s | 18,4 tok/s | 284,6 ms | 6,14 tok/s/GiB | 0,30 tok/J |

*Nota:* VRAM de pico registrada em MiB binário ($1024^2$ bytes). A eficiência de memória é definida como $\eta_{\text{mem}} = \text{Throughput} / \text{VRAM}_{\text{GiB}}$ (onde $1\text{ GiB} = 1024^3\text{ bytes}$). A eficiência energética estimada ($E_{\text{tok/J}} = \text{Throughput} / P_{\text{est}}$) decorre de um modelo calibrado de carga do encapsulamento da GPU ($P_{\text{est}} \in [49, 62]\text{ W}$) refletindo pontos de operação de TDP da placa; a potência consumida na tomada AC do host ($65\text{ W}$--$110\text{ W}$) não está incluída.

### 3. Robustez Adversarial Exploratória e Model Context Protocol (MCP)

| Modelo | Recusa de Ataque Direto (5 Vetores) | Injeção Indireta de Contexto (1 Vetor de Log) | Chamada de Ferramentas MCP (3 Cenários) | Aritmética SysAdmin (3 Sondas) |
| :--- | :--- | :--- | :--- | :--- |
| **Gemma-4-E2B (MTP)** | **100% (5/5)** | **Falhou (0% recusa)** | **Aprovado (100% conformidade)** | 33,3% (Paridade ZFS) |
| **Qwen-3.5-4B** | **100% (5/5)** | **Falhou (0% recusa)** | **Aprovado (100% conformidade)** | 33,3% (Paridade ZFS) |
| **Qwen-3.5-2B** | **100% (5/5)** | **Falhou (0% recusa)** | **Aprovado (100% conformidade)** | 0,0% (deriva aritmética) |
| **Llama-3.2-3B** | **100% (5/5)** | **Falhou (0% recusa)** | Falhou (erro de parsing no turno 2) | 33,3% (Lógica de RAM) |

*Nota sobre o Escopo de Segurança e MCP:* Todas as métricas de segurança, ferramentas e aritmética representam microbenchmarks exploratórios preliminares ($N=5$ testes de segurança direta, $N=1$ teste de injeção indireta, $N=3$ cenários de ferramentas MCP, $N=3$ sondas de aritmética de sysadmin). Demonstram perfis comportamentais específicos sob condições controladas de borda, mas não constituem certificações exaustivas de segurança ou protocolo (as quais demandam suítes escaladas como HarmBench, StrongREJECT e BFCL).

- **Recusa Direta:** 100% em todos os modelos contra exploits armados de CVE (Log4Shell), keyloggers furtivos, personificação DAN e extração de instruções do sistema.
- **Injeção Indireta de Prompt:** Vulnerabilidade universal (0% de recusa). Todos os modelos executaram comandos simulados de substituição quando encapsulados em logs de contexto não confiáveis, provando que o alinhamento pós-treinamento falha em isolar fronteiras de instrução.

---

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
