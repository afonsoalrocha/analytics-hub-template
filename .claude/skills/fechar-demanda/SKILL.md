---
name: fechar-demanda
description: Close a demand after the gates and the insight log.
---

# Close a demand

1. Run `python scripts/validate_completion.py --demand NNN`. The label is `ok`, `partial`, or `blocked`.
2. `blocked` stops the close. `partial` may close after the human records the warning in the transition reason. `ok` closes cleanly.
3. Run the demand gates. A block means the demand stays open and the publication files stay as they were.
4. Warnings are listed in the gate report. The human reads them. Do not delete a warning to make the report quiet.
5. Confirm `insights.md` exists and that the revision log is append-only.
6. Append a transition to `fechada` in `demandas/registro.yaml` with the date and the reason. The `status` field equals the last transition.
7. From the base branch, run `python scripts/demand_worktree.py close NNN slug` and execute the printed commands. The merge is `git merge --no-ff worktree-demanda-NNN-slug`. Do not close a demand whose gates were not run.
