---
name: nova-demanda
description: Open the next numbered demand from the template and register it.
---

# Open a demand

1. Read `demandas/registro.yaml` and take the next number. The folder is `demandas/NNN-slug/`.
2. Copy `templates/demanda/README.md` into that folder and fill every heading. Link metric cards. Do not invent a metric that has no card.
3. Add `config.yaml` only for values the gates read (thresholds, filters, output paths). The README remains the human spec.
4. Append the demand to `registro.yaml` with status `aberta` and a transition that has today's date and a reason.
5. Use a branch named `worktree-demanda-NNN-slug`.

Leave status changes, metric status, and acceptance thresholds for the human when they are not already written in the spec.
