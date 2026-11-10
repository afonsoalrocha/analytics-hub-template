---
name: verificacao
description: Record a one-off check under verificacoes-rapidas.
---

# Quick verification

1. Create `verificacoes-rapidas/YYYY-MM-DD-slug/`.
2. Copy `templates/verificacao/notas.md` and fill Question, Query, Result, Conclusion, and whether it becomes a demand.
3. Put the query in a script in the same folder. The script reads the warehouse and prints one result. It does not publish a metric.
4. The conclusion is one line. If the check should become a demand, stop and use the nova-demanda skill instead of expanding the script into a mart.
