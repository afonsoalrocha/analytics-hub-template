# Analytics Hub Template

Um ambiente de trabalho para analistas em que cada pergunta de negócio vira uma demanda rastreável, cada número passa por um gate determinístico e cada interpretação fica registrada com histórico.

O humano é dono da arquitetura, das definições de métrica, dos critérios de aceite e da leitura do resultado. O agente implementa o SQL, os testes e os scripts. O modelo de linguagem redige e pergunta. O warehouse calcula.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make demo
```

`make demo` baixa o extrato público de e-commerce da Olist quando consegue e, na falta dele, monta uma semente sintética com as mesmas tabelas. Em seguida roda o dbt em DuckDB local, fecha a demanda 001, grava o snapshot mensal e imprime uma checagem de frete em uma linha. Nenhuma credencial de warehouse é necessária.

Para começar sem rede:

```bash
make demo-synthetic
```

## Ciclo de vida

```mermaid
flowchart TD
  A[Intake: pergunta de negócio e solicitante] --> B[Spec: o humano define métricas, grão, escopo e aceite]
  B --> C[Build: o agente implementa SQL, dbt e Python no worktree]
  C --> D{Gates passam?}
  D -->|block| C
  D -->|ok ou warn| E[Interrogação: o humano pergunta se reconcilia e por quê]
  E -->|redefinir| B
  E --> F[Log de insight: insights.md e revisão só de inclusão]
  F --> G[Fechar: validador, registro e merge]
