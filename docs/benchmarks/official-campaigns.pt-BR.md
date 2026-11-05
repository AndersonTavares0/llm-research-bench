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
- O entrypoint do sandbox agora oferece o modo fixo `GPU_LAB_TASK=gsm8k-paired`, que executa somente `tools/homelab/gsm8k-diagnostic.sh`; o padrão continua sendo a campanha completa e outros valores são rejeitados antes da configuração. Selecione esse modo no ambiente de um `gpu-lab job` já autorizado; não são aceitos argumentos de comando ou script. **A execução pareada continua pendente** porque este repositório não documenta como o gateway externo restrito encaminha essa variável de ambiente. Nenhum desvio do gateway, alteração de acesso/configuração ou job remoto foi tentado; a comparação e qualquer validação maior aguardam a confirmação da interface suportada pelo gateway para definir variáveis de ambiente.
- O diagnóstico anterior de um item com thinking ativo retornou `message.content` vazio, `reasoning_content` não vazio e `finish_reason=length` nos limites de 256 e 384 tokens; o harness reproduziu fielmente o conteúdo vazio. Esse comportamento não apareceu na execução de 20 itens com thinking desativado. Os artefatos e a pontuação smoke originais permanecem inalterados; o diagnóstico é uma série separada e não justifica corrigir a pontuação.
- Os artefatos originais da campanha smoke não comprovam o template efetivo: o JSON do harness registra template/hash vazios. O diagnóstico separado registra o template observado via `/props`. Para execuções futuras, o orquestrador transmite `max_gen_toks` configurado (padrão 256), `eos_string` opcional e `chat_template_kwargs` opcionais no servidor.
- O manifesto de `llama-bench` registra texto de uso no campo de versão, não uma versão semântica. A identificação verificável é o build 12024 e commit `ddf48f85c` gravados na saída de benchmark.
- A campanha foi executada em uma única GPU física. Resultados históricos do repositório são outra série experimental e não devem ser combinados com esta campanha.

## Campanha GPU Lab v2: Qwen3-1.7B na GTX 1050 Ti (exploratória)

Artefatos completos: [`results/campaigns/gpu-lab-qwen3-1.7b-v2/`](../../results/campaigns/gpu-lab-qwen3-1.7b-v2/).
Spec: [`configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml`](../../configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml).

**Status: exploratória.** O protocolo não foi pré-registrado e uma configuração
de hardware foi medida uma vez; os valores descrevem esta execução. Não autorizam
ranking de modelos nem são comparáveis aos escores com limite 20 da campanha smoke.

| Dimensão | Detalhes |
|---|---|
| Hardware | GTX 1050 Ti, 4 GiB; Ryzen 5 3600; GPU Lab CT108 (LXC 108 no Proxmox `v01`) |
| Modelo | Qwen3-1.7B Q4_K_M (1.276.487.680 bytes carregados; 2.031.739.904 parâmetros) |
| SHA-256 do GGUF | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Harness | lm-evaluation-harness `0.4.14.dev0`, commit fixado `d6de81643928d653435c431bae19945d41d32520` |
| Runtime | llama.cpp `0.8.0-dev`, build 12024, commit `ddf48f85c`, build CUDA |
| Servidor | ctx 4096, 99 camadas na GPU, 2 threads, `--parallel 1`, `enable_thinking=false`, `--cache-ram 0` |
| Amostra | limite 100 por tarefa (primeiros N, determinístico); seed 42; zero-shot |
| Execução | um lease `gpu-lab job`, geração 168 |

### Qualidade (n=100 por tarefa)

Intervalos de Wilson 95% tratam os 100 itens como sorteios de Bernoulli: medem
incerteza de amostragem de itens, não variância entre execuções.

| Tarefa | Métrica | Valor | IC 95% |
|---|---|---:|---|
| ARC Challenge | acc | 0,470 | 0,375–0,567 |
| ARC Challenge | acc_norm | 0,470 | 0,375–0,567 |
| HellaSwag | acc | 0,440 | 0,347–0,538 |
| HellaSwag | acc_norm | 0,470 | 0,375–0,567 |
| GSM8K | exact match estrito | 0,000 | 0,000–0,037 |
| GSM8K | extração flexível | 0,460 | 0,366–0,557 |
| IFEval | prompt-level estrito | 0,680 | 0,583–0,763 |
| IFEval | prompt-level flexível | 0,720 | 0,625–0,799 |
| IFEval | instruction-level estrito | 0,755 | 0,662–0,829 |
| IFEval | instruction-level flexível | 0,791 | 0,702–0,860 |

A diferença em GSM8K é **de formato**, não evidência de incapacidade
aritmética: o modo estrito exige o marcador `#### <número>` e as gerações
terminam com a resposta em prosa. As respostas cruas inspecionadas mostram
cadeias de raciocínio corretas sem o marcador.

### Throughput (llama-bench, 10 repetições)

| Operação | Tokens | Média | DP | EPM | IC 95% (t, gl=9) |
|---|---|---:|---:|---:|---|
| Prefill | 512 | 848,835 tok/s | 1,892 | 0,598 | 847,48–850,19 |
| Decode | 128 | 48,030 tok/s | 0,015 | 0,005 | 48,020–48,041 |

