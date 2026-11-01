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
- Um diagnóstico GSM8K separado com 20 itens usou `enable_thinking=false`, zero-shot, seed 42, `max_gen_toks=384`, `eos_string=<|im_end|>` e o harness pinado. O conteúdo da API correspondeu à resposta do harness nos 20 itens; nenhum continha o marcador `####`. A geração parou normalmente em 18/20 e atingiu o limite de tokens em 2/20; `reasoning_content` não apareceu. O template efetivo do servidor foi observado via `/props` (SHA-256 `87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5`).
- Nesse diagnóstico, o filtro oficial estrito retornou `[invalid]` em 20/20. O filtro flexível marcou 0/20 como inválidos, mas extraiu `$$` em 9/20; portanto, a taxa de inválidos não significa que a extração esteja correta. O formato gerado pelo modelo é incompatível com o esperado pelo GSM8K (`#### <número>`); tarefas/filtros oficiais não foram alterados e não há alegação de acurácia. Consulte `results/diagnostics/pr9-gsm8k-n20-20261101T174900Z/` para requisições/respostas sanitizadas, análise por item, propriedades observadas do servidor, identidade do modelo e saídas do harness.
- O executor local do diagnóstico pareado zero-shot/cinco-shot foi implementado, mas **a execução está pendente**: os scripts do repositório documentam o entrypoint do sandbox, que roda a campanha smoke completa, mas não documentam um comando autorizado do launcher para um diagnóstico isolado. O gateway restrito do GPU Lab rejeitou consultas de ajuda/status. Nenhum desvio do gateway, alteração de acesso/configuração ou job remoto foi tentado; os resultados comparativos e qualquer validação maior continuam pendentes.
- O diagnóstico anterior de um item com thinking ativo retornou `message.content` vazio, `reasoning_content` não vazio e `finish_reason=length` nos limites de 256 e 384 tokens; o harness reproduziu fielmente o conteúdo vazio. Esse comportamento não apareceu na execução de 20 itens com thinking desativado. Os artefatos e a pontuação smoke originais permanecem inalterados; o diagnóstico é uma série separada e não justifica corrigir a pontuação.
- Os artefatos originais da campanha smoke não comprovam o template efetivo: o JSON do harness registra template/hash vazios. O diagnóstico separado registra o template observado via `/props`. Para execuções futuras, o orquestrador transmite `max_gen_toks` configurado (padrão 256), `eos_string` opcional e `chat_template_kwargs` opcionais no servidor.
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
