# Measured results

| Split | Threshold | TP / predictions / GT | Precision | Recall | Protocol median ms |
|---|---:|---:|---:|---:|---:|
| tune | 0.05 | 602 / 934 / 1045 | 64.45% | 57.61% | 90.35 |
| test | 0.05 | 430 / 770 / 659 | 55.84% | 65.25% | 88.45 |
| tune | 0.25 | 420 / 542 / 1045 | 77.49% | 40.19% | 89.67 |
| test | 0.25 | 318 / 476 / 659 | 66.81% | 48.25% | 90.58 |

## Tune miss analysis

Counts below are mutually exclusive morphology proxies, not proven model causes.
A merged-link diagnosis requires additional manual prediction review. Small means
GT height <18 pixels or width <16 pixels. Prediction/GT matching is preserved in JSON.

| Threshold | Miss morphology | Count |
|---:|---|---:|
| 0.05 | small text links | 240 |
| 0.05 | other | 165 |
| 0.05 | icons / buttons | 19 |
| 0.05 | fields | 6 |
| 0.05 | other text links | 6 |
| 0.05 | menu items | 6 |
| 0.05 | rows / files | 1 |
| 0.25 | small text links | 325 |
| 0.25 | other | 230 |
| 0.25 | icons / buttons | 38 |
| 0.25 | fields | 12 |
| 0.25 | other text links | 12 |
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
| mattermost-channel | mattermost | tune | dom | 112 |
| mattermost-thread | mattermost | tune | dom | 132 |
| mattermost-switcher | mattermost | test | dom | 20 |
