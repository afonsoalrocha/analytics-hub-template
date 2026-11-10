---
name: new-request
description: Open the next numbered request from the template and register it.
---

# Open a request

1. Read `requests/registry.yaml` and take the next number. The folder is `requests/NNN-slug/`.
2. Copy `templates/request/README.md` into that folder and fill every heading. Link metric cards. Do not invent a metric that has no card.
3. Add `config.yaml` only for values the gates read (thresholds, filters, output paths). The README remains the human spec.
4. Append the request to `registry.yaml` with status `open` and a transition that has today's date and a reason. Leave `outcome` unset.
5. Open the worktree with `python scripts/request_worktree.py open NNN slug`. The printed command is `git worktree add ../worktree-request-NNN-slug -b worktree-request-NNN-slug`.

Leave status changes, metric status, and acceptance thresholds for the human when they are not already written in the spec.
