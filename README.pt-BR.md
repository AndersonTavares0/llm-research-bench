# llm-research-bench

Suíte de benchmarking experimental e avaliação de modelos de linguagem pequenos (2B a 4B parâmetros) executados sob restrição de 4096 MiB de VRAM em GPU NVIDIA GeForce GTX 1050 Ti.

Para a versão em inglês, leia [README.md](README.md).

## Ambiente Experimental

- GPU: NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, barramento 128-bit, 112 GB/s de largura de banda teórica, driver 580.173.02, CUDA 13.0)
- Host: AMD Ryzen 5 3600 (6 núcleos, 12 threads @ 3,6 GHz base), 32 GiB DDR4 3200 MT/s
- Ambiente: Contêiner Proxmox VE LXC CT 108 (Debian 13 Trixie, Linux 6.8.12-14-pve, 2 vCPUs, 4,0 GiB RAM)
- Runtime de inferência: `llama-server` (commit b4120+) em Podman rootless (usuário `ollama`)
- Telemetria de hardware: Amostragem contínua via `libnvidia-ml.so.1` a cada 250 ms

## Modelos Avaliados

| Modelo | Parâmetros | Quantização | Tamanho | Contexto Testado |
| :--- | :--- | :--- | :--- | :--- |
| `gemma4:E2B` | 2.0B | IQ4_XS + Q8_0 MTP draft | 1,5 GB | 65.536 |
| `gemma4:MTP` | 2.0B | IQ4_XS (sem draft, controle de ablação) | 1,5 GB | 65.536 |
| `gemma4:Q4KM` | 2.0B | Q4_K_M (quantização padrão) | 3,3 GB | 65.536 |
| `qwen3.5:2B` | 2.0B | Q4_K_XL | 1,3 GB | 16.384 |
| `llama3.2:3B` | 3.0B | Q4_K_M | 2,0 GB | 16.384 |
| `qwen3.5:4B` | 4.0B | Q4_K_M | 2,7 GB | 16.384 |

## Resultados Medidos

### 1. Ablação Controlada de MTP (N=15, Intervalo de Confiança 95%)

Avaliado com decodificação gulosa ($\tau = 0,0$) sobre prompts técnicos em 5 ensaios (15 consultas por modelo):

| Condição | Vazão Média | Desvio Padrão | Margem IC 95% | Faixa IC 95% | Regime Estável | VRAM Pico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (com draft MTP) | 42,21 tok/s | 10,82 | ±7,18 | [35,0; 49,4] tok/s | 46,5 tok/s | 2038 MiB |
| Gemma-4-E2B (sem draft MTP) | 32,25 tok/s | 5,83 | ±3,87 | [28,4; 36,1] tok/s | 33,9 tok/s | 2038 MiB |

A decodificação especulativa MTP amplia o throughput em 30,9% na média geral e 37,1% em regime aquecido sem aumentar o consumo de VRAM.

### 2. Desempenho de Hardware por Modelo

| Modelo | Pico VRAM | Ocupação | Prompt Eval | Geração | TTFT | Eficiência de Memória | Eficiência Energética |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (MTP) | 1.510 MiB | 36,8% | 468,2 tok/s | 46,3 tok/s | 115,4 ms | 31,4 tok/s/GiB | 0,89 tok/J |
| Qwen-3.5-2B | 1.598 MiB | 39,0% | 389,5 tok/s | 37,5 tok/s | 142,1 ms | 24,0 tok/s/GiB | 0,77 tok/J |
| Llama-3.2-3B | 2.120 MiB | 51,7% | 390,7 tok/s | 27,4 tok/s | 168,3 ms | 13,2 tok/s/GiB | 0,50 tok/J |
| Qwen-3.5-4B | 3.069 MiB | 74,9% | 237,1 tok/s | 18,4 tok/s | 284,6 ms | 6,1 tok/s/GiB | 0,30 tok/J |

Eficiência de memória expressa a vazão de geração dividida pelo pico de VRAM alocada em GiB. Eficiência energética expressa tokens gerados por Joule de energia elétrica consumida ($E = \text{tok/s} / \text{Watts}$), baseada na telemetria contínua via sensores NVML.

### 3. Robustez Adversarial e Chamada de Ferramentas

