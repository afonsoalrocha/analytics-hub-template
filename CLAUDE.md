# Agent entry

This repository is a demand-driven analytics workspace. A human owns the architecture, the metric definitions, the acceptance criteria, and the interpretation. An agent implements.

## What calculates

SQL, dbt, Python gates, and scripts calculate. A language model may draft text, ask questions, and edit files. It does not invent a metric, a tolerance, or a number that the warehouse did not produce. An automation makes zero language-model calls at runtime.

## What an agent may decide

- File layout inside the demand worktree, names of intermediate models, and how a declared rule is implemented.
- A failing test or a failing gate. Fix the implementation, or stop and report the failure.
- The wording of a commit, using the prefixes below.

## What an agent leaves to the human

- Opening, pausing, or closing a demand, and the reason recorded on each transition.
- The status of a metric: `certificada`, `indicativa`, or `bloqueada`. The same three words are the status of a product asset.
- Changing a gate from `block` to `warn`, or the other way around.
- Editing an earlier decision in `ARCHITECTURE.md` or an earlier entry in an insight revision log. Both logs are append-only.
- Filling `.leak-denylist.txt`. That file stays untracked.

## Flow

1. Read `demandas/registro.yaml`. It is the only index of demands.
2. Work on one demand at a time. Open a worktree and a branch together:

```bash
python scripts/demand_worktree.py open 001 conversao-e-receita-mensal
```

The printed command is `git worktree add ../worktree-demanda-001-conversao-e-receita-mensal -b worktree-demanda-001-conversao-e-receita-mensal main`. Run the printed command. The script itself does not touch git.

3. Implement from the demand README and the metric cards. Thresholds live in the demand `config.yaml`.
4. Run the gates. A `block` stops the write. A `warn` is reported and the publication continues.
5. The human writes the interpretation in `insights.md`.
6. Before closing, run `python scripts/validate_completion.py --demand 001`. The label is `ok`, `partial`, or `blocked`. `blocked` stops the close. `partial` may close after the human records the warning in the transition reason.
7. Append the `fechada` transition, then close the worktree with a merge commit:

```bash
python scripts/demand_worktree.py close 001 conversao-e-receita-mensal
```

The printed commands check out the base branch, run `git merge --no-ff worktree-demanda-001-conversao-e-receita-mensal`, and remove the worktree.

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

Connectors are read-only unless `CONNECTOR_ALLOW_WRITE=true`. A read is one statement whose first verb is `select`, `with`, `show`, `describe`, `explain`, or `values`. `CONNECTOR_DRY_RUN=true` returns the statement and the byte ceiling without a network call. `CONNECTOR_MAX_BYTES` is sent as BigQuery `maximumBytesBilled` and as Databricks `byte_limit`. `identity()` returns the account, project, or database and leaves the secret in the process environment.

## Path guard

`.claude/hooks/guard_paths.py` runs before read, write, and shell tools. It refuses `.env` (`.env.example` stays readable), anything under a temp directory, and any `python`, `pip`, `pytest`, `dbt`, `ruff`, or `sqlfluff` binary that is not `.venv/bin/...`. Create the environment with `python3 -m venv .venv`.

## MCP

`.mcp.json` names `scripts/mcp_wrapper.py` and a server id. Tokens stay in the environment or in an OAuth profile outside the repo (`MCP_OAUTH_PROFILE`, default `~/.config/analytics-hub/oauth-readonly.json`). The profile must set `read_only` to true. The wrapper refuses to start otherwise. The JSON file holds no credentials.

## Heavy artifacts

Raw extracts, warehouse files, demand outputs, automation snapshots, `dbt/target/`, and logs stay out of git. SQL, Python, YAML, and Markdown stay in git.

## Commits

`feat(demandas)`, `docs(conhecimento)`, `docs(verificacao)`, `chore`.

## Skills

The catalog below is generated from the frontmatter of `.claude/skills/*/SKILL.md`. `python scripts/render_skills.py --check` fails when this section drifts.

<!-- skills:start -->
| Skill | Path | Description |
| --- | --- | --- |
| `fechar-demanda` | `.claude/skills/fechar-demanda/SKILL.md` | Close a demand after the gates and the insight log. |
| `metric-card` | `.claude/skills/metric-card/SKILL.md` | Add or revise a metric card and render it. |
| `nova-demanda` | `.claude/skills/nova-demanda/SKILL.md` | Open the next numbered demand from the template and register it. |
| `verificacao` | `.claude/skills/verificacao/SKILL.md` | Record a one-off check under verificacoes-rapidas. |
<!-- skills:end -->
