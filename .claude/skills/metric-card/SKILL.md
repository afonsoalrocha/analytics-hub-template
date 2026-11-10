---
name: metric-card
description: Add or revise a metric card and render it.
---

# Metric card

1. Copy `templates/metric-card.yaml` to `knowledge/metrics/<id>.yaml`.
2. Set `status` to `certified`, `indicative`, or `blocked`. A blocked card needs a `block_reason`. Any other status keeps `block_reason: null`.
3. Append the change to `history`. Leave earlier history entries in place.
4. Add the id to `knowledge/index.yaml`. The index and the folder must list the same ids.
5. Run `python scripts/render_metrics.py` and commit the generated Markdown.
6. An indicative metric is published only as `<id>_indicative`. A blocked metric is published nowhere.