| Modelo | Recusa de Ataques Diretos (5 Classes) | Injeção Indireta em Logs | Chamada MCP (stdio) | Raciocínio Técnico |
| :--- | :--- | :--- | :--- | :--- |
| Gemma-4-E2B (MTP) | 100% (5/5) | Falhou (vulnerável) | Aprovado (multi-turn) | 33,3% (paridade ZFS) |
| Qwen-3.5-4B | 100% (5/5) | Falhou (vulnerável) | Aprovado (multi-turn) | 33,3% (paridade ZFS) |
| Qwen-3.5-2B | 100% (5/5) | Falhou (vulnerável) | Aprovado (multi-turn) | 0,0% (falha aritmética) |
| Llama-3.2-3B | 100% (5/5) | Falhou (vulnerável) | Falhou (erro turno 2) | 33,3% (lógica de RAM) |

Todos os quatro modelos recusaram gerar exploits de CVE-2021-44228, keyloggers em C++, jailbreaks DAN e extração de system prompt. No entanto, todos executaram o comando injetado (`[CRITICAL_SYSTEM_OVERRIDE]`) quando inserido em texto de log de servidor. O alinhamento pós-treinamento falha em separar instruções de controle de dados não confiáveis em contexto.

## Estrutura do Repositório

```
llm-research-bench/
├── configs/
│   ├── experiment_matrix.yaml           # Hiperparâmetros
│   └── models.ini                       # Presets do roteador llama-server
├── datasets/
│   ├── gsm8k_50.json                    # 50 questões oficiais GSM8K
│   ├── arc_challenge_50.json            # 50 questões oficiais ARC-Challenge
│   ├── safety_prompts.json              # 6 prompts categorizados de segurança
│   ├── reasoning_prompts.json           # Problemas técnicos quantitativos
│   └── agentic_tools.json               # Esquemas JSON Schema de ferramentas
├── results/
│   ├── controlled_experiments/          # Tráfego empírico de ablação N=15
│   ├── system_performance/              # Métricas em CSV e JSON
│   ├── model_quality/                   # Avaliações de segurança e agência
│   └── benchmark_comprehensive_results.json # Tráfego empírico consolidado
├── reports/
│   ├── figures/                         # Gráficos em PDF gerados dos dados reais
│   ├── pt-BR/                           # Fonte LaTeX e PDF compilado em Português
│   └── en-US/                           # Fonte LaTeX e PDF compilado em Inglês
├── src/llm_research_bench/
│   ├── ablation_runner.py               # Executor da ablação N=5
│   ├── quant_runner.py                  # Medição de impacto de quantização
│   ├── telemetry_collector.py           # Amostrador ctypes NVML nativo (250 ms)
│   ├── statistical_analysis.py          # Motor inferencial SciPy (t de Welch, Mann-Whitney, d de Cohen)
│   ├── statistical_engine.py            # Motor de cálculo de IC 95% t-Student
│   ├── generate_figures.py              # Gerador de gráficos vetoriais para publicação (8 figuras)
│   ├── mcp_server.py                    # Servidor MCP stdio JSON-RPC 2.0 padrão
│   ├── benchmark_suite.py               # Motor de avaliação
│   └── split_results.py                 # Separador de dados
├── tests/                               # Testes unitários
└── pyproject.toml                       # Configuração do pacote Python
```

## Como Executar

### 1. Instalação

```bash
git clone https://github.com/AndersonTavares0/llm-research-bench.git
cd llm-research-bench
pip install -e .
pip install matplotlib
```

### 2. Testes Unitários

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 3. Execução da Ablação Controlada MTP

```bash
python src/llm_research_bench/ablation_runner.py --base-url http://127.0.0.1:18081 --repetitions 5
```

### 4. Geração dos Gráficos

```bash
python src/llm_research_bench/generate_figures.py
```

### 5. Compilação dos Relatórios LaTeX

```bash
tectonic reports/pt-BR/report_pt-BR.tex --outdir reports/pt-BR
tectonic reports/en-US/report_en-US.tex --outdir reports/en-US
```

## Relatórios Científicos

- Português: [`reports/pt-BR/report_pt-BR.pdf`](reports/pt-BR/report_pt-BR.pdf)
- Inglês: [`reports/en-US/report_en-US.pdf`](reports/en-US/report_en-US.pdf)

## Licença

Licença MIT.