O `llama-bench` roda em processo próprio com 6 threads e não usa o servidor de
avaliação, então não é afetado pelo `--cache-ram`. Warm-up é desprezível: a
primeira repetição é 0,33% mais rápida que as nove seguintes no prefill e 0,04%
no decode, ambos dentro do intervalo.

### Tempo de parede e memória observados

- Grupo de conhecimento: 200 itens em 216 s (1,08 s/item).
- Grupo generativo: 200 itens em 1.064 s (5,32 s/item); as gerações longas do
  IFEval dominam.
- Memória de GPU em uso durante a avaliação: 1,21–1,61 GiB (amostragens pontuais
  com `nvidia-smi`). Não é uma série temporal; não houve medição de pico.
- Utilização da GPU 88–98% nas amostragens pontuais.
- Sem telemetria de potência, clock ou temperatura: não há alegação de
  tokens/joule nem de throttling térmico.

### O que este experimento estabelece — e o que não estabelece

- **Reprodutível:** um segundo lease repetiu o grupo de conhecimento com escores
  idênticos (ARC 0,47/0,47; HellaSwag 0,44/0,47), esperado a temperatura 0 sobre
  o mesmo subconjunto. É verificação de consistência, não estimativa de variância.
- **Replicação não independente:** 100 itens por tarefa não são 100 réplicas de
  hardware; os dois grupos compartilham GPU, lease e histórico térmico.
- **Confundidores:** o sandbox limita o job a 3 GiB de RAM e 1,5 CPU; o servidor
  usou 2 threads e o `llama-bench` 6; o LXC hospeda outros serviços. A latência
  por item inclui fila e preempção que uma máquina dedicada não teria.
- **Uma tentativa abortada:** a primeira execução generativa (geração 167) foi
  morta pelo cgroup de memória em 50/200 requisições porque o cache de prompt do
  llama.cpp é ilimitado por padrão. A execução concluída fixa `--cache-ram 0`.
  A tentativa abortada não gerou valores de qualidade.

### Ciclo de vida do gpu-lab: preempção, bug e restauração

A GPU não está "presa": o serviço de inferência de produção (Qwen3.5-4B) é o
dono ocioso da placa. O lease do laboratório o preempta durante o job e o
restaura depois; inferência externa recebe HTTP 503 enquanto o lease está ativo.

Um bug de agendamento apareceu na primeira tentativa: o reaper
(`gpu-lab-controller reap`, a cada 30 s pelo watchdog) tratava a tentativa de job
como órfã durante a janela de aquisição, porque o registro do supervisor só é
gravado no bind. Ele restaurava a produção no meio da aquisição e recusava o
grant. A correção faz o ramo de job só fazer reap quando existe registro de
supervisor e o PID está morto; o TTL do lease cobre a janela pré-bind. Backup:
`/root/gpu_lab_controller.py.bak-20261105T124243Z`. `gpu-labctl reconcile`
retorna `healthy`.

Evidência de restauração do run concluído: a tentativa terminal da geração 168 é
`mode=job`, `reason=supervisor_stopped`, `result=restored`; o controlador voltou a
`production/production`; o gateway de produção respondeu `GET /health` com 200.

### Limitações

- Não pré-registrada; nenhuma hipótese confirmatória fixada de antemão.
- Um modelo, uma quantização, uma GPU, um lease por configuração.
- `--limit 100` são os primeiros 100 itens, não uma amostra aleatória/estratificada.
- Zero-shot em tudo; o padrão do GSM8K no harness é 5-shot, então os valores não
  são comparáveis ao protocolo padrão.
- Sem telemetria de potência, clock ou temperatura; sem controle de regime térmico.
- Os intervalos de acurácia assumem itens independentes; itens de benchmark
  costumam ser agrupados.

### Protocolo de acompanhamento proposto

Os testes de estresse do controlador de lease, a auditoria dos artefatos e o
protocolo detalhado estão em [`gpu-lab-hardening.md`](gpu-lab-hardening.md).

1. Pré-registrar hipótese, métricas primárias e análise, incluindo a família de
   comparações múltiplas.
2. Cinco leases independentes por configuração, ordem aleatorizada, com
   cool-down fixo e temperatura da GPU registrada antes de cada lease.
3. Amostrar clock, potência, temperatura e memória a 1 Hz durante todo o run
   (`nvidia-smi --query-gpu=... --loop-ms=1000`); relatar tokens/joule apenas com
   sensor de potência presente.
4. Rodar splits completos (sem `--limit`), GSM8K 5-shot e uma ablação de
   EOS/stop-sequence para separar falha de formato de falha de capacidade.
5. Analisar itens com bootstrap pareado no conjunto compartilhado e relatar o
   efeito mínimo detectável para o tamanho de amostra planejado.

## Reprodução

Na raiz do repositório, com `llama-server`, `llama-bench` e o harness na versão/commit indicados, execute no ambiente isolado do GPU Lab:

```bash
python -m llm_research_bench.campaign plan --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign run --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign summary --out results/campaigns
```

O manifesto e as saídas brutas em `results/campaigns/` são a referência para proveniência; os valores resumidos acima não substituem esses artefatos.
