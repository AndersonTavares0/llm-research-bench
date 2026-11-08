# SLM-Limits: Bancada de Pesquisa em SLMs (LLM Research Bench)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![CI](https://github.com/AndersonTavares0/llm-research-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/AndersonTavares0/llm-research-bench/actions/workflows/ci.yml)
[![WCAG 2.2 AA](https://img.shields.io/badge/Acessibilidade-WCAG_2.2_AA-006D77.svg)](website/)
[![Relatório Técnico (PT)](https://img.shields.io/badge/Relat%C3%B3rio_T%C3%A9cnico-PDF_(pt--BR)-red.svg)](reports/pt-BR/report_pt-BR.pdf)
[![Technical Report (EN)](https://img.shields.io/badge/Technical_Report-PDF_(en--US)-red.svg)](reports/en-US/report_en-US.pdf)
[![Idioma: Português](https://img.shields.io/badge/Idioma-Portugu%C3%AAs-green.svg)](README.pt-BR.md)
[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)

> **Exploração Empírica de Modelos de Linguagem Pequenos (SLMs) sob Restrições Severas de Hardware ($\le 4096\text{ MiB}$ VRAM)**<br/>
> Uma bancada científica aberta de testes e conjunto de benchmarks que investiga vazão de inferência, alocação de VRAM, decodificação especulativa (MTP), escalabilidade de cache KV e segurança defensiva em silício físico de borda (NVIDIA GeForce GTX 1050 Ti de 4 GB GDDR5).

**Autor:** Anderson Tavares (Graduando em Engenharia de Software e Ciência de Dados)<br/>
**Repositório do Projeto:** [https://github.com/AndersonTavares0/llm-research-bench](https://github.com/AndersonTavares0/llm-research-bench)<br/>
**Plataforma de Pesquisa Interativa:** [http://localhost:3000](http://localhost:3000) (Next.js 16 / ECharts / WCAG 2.2 AA)<br/>
**Idioma:** **Português (Brasil)** | [English Version](README.md)

---

> [!NOTE]
> **Integridade Científica e Aviso Legal**<br/>
> Este repositório é um projeto de pesquisa independente focado em engenharia de sistemas empírica e reproduzível. Embora todos os experimentos sigam rigorosa temporização monotônica, isolamento de hardware, proveniência criptográfica e validação estatística *fail-closed*, **este trabalho não é uma publicação acadêmica com revisão por pares**. Os resultados refletem o comportamento físico observado em uma bancada dedicada com GPU Pascal. Observações históricas, limites analíticos e medições verificadas são rotulados separadamente de acordo com a hierarquia de evidências do projeto. Consulte [Integridade Científica e Hierarquia de Evidências](#5-metodologia-limitações-e-evolução) e o [Research Charter](docs/research/research-charter.md).

---

## Sumário

- [1. Visão Geral e Escopo de Pesquisa](#1-visão-geral-e-escopo-de-pesquisa)
- [2. Arquitetura do Sistema e Fluxo](#2-arquitetura-do-sistema-e-fluxo)
- [3. Resultados Empíricos e Fronteiras de Pesquisa](#3-resultados-empíricos-e-fronteiras-de-pesquisa)
- [4. Como Começar, CLI e Plataforma Web](#4-como-começar-cli-e-plataforma-web)
- [5. Metodologia, Limitações e Evolução](#5-metodologia-limitações-e-evolução)

---

## 1. Visão Geral e Escopo de Pesquisa

### O Que É o SLM-Limits?

O **SLM-Limits** é uma bancada de experimentação empírica projetada para avaliar **Modelos de Linguagem Pequenos (SLMs, com 0,5B a 4B de parâmetros)** executando em aceleradores de consumo legados sob restrições severas de memória ($\le 4096\text{ MiB}$ VRAM). Em vez de depender de APIs em nuvem ou GPUs corporativas de data center (A100/H100), este projeto investiga os limites físicos operacionais ao executar modelos locais diretamente no hardware de borda.

### Por Que Avaliar em uma GTX 1050 Ti de 4 GB?

A **NVIDIA GeForce GTX 1050 Ti (Pascal GP107, 4096 MiB GDDR5, barramento de 128 bits, banda de 112 GB/s, 75W TDP)** serve como uma fronteira física rigorosa e inflexível:

1. **Limite Rígido de VRAM (4096 MiB):** Os pesos estáticos dos modelos consomem sozinhos de 15% a 77% da memória física total. O espaço livre para o cache Key-Value (KV) é estrito, provocando rapidamente falhas de Out-of-Memory (OOM) ou queda para a RAM do sistema sem quantização agressiva.
2. **Zero Tensor Cores:** A microarquitetura GP107 não possui aceleradores matriciais dedicados (Tensor Cores). O processamento em FP16 opera a uma taxa penalizada de 1:64. Consequentemente, a decodificação autorregressiva com batch unitário é estritamente limitada pela largura de banda da memória ($112\text{ GB/s}$).
3. **Hardware Real de Borda:** Bilhões de dispositivos industriais, equipamentos médicos e estações de trabalho de consumo operam em GPUs das eras Pascal/Turing sem conectividade contínua a provedores de nuvem.

### Perguntas Centrais de Pesquisa (RQs)

O programa de pesquisa investiga quatro dimensões interdependentes:

- **Dinâmica de Quantização:** Como quantizações não uniformes com matriz de importância (`IQ4_XS`) se comparam a quantizações em bloco convencionais (`Q4_K_M`) em velocidade de geração e pegada de VRAM?
- **Aceleração Especulativa:** A predição de múltiplos tokens (MTP) confere ganhos práticos de vazão em GPUs limitadas por largura de banda sem a necessidade de modelos auxiliares dedicados?
- **Física do Cache KV e Limites de Contexto:** Em qual extensão de contexto o cache KV desencadeia colapso de memória sob FP16 vs quantização `q8_0`?
- **Robustez Defensiva e Segurança:** Modelos compactos conseguem estruturar saídas com precisão gramatical, respeitar envelopes autorizados de ferramentas e resistir a injeções de contexto?

---

## 2. Arquitetura do Sistema e Fluxo

A arquitetura do SLM-Limits é estruturada em quatro camadas desacopladas, garantindo isolamento estrito de hardware, execução determinística e rastreabilidade integral da telemetria de silício até a disseminação dos resultados.

```mermaid
flowchart TD
    subgraph L1["Camada 1: Hardware Físico e Substrato de Isolamento"]
        GPU["NVIDIA GeForce GTX 1050 Ti<br/>4096 MiB GDDR5 · 112 GB/s · 75W TDP"]
        PVE["Container Proxmox VE CT 108<br/>Debian 12 Minimal · Headless · PCI Passthrough Direto"]
        NVML["Monitor de Telemetria de Hardware<br/>Sonda NVML ctypes · Amostragem a 250 ms (VRAM, Temp, Drift)"]
        GPU --- PVE
        PVE --- NVML
    end

    subgraph L2["Camada 2: Motores de Inferência e Serviço"]
        LLAMA["Runtime llama.cpp (Versão Fixada b12024)<br/>Offload cuBLAS · llama-server e llama-bench"]
        QUANTS["Fronteiras de Quantização<br/>Q4_K_M · IQ4_XS · Cache KV em Q8_0"]
        SPEC["Motor de Decodificação Especulativa<br/>Cabeças de Predição de Múltiplos Tokens (MTP)"]
        LLAMA --- QUANTS
        LLAMA --- SPEC
    end

    subgraph L3["Camada 3: Trilhas de Avaliação e Arnês Científico"]
        TRACK_A["Trilha A: Sistemas e Telemetria<br/>Prefill / Decode tok/s · TTFT · Inclinação KV · Concorrência"]
        TRACK_B["Trilha B: Qualidade e Capacidade<br/>ARC-Challenge · HellaSwag · GSM8K · IFEval Strict"]
        TRACK_C["Trilha C: Dinâmica de Contexto e Saídas Estruturadas<br/>Gramática JSON Schema (30/30) · Ferramentas Nativas · Fertilidade"]
        TRACK_D["Trilha D: Cibersegurança Defensiva<br/>Triagem CWE-10 · Triagem CVE NVD 2.0 · Arnês de AppSec"]
    end

    subgraph L4["Camada 4: Proveniência de Dados, Artefatos e Disseminação"]
        PROV["Proveniência Criptográfica<br/>Hashes SHA-256 · Manifestos Declarativos"]
        TIER["Hierarquia Estrita de Evidências<br/>[MEASURED] · [PARTIAL] · [ANALYTICAL] · [READY]"]
        REPORTS["Monografias Técnicas em LaTeX<br/>20p EN / 30p PT compiladas via Tectonic"]
        WEB["Painel de Pesquisa Interativo<br/>Next.js 16 · Tailwind · ECharts · WCAG 2.2 AA"]
    end

    L1 -->|Traços de Telemetria Física| L2
    L2 -->|Geração Determinística (τ = 0.0)| L3
    L3 -->|Microdados Brutos de Avaliação| L4
```

### Detalhamento das Camadas

#### 1. Hardware Físico e Substrato de Isolamento
- **Ambiente de Execução Isolado:** Os testes são executados em um container Proxmox VE minimalista com Debian 12 (`CT 108`), com passthrough exclusivo de PCI. Sem servidor gráfico X11, compositor ou processos desktop concorrentes, eliminando contaminação na VRAM do host.
- **Sonda Assíncrona de Telemetria (`telemetry_collector.py`):** Consulta a NVML nativa via C-types a cada 250 ms, registrando alocação de pico de VRAM, desvio de memória, temperatura da matriz e eventos de estrangulamento térmico via GPU Boost 3.0 ($1695 \to 1607\text{ MHz}$).

#### 2. Motores de Inferência e Serviço
- **Runtime Pinned:** Avaliado na versão fixada `b12024` do `llama.cpp` com aceleração nativa via cuBLAS.
- **Dois Caminhos de Inferência:**
  - *Pipeline Oficial de Campanhas (`campaign.py`):* Execução declarativa em YAML orquestrando `llama-bench` e `lm-evaluation-harness` com geração automática de manifestos.
  - *Módulos de Telemetria e Microbenchmarks (`src/llm_research_bench/`):* Microperfilamento de TTFT, percentis de latência por token, inclinação de consumo de cache KV e alocação de slots concorrentes.

#### 3. Trilhas de Avaliação
- **Trilha A (Telemetria de Sistemas):** Escalabilidade de vazão, modelagem de demanda do barramento de memória e degradação com 1 a 4 slots concorrentes.
- **Trilha B (Capacidade Zero-Shot):** Tarefas padronizadas de qualidade (ARC-Challenge, HellaSwag, GSM8K Flex, IFEval estrito).
- **Trilha C (Dinâmica de Contexto e Ferramentas):** Aderência gramatical a JSON Schema ($30/30$ vs $18/30$ sem gramática), envelopes nativos de ferramentas compatíveis com OpenAI e fertilidade de tokenização multilíngue.
- **Trilha D (Cibersegurança Defensiva):** Triagem estática de vulnerabilidades CWE, classificação de alertas CVE verificada contra a NVD 2.0 e guardrails de segurança em nível de aplicação (`defensive_harness.py`).

#### 4. Proveniência de Dados e Disseminação
- **Verificação SHA-256:** Cada modelo GGUF e registro de dataset tem seu hash criptográfico validado contra `datasets/model_provenance.json`.
- **Publicação e Visualização:** Os dados compilam em monografias técnicas completas em LaTeX (`reports/`) e em uma plataforma interativa acessível construída em Next.js (`website/`).

---

## 3. Resultados Empíricos e Fronteiras de Pesquisa

### Tabela Mestra Comparativa (Bancada GTX 1050 Ti)

Todas as configurações avaliadas sob amostragem gulosa em host único ($\tau = 0.0$, $\text{seed} = 42$) na NVIDIA GeForce GTX 1050 Ti de referência (4096 MiB GDDR5, 112 GB/s):

| Modelo | Arquitetura | Quantização | Pico VRAM | % de 4GB | Vazão Decode | TTFT Estável | Índice Qualidade | Eficiência Memória |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Qwen2.5:0.5B** | Qwen2.5 (0.49B) | `Q4_K_M` | **620.7 MiB** | 15.2% | **97.5 tok/s** | **12.1 ms** | 30.5% | **160.8 tok/s/GiB** |
| **SmolLM2:1.7B** | LLaMA (1.71B) | `Q4_K_M` | 1184.2 MiB | 28.9% | 52.1 tok/s | 78.4 ms | 39.8% | 45.0 tok/s/GiB |
| **Gemma-4:E2B** | Gemma 2 (2.00B) | `IQ4_XS` + **MTP** | 1510.0 MiB | 36.8% | 46.3 tok/s | 115.4 ms | 52.0% | 31.4 tok/s/GiB |
| **Qwen3.5:2B** | Qwen (1.95B) | `Q4_K_XL` | 1598.0 MiB | 39.0% | 37.5 tok/s | 142.1 ms | 45.3% | 24.0 tok/s/GiB |
| **Llama-3.2:3B** | Llama 3.2 (3.21B) | `Q4_K_M` | 2120.0 MiB | 51.7% | 27.4 tok/s | 168.3 ms | 49.0% | 13.2 tok/s/GiB |
| **Qwen3.5:4B** | Qwen (4.02B) | `Q4_K_M` | 3069.0 MiB | 74.9% | 18.4 tok/s | 284.6 ms | **54.0%** | 6.1 tok/s/GiB |

> [!NOTE]
> O *Índice de Qualidade* representa a média aritmética das pontuações zero-shot em ARC-Challenge, HellaSwag, GSM8K (Flex) e IFEval (Prompt-Strict). A *Eficiência de Memória* mede a vazão de geração por GiB alocado de VRAM ($\text{tok/s} / \text{GiB}$).

### Ablações Arquiteturais Controladas (Gemma-4-E2B)

Observações controladas sequenciais em uma arquitetura fixa de 2B mediram os efeitos isolados da quantização não uniforme e da Predição de Múltiplos Tokens (MTP):

```
Vazão de Geração (tok/s):
  Linha de Base Q4_K_M:    [==========================]  26.92 tok/s
  Quantização IQ4_XS:      [==================================]  34.51 tok/s (+28.2%)
  Quant + MTP Especulativo:[============================================]  43.35 tok/s (+61.0%)

Pegada de VRAM (MiB):
  Linha de Base Q4_K_M:    [========================================] 1996.7 MiB
  Quantização IQ4_XS:      [====================================]     1800.7 MiB (-196.0 MiB)
  Quant + MTP Especulativo:[=========================================] 2036.7 MiB (+40.0 MiB líq.)
```

- **Efeito da Quantização:** A matriz de importância `IQ4_XS` reduziu a pegada de pesos estáticos em **196.0 MiB**, aumentando a vazão de decodificação em **+28.2%** graças à redução de tráfego no barramento de memória.
- **Efeito do MTP Especulativo:** A ativação de cabeças MTP conferiu **+25.6% de vazão** ($34.51 \to 43.35\text{ tok/s}$) com um custo operacional de buffer de **+236.0 MiB**.
- **Sinergia Líquida:** A economia de memória do `IQ4_XS` absorveu **83%** da sobretaxa do MTP, gerando um ganho combinado de **+61.0% de velocidade** por apenas **+40.0 MiB** adicionais de VRAM.

### Física do Cache KV e Limites de Contexto (Campanha H1)

- **Taxa de Expansão de Memória:** O consumo do cache KV cresce a **$113.0\text{ KiB/token}$** em FP16 contra **$60.3\text{ KiB/token}$** sob quantização `q8_0`.
- **Horizonte Seguro de 3.8k Tokens:** Para modelos de 3B em `Q4_K_M` (pesos estáticos: ~2.5 GiB), o cache KV em FP16 esgota toda a margem restante de VRAM em ~3.800 tokens, precipitando CUDA OOM. O uso de cache KV em `q8_0` reduz a pegada de pico de VRAM em **19.6%**, mantendo precisão perfeita de recuperação de fatos em agulhas de contexto ($30/30$).

### Saídas Estruturadas e Confiabilidade de Chamada de Ferramentas

- **Decodificação Guiada por Gramática:** A decodificação com restrição gramatical via JSON Schema atingiu **$30/30$** ($100\%$) de conformidade contra **$18/30$** ($60\%$) no modo genérico `json_object` ($12/0$ pares discordantes, teste exato de McNemar $p = 0.000488$).
- **Chamada de Ferramentas Nativa vs Mediada:** O envelope nativo de ferramentas compatível com OpenAI alcançou **$18/18$** invocações válidas, enquanto a extração mediada por prompt textual degradou para $2\text{--}8/18$.

### Sobretaxa Multilíngue de Tokenização

A avaliação de 12 textos paralelos em português, mandarim e inglês expôs grandes assimetrias em vocabulários compactos:
- **SmolLM2 (49k tokens):** Razão de fertilidade de **$2.40\times$** para o português e **$4.59\times$** para o mandarim em relação ao inglês, reduzindo a capacidade útil de contexto em idiomas não ingleses para menos de $22\%$.
- **Qwen2.5 (151k tokens):** Manteve fertilidade equilibrada ($1.15\times$ em português, $1.42\times$ em mandarim), preservando a capacidade de contexto.

### Trilha de Pesquisa em Cibersegurança Defensiva

Uma trilha defensiva dedicada implementa testes determinísticos offline sem executar código gerado fora de sandbox:
- **Triagem Estática de CWE (v2):** 10 casos balanceados cobrindo injeção de comando (CWE-78), SQLi (CWE-89), XSS (CWE-79), vazamento de credenciais (CWE-798) e controles negativos.
- **Triagem de Alertas CVE (v1):** 6 alertas de segurança avaliados contra inventários simulados de software, verificados com a NVD 2.0 e MITRE.
- **Arnês de Segurança em Aplicação (`defensive_harness.py`):** Ambiente simulado multi-inquilino que avalia barreiras de autorização baseadas em papéis para bloquear injeções indiretas de prompt e exfiltração de dados.

---

## 4. Como Começar, CLI e Plataforma Web

### Pré-requisitos

- **Sistema Operacional:** Linux (Debian 12 / Ubuntu 22.04 LTS recomendado)
- **Python:** 3.10+
- **Node.js:** v18+ e gerenciador `pnpm` (para a plataforma web interativa)
- **Hardware Opcional:** GPU NVIDIA com driver proprietário (para telemetria NVML em tempo real; modos mock disponíveis para testes offline)

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench

# Configurar ambiente virtual Python
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências em modo editável
pip install -e .
```

### Executar a Suíte de Testes

```bash
# Executa 270+ testes unitários, de integração e regressão estatística
python -m pytest tests/
```

### Executar a Plataforma Web Interativa

O projeto inclui um portal de pesquisa construído em Next.js 16 com exploração de fronteiras de Pareto, gráficos de telemetria e matrizes de comparação:

```bash
# Acessar a pasta do website
cd website

# Instalar dependências e iniciar o servidor
pnpm install
pnpm dev
# Ou compilar e rodar a versão de produção
pnpm build && pnpm start -p 3000
```
Abra [http://localhost:3000](http://localhost:3000) no seu navegador. Compatibilidade total com acessibilidade WCAG 2.2 AA nos temas claro e escuro.

### Compilação das Monografias em LaTeX

Ambas as monografias técnicas podem ser compiladas diretamente da fonte usando o [Tectonic](https://tectonic-typesetting.github.io/):

```bash
# Monografia em Inglês (reports/en-US/report_en-US.pdf)
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US

# Monografia em Português (reports/pt-BR/report_pt-BR.pdf)
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
```

---

## 5. Metodologia, Limitações e Evolução

### Hierarquia Científica de Evidências

Para evitar afirmações infladas, este repositório classifica rigorosamente todas as conclusões em cinco categorias:

- `[MEASURED]`: Microdados empíricos coletados diretamente no hardware físico com telemetria contínua via NVML e temporização monotônica.
- `[PARTIAL]`: Dados empíricos válidos obtidos sob protocolos-piloto ou suítes amostrais incompletas.
- `[ANALYTICAL]`: Derivações teóricas, limites do modelo Roofline ou fórmulas matemáticas de cache ($B_{\text{demand}} = S_{\text{weights}} \times \text{Throughput}$).
- `[READY]`: Suítes de testes, benchmarks e arneses defensivos implementados e testados deterministicamente, aguardando execução física em hardware.
- `[UNKNOWN]`: Hipóteses ou configurações ainda não estudadas nesta plataforma.

### Limites Metodológicos

- **Observações Descritivas em Host Único:** Todas as medições foram coletadas em uma única máquina com GTX 1050 Ti. Repetições de consultas no mesmo host representam consistência operacional, não réplicas de hardware estatisticamente independentes. Inferências estatísticas de hardware (como teste t de Welch) operam em modo *fail-closed* até que testes multissítio sejam conduzidos.
- **Deriva Térmica:** Testes prolongados elevam a temperatura da matriz de $44^\circ\text{C}$ para $74^\circ\text{C}$, ativando o escalonamento do NVIDIA GPU Boost 3.0 ($-5.2\%$). Períodos de resfriamento automatizados são impostos entre baterias de testes.
- **Sem Inferência para Hiperscalers:** Os resultados avaliam estritamente hardware de consumo; não devem ser generalizados para aceleradores corporativos de centros de dados equipados com memória HBM e Tensor Cores.

### Research Charter e Roteiro

O roteiro científico completo, contendo a matriz de 22 Questões de Pesquisa (RQs) e prioridades experimentais (P0–P3), está mantido em [`docs/research/research-charter.md`](docs/research/research-charter.md).

---

## Citação e Licença

Caso utilize esta metodologia de benchmark, dados empíricos ou traços de telemetria em sua pesquisa, cite:

```bibtex
@article{tavares2026slmlimits,
  title   = {SLM-Limits: Reproducible Evaluation of Small Language Models Under Severe Memory and Compute Constraints},
  author  = {Tavares, Anderson},
  journal = {Open Technical Report and Benchmark Monograph},
  year    = {2026},
  url     = {https://github.com/AndersonTavares0/llm-research-bench}
}
```

Este projeto é um software de código aberto licenciado sob a **[Licença MIT](LICENSE)**.

---
*Iniciativa de pesquisa independente conduzida por Anderson Tavares. Não filiada, patrocinada ou endossada por NVIDIA, Google, Meta ou Alibaba.*
