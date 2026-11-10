# Agent entry

This repository is a demand-driven analytics workspace. A human owns the architecture, the metric definitions, the acceptance criteria, and the interpretation. An agent implements.

## What calculates

SQL, dbt, Python gates, and scripts calculate. A language model may draft text, ask questions, and edit files. It does not invent a metric, a tolerance, or a number that the warehouse did not produce.

## What an agent may decide

- File layout inside the demand worktree, names of intermediate models, and how a declared rule is implemented.
- A failing test or a failing gate. Fix the implementation, or stop and report the failure.
- The wording of a commit, using the prefixes below.

## What an agent leaves to the human

- Opening, pausing, or closing a demand, and the reason recorded on each transition.
- The status of a metric: `certificada`, `indicativa`, or `bloqueada`.
- Changing a gate from `block` to `warn`, or the other way around.
- Editing an earlier decision in `ARCHITECTURE.md` or an earlier entry in an insight revision log. Both logs are append-only.
- Filling `.leak-denylist.txt`. That file stays untracked.

## Flow

1. Read `demandas/registro.yaml`. It is the only index of demands.
2. Work on one demand at a time, on a branch named `worktree-demanda-NNN-slug`.
3. Implement from the demand README and the metric cards. Thresholds live in the demand `config.yaml`.
4. Run the gates. A `block` stops the write. A `warn` is reported and the publication continues.
5. The human writes the interpretation in `insights.md`.
6. Closing the demand appends a `fechada` transition and merges the branch.

States: `aberta`, `em_spec`, `em_build`, `em_interpretacao`, `fechada`, `pausada`. Each transition has a date and a reason.

## Publication rules

- A blocked metric has no column in a published file.
- An indicative metric is published with the `_indicativo` suffix.
- A certified answer shows the period, the filters, the unit, and the load time.
- A missing segment stays missing. Do not fill it with zero.
- An open or incomplete month stays out.
- A month already written by `automacoes/fechamento-mensal` is frozen.

## Connectors

Remote connectors read credentials from the environment, use HTTPS, and verify TLS. Do not set `verify=False` or a Postgres `sslmode` of `disable`, `allow`, or `prefer`.

## Commits

`feat(demandas)`, `docs(conhecimento)`, `docs(verificacao)`, `chore`.

## Skills

- `.claude/skills/nova-demanda`
- `.claude/skills/verificacao`
- `.claude/skills/metric-card`
- `.claude/skills/fechar-demanda`
