---
name: quick-check
description: Record a one-off check under quick-checks.
---

# Quick check

1. Create `quick-checks/YYYY-MM-DD-slug/`.
2. Copy `templates/quick-check/notes.md` and fill Question, Query, Result, Conclusion, and whether it becomes a request.
3. Put the query in a script in the same folder. The script reads the warehouse and prints one result. It does not publish a metric.
4. The conclusion is one line. If the check should become a request, stop and use the new-request skill instead of expanding the script into a mart.
