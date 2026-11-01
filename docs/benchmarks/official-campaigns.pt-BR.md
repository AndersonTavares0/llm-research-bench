# Campanhas oficiais de benchmark

Esta página documenta a camada de orquestração sobre ferramentas mantidas pela comunidade. Ela **não substitui nem reclassifica** os resultados históricos do projeto, que foram produzidos pelos avaliadores e protocolos próprios descritos nos relatórios existentes.

## Campanha smoke: Qwen3-1.7B

Artefatos completos, incluindo saídas originais, amostras e manifestos:
[`results/campaigns/smoke-qwen3-1.7b-v1/`](../../results/campaigns/smoke-qwen3-1.7b-v1/).

| Dimensão | Resultado |
|---|---|
| Hardware | GTX 1050 Ti, 4 GiB; Ryzen 5 3600; campanha no GPU Lab/CT108 |
| Modelo | Qwen3-1.7B Q4_K_M, GGUF; Apache-2.0 |
| SHA-256 do GGUF | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Harness de qualidade | EleutherAI lm-evaluation-harness `0.4.14.dev0`, commit `d6de81643928d653435c431bae19945d41d32520` |
| Runtime | llama.cpp build 12024, commit `ddf48f85c` |
| Amostra | limite de 20 exemplos por tarefa; seed 42 |

### Qualidade

Resultados provenientes diretamente do JSON do harness; `acc_norm` é informado quando disponível.

| Tarefa | Métrica | Valor | n |
|---|---|---:|---:|
| ARC Challenge | acc / acc_norm | 0,350 / 0,400 | 20 |
| HellaSwag | acc / acc_norm | 0,400 / 0,400 | 20 |
| Belebele (português, `por_Latn`) | acc / acc_norm | 0,750 / 0,750 | 20 |
| GSM8K | exact match (strict / flexible) | 0,000 / 0,000 | 20 |
| IFEval | prompt strict / loose | 0,600 / 0,550 | 20 |
| IFEval | instance strict / loose | 0,667 / 0,633 | 20 |

As métricas e erros-padrão reportados pelo harness, as configurações, versões das tarefas, hashes e amostras estão nos arquivos `knowledge-mcq/results.json` e `generative-chat/results.json`, junto com seus `meta.json` e logs.

### Desempenho

Medição feita por `llama-bench`, CUDA, 99 camadas na GPU, KV cache F16, três repetições:

| Operação | Tamanho | Média | Desvio-padrão |
|---|---:|---:|---:|
| Prefill | 512 tokens | 850,305 tokens/s | 1,123 |
| Decode | 128 tokens | 48,155 tokens/s | 0,023 |

Os valores detalhados de cada repetição e a saída original estão em `llama-bench/results.json` e `llama-bench/run.log`.

## Protocolo e limites

- Esta é uma **campanha smoke**, não um benchmark comparativo: `limit=20` serve para testar integração e rastreabilidade. A amostra pequena não autoriza ranking nem conclusões generalizáveis.
- A campanha usou zero-shot (`num_fewshot=0`), inclusive em GSM8K, cuja configuração padrão do harness é 5-shot. Os números não são diretamente comparáveis a execuções com os defaults da tarefa.
- O harness avisou que não conseguiu inferir a sequência EOS de parada. A execução terminou, mas essa limitação pode afetar a fidelidade da geração e deve ser resolvida antes de uma avaliação comparativa.
- A inspeção dos samples GSM8K confirmou um problema de geração, não de extração: 38 das 40 respostas registradas (20 exemplos em dois filtros) estão vazias; as duas não vazias também não contêm a resposta final completa. O log do servidor mostra várias gerações chegando a 256 tokens, mas não permite atribuir o limite à configuração da tarefa, ao backend ou ao servidor. Assim, `[invalid]` é consequência da saída vazia/incompleta, e não evidência de falha do extrator. Os artefatos históricos e a pontuação zero foram preservados; não foi alterado limite nem stop token sem reprodução controlada.
- Correção da orquestração para execuções futuras: o comando de chat agora transmite `max_gen_toks` configurado (padrão 256) e aceita `eos_string` explícito. Isso não altera nem valida retroativamente a execução histórica; ainda é necessária reprodução isolada para confirmar a causa dos outputs vazios.
- O comando registrou `--apply_chat_template` e o servidor foi iniciado com `--jinja`; entretanto, o JSON do harness registra `chat_template` vazio/hash nulo. Portanto, a proveniência efetiva do template não está comprovada pelos artefatos atuais.
- O manifesto de `llama-bench` registra texto de uso no campo de versão, não uma versão semântica. A identificação verificável é o build 12024 e commit `ddf48f85c` gravados na saída de benchmark.
- A campanha foi executada em uma única GPU física. Resultados históricos do repositório são outra série experimental e não devem ser combinados com esta campanha.

## Reprodução

Na raiz do repositório, com `llama-server`, `llama-bench` e o harness na versão/commit indicados, execute no ambiente isolado do GPU Lab:

```bash
python -m llm_research_bench.campaign plan --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign run --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign summary --out results/campaigns
```

O manifesto e as saídas brutas em `results/campaigns/` são a referência para proveniência; os valores resumidos acima não substituem esses artefatos.