```

Cada demanda é uma pasta `demandas/NNN-slug/` e um item em `demandas/registro.yaml`. O registro é o único índice. Os estados são `aberta`, `em_spec`, `em_build`, `em_interpretacao`, `fechada` e `pausada`. Cada transição tem data e motivo.

Fluxo git: um worktree e um branch por demanda, no nome `worktree-demanda-NNN-slug`. Abra com `git worktree add ../worktree-demanda-NNN-slug -b worktree-demanda-NNN-slug` e feche, a partir do branch base, com `git merge --no-ff worktree-demanda-NNN-slug`. O merge commit guarda a demanda como uma unidade de histórico. `python scripts/demand_worktree.py` imprime esses comandos e não os executa. Antes do merge, `python scripts/validate_completion.py --demand NNN` imprime `ok`, `partial` ou `blocked`. Uma demanda `blocked` continua aberta. Prefixos de commit: `feat(demandas)`, `docs(conhecimento)`, `docs(verificacao)`, `chore`.

## Princípios

1. O que pode ser determinístico é determinístico. SQL, testes, gates e scripts calculam.
2. O humano é dono das definições e da interpretação. O agente implementa.
3. Decisão fica escrita. `ARCHITECTURE.md` e `insights.md` guardam histórico só de inclusão.
4. Integridade bloqueia. Anomalia alerta. A severidade é explícita.
5. Métrica é `certificada`, `indicativa` ou `bloqueada`. Nada é publicado sem status.
6. Uma fonte de verdade por assunto: o registro, o card da métrica, a config da demanda.
7. Número novo reconcilia com uma fonte independente, ou a diferença fica declarada.
8. O repositório nasce privado e nasce sem dado proprietário.

## O que o exemplo responde

A demanda `001-conversao-e-receita-mensal` pergunta como andaram a demanda entregue e a receita, qual foi o ticket, quantos clientes maduros voltaram e que parcela das visitas virou pedido.

| Métrica | Status | Definição |
| --- | --- | --- |
| Pedidos entregues | certificada | Pedidos distintos com status entregue, no mês da compra |
| Receita de produtos | certificada | Soma do preço dos itens desses pedidos, sem frete |
| Ticket médio | certificada | Preço mais frete, dividido pelos pedidos entregues |
| Taxa de recompra | indicativa | Clientes maduros com 2 ou mais pedidos, sobre os clientes maduros |
| Conversão visita→pedido | bloqueada | O dataset não tem visitas, então o denominador não é inventado |

Os arquivos publicados aparecem em `demandas/001-conversao-e-receita-mensal/outputs/` depois do comando acima. Uma resposta certificada mostra período, filtros, unidade e horário da carga em `publication.json`. A taxa indicativa conserva o sufixo `_indicativo`. A métrica bloqueada não tem coluna.

O gate de variação alerta quando os pedidos entregues oscilam mais de 50% contra o mês anterior. No extrato público esse alerta aparece na rampa de 2017 e em novembro de 2017. A semente sintética foi construída para que só novembro de 2017 ultrapasse a linha. A reconciliação entre o valor dos itens e os pagamentos alerta acima de 0,5% e, nos dois extratos deste template, fica dentro da tolerância. Os alertas ficam em `outputs/gate_report.json`. Eles não impedem a gravação. Um block impede, e deixa a publicação anterior no lugar.

Uma verificação rápida está em `verificacoes-rapidas/2018-08-20-participacao-do-frete/`. Ela mede a participação do frete no último mês completo e continua sendo só uma checagem. O fechamento mensal em `automacoes/fechamento-mensal/` acrescenta meses novos e recusa reescrever um mês que já está no snapshot. As regras estão em `docs/ARCHITECTURE.md`.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `CLAUDE.md`, `.claude/skills/` | O que o agente pode implementar e o que fica com o humano |
| `demandas/` | Uma pasta por demanda, mais `registro.yaml` |
| `verificacoes-rapidas/` | Uma checagem datada, com notas e script |
| `conhecimento/` | Notas duráveis e o catálogo de métricas |
| `produtos/` | Um ativo publicado: `contrato.md`, `asset.yaml` e `CHANGELOG.md` |
| `automacoes/` | Uma rotina recorrente, com `docs/ARCHITECTURE.md`, config e testes |
| `dbt/` | Staging, a regra de mês completo, marts e views de auditoria |
| `scripts/connectors/` | DuckDB, Postgres, Databricks SQL, BigQuery, GA4, Azure Blob, Azure DevOps |
| `scripts/gates/` | Funções puras de gate e o leak scan |
| `templates/` | Demanda, arquitetura, verificação, insight, metric card, ativo |
| `tests/` | Gates, catálogo, conectores com mock, leak scan, estrutura |
| `.github/workflows/ci.yml` | ruff, sqlfluff, pytest, dbt build, estrutura, gitleaks, denylist |

## Gates

| Gate | Severidade |
| --- | --- |
| Unicidade do grão | block |
| Cobertura temporal | block |
| Completude de escopo | block |
| Domínio de valores | block |
| Mês parcial | block |
| Histórico congelado | block |
| Status da métrica | block |
| Metadados da publicação | block |
| Leak scan | block |
| Reconciliação entre fontes | warn |
| Variação anômala | warn |

O runner sai com código 1 se houver qualquer block. Um warn é impresso e o código de saída continua 0.

## Conectores

Cada conector implementa `query(sql, params)`, `identity()`, `healthcheck()` e um contexto que fecha a conexão. Credenciais vêm do ambiente (veja `.env.example`). Chamadas remotas usam HTTPS, verificam TLS e declaram timeout e retentativas. O Postgres aceita só `verify-full` e `verify-ca`.

Os conectores são somente leitura, a menos que `CONNECTOR_ALLOW_WRITE=true`. Uma leitura é uma sentença cujo primeiro verbo é `select`, `with`, `show`, `describe`, `explain` ou `values`. `CONNECTOR_DRY_RUN=true` devolve a sentença e o teto de bytes sem chamar a rede. `CONNECTOR_MAX_BYTES` (padrão 1 GiB) vai para o BigQuery como `maximumBytesBilled`. O Databricks recebe o mesmo teto como `byte_limit`, que limita os bytes devolvidos pela Statement API. `identity()` devolve a conta, o projeto ou o banco e deixa o segredo no ambiente do processo.

GA4 não é um motor SQL: `query` recebe um JSON de RunReport. O Azure Blob recebe o caminho do blob e recusa um caminho que saia do container. O Azure DevOps recebe uma sentença WIQL. Os testes usam mock e não precisam de credencial.

O padrão é DuckDB, sem credencial.

## Produtos

Cada pasta em `produtos/` é um ativo publicado. `asset.yaml` registra o papel do dono, o status (`certificada`, `indicativa` ou `bloqueada`), as fontes, a atualização e o SLA. `CHANGELOG.md` é só de inclusão. `contrato.md` é o contrato funcional.

## Guardrails do agente

`CLAUDE.md` lista as skills. A tabela sai do frontmatter de `.claude/skills/*/SKILL.md` via `scripts/render_skills.py`, e o CI falha quando a tabela commitada diverge.

`.claude/hooks/guard_paths.py` recusa leitura ou escrita de `.env` (`.env.example` continua legível), recusa diretórios temporários e recusa `python`, `pip`, `pytest`, `dbt`, `ruff` ou `sqlfluff` fora de `.venv/bin/...`. Crie o ambiente com `python3 -m venv .venv`.

`.mcp.json` chama `scripts/mcp_wrapper.py`. Tokens ficam no ambiente ou num perfil OAuth fora do repositório. O perfil precisa de `read_only: true`. O JSON não carrega credencial.

`scripts/validate_structure.py` confere pastas e arquivos obrigatórios, o registro, o catálogo de métricas, os documentos de cada demanda, o ativo de cada produto e os invariantes de cada automação. O CI roda esse script. O `docs/ARCHITECTURE.md` de uma automação declara os invariantes, inclusive zero chamadas de modelo de linguagem em tempo de execução.

## O que fica fora do git

Extratos brutos, arquivos de warehouse, saídas de demanda, snapshots de automação, o `target/` do dbt e logs ficam sem rastreio. SQL, Python, YAML e Markdown ficam no git. O `.gitignore` lista os padrões pesados, entre eles `*.duckdb`, `*.parquet`, `*.xlsx`, `demandas/**/outputs/`, `automacoes/**/snapshots/` e `dbt/target/`.

## Como impedir que nomes internos vazem

Dois checks rodam no pre-commit e no GitHub Actions:

1. O [gitleaks](https://github.com/gitleaks/gitleaks) procura segredos.
2. `scripts/gates/leak_scan.py` falha se `.leak-denylist.txt` ou `.env` estiver no índice do git, e se qualquer termo da denylist local aparecer num arquivo rastreado.

Copie `.leak-denylist.example.txt` para `.leak-denylist.txt` e troque as linhas de exemplo por termos que não podem sair: hostnames internos, nomes de schema, codinomes de projeto. A cópia fica no `.gitignore`. No CI, guarde o mesmo texto no secret `LEAK_DENYLIST` do repositório. Enquanto o secret não existir, a varredura de conteúdo não faz nada e a checagem de índice continua, então o workflow permanece verde.

```bash
pre-commit install
```

## Dados e licença

O código deste repositório é MIT. Veja `LICENSE`. Essa licença cobre o código do template. Os CSVs da Olist são uma obra à parte.

O Brazilian E-Commerce Public Dataset by Olist está publicado no [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) sob [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). NonCommercial significa que o dataset não admite uso comercial. ShareAlike significa que uma adaptação do dataset permanece sob a mesma licença. Este template não versiona esses arquivos.

`scripts/prepare_data.py` baixa a amostra CSV de [olist/work-at-olist-data](https://github.com/olist/work-at-olist-data). Esse repositório declara MIT no GitHub e entra só como fonte dos arquivos. Trate os CSVs sob a licença canônica do Kaggle, CC BY-NC-SA 4.0, que é a licença mais restritiva e exclui uso comercial. Atribua a Olist quando publicar um número desse extrato.

A semente sintética é original, determinística (`seed=42`) e pequena. A integração contínua usa essa semente para não depender do download.

## O que trocar ao adotar

- O papel do solicitante, o dono da métrica e o "quem" de cada decisão de arquitetura.
- A tolerância de 0,5% na reconciliação, o limiar de 50% na variação e a janela de 90 dias da recompra. São premissas do template, e estão registradas como tal.
- `.leak-denylist.txt` e o secret `LEAK_DENYLIST`.
- `.env`, para cada conector remoto que você for usar de verdade.
- `.mcp.json`, que chama `scripts/mcp_wrapper.py` e não carrega credencial.

O fluxo de demandas, o registro, o catálogo certificada / indicativa / bloqueada, os gates de block e warn, o snapshot congelado e os logs de decisão só de inclusão são o método. As métricas da Olist são o exemplo público.

A versão em inglês está em `README.md`.

## Autor

Afonso Rocha — [github.com/afonsoalrocha](https://github.com/afonsoalrocha)
