# Measured results

| Split | Threshold | TP / predictions / GT | Precision | Recall | Protocol median ms |
|---|---:|---:|---:|---:|---:|
| tune | 0.05 | 462 / 736 / 801 | 62.77% | 57.68% | 28.55 |
| test | 0.05 | 424 / 675 / 639 | 62.81% | 66.35% | 26.74 |
| tune | 0.25 | 297 / 382 / 801 | 77.75% | 37.08% | 26.82 |
| test | 0.25 | 315 / 403 / 639 | 78.16% | 49.30% | 26.70 |

## Tune miss analysis

Counts below are mutually exclusive morphology proxies, not proven model causes.
A merged-link diagnosis requires additional manual prediction review. Small means
GT height <18 pixels or width <16 pixels. Prediction/GT matching is preserved in JSON.

| Threshold | Miss morphology | Count |
|---:|---|---:|
| 0.05 | small text links | 240 |
| 0.05 | other | 76 |
| 0.05 | icons / buttons | 6 |
| 0.05 | other text links | 6 |
| 0.05 | menu items | 6 |
| 0.05 | fields | 4 |
| 0.05 | rows / files | 1 |
| 0.25 | small text links | 325 |
| 0.25 | other | 133 |
| 0.25 | icons / buttons | 16 |
| 0.25 | other text links | 12 |
| 0.25 | fields | 10 |
| 0.25 | menu items | 6 |
| 0.25 | rows / files | 2 |

## Scene inventory

| Scene | Category | Split | Primary GT | Targets |
|---|---|---|---|---:|
| hn | dense_text | tune | dom | 218 |
| lobsters | dense_text | test | dom | 156 |
| wiki | content | tune | dom | 96 |
| mdn | content | test | dom | 75 |
| arch | content | tune | dom | 72 |
| github | modern_web | test | dom | 158 |
| login | forms | tune | dom | 15 |
| go | docs_sidebar | test | dom | 20 |
| hn-dark | theme_variant | tune | dom | 218 |
| arch-dark | theme_variant | test | dom | 72 |
| mdn-forms | forms | tune | dom | 54 |
| httpbin-form | forms | test | dom | 13 |
| python-docs | docs_sidebar | tune | dom | 34 |
| nautilus | native_gtk | tune | manual | 20 |
| nautilus-list | native_gtk | test | manual | 29 |
| nautilus-context | menus | tune | manual | 32 |
| nautilus-menu | menus | test | manual | 36 |
| thunar | native_gtk | tune | manual | 22 |
| thunar-menu | menus | test | manual | 17 |
| editor | native_gtk | test | manual | 6 |
| editor-menu | menus | tune | manual | 20 |
| firefox-menu | menus | test | manual | 57 |
