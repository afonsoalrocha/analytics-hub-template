---
name: close-request
description: Close a request after the gates and the insight log.
---

# Close a request

1. Run `python scripts/validate_completion.py --request NNN`. The outcome is `complete`, `partial`, or `blocked`. That outcome is not a lifecycle status.
2. `blocked` stops the close. `partial` may close after the human records the warning in the transition reason. `complete` closes cleanly. A paused request cannot carry an outcome; resume it before closing.
3. Run the request gates. A block means the request stays open and the publication files stay as they were.
4. Warnings are listed in the gate report. The human reads them. Do not delete a warning to make the report quiet.
5. Confirm `insights.md` exists and that the revision log is append-only.
6. Append a transition to `closed` in `requests/registry.yaml` with the date and the reason. The `status` field equals the last transition. If you record `outcome`, do it only on this closed request, as `complete` or `partial`.
7. From the base branch, run `python scripts/request_worktree.py close NNN slug` and execute the printed commands. The merge is `git merge --no-ff worktree-request-NNN-slug`. Do not close a request whose gates were not run.
