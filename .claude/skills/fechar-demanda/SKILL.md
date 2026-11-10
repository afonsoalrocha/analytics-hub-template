---
name: fechar-demanda
description: Close a demand after the gates and the insight log.
---

# Close a demand

1. Run the demand gates. A block means the demand stays open and the publication files stay as they were.
2. Warnings are listed in the gate report. The human reads them. Do not delete a warning to make the report quiet.
3. Confirm `insights.md` exists and that the revision log is append-only.
4. Append a transition to `fechada` in `demandas/registro.yaml` with the date and the reason. The `status` field equals the last transition.
5. The merge of `worktree-demanda-NNN-slug` is the close. Do not close a demand whose gates were not run.
