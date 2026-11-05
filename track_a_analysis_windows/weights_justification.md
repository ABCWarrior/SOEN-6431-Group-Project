<!-- Where this goes: Track A report, section 1.2 (Debt heatmap and summary table), right after the sentence that states the weights. -->

## Justify the weights

The weights are a judgement call. Complexity counts most (30%) because it directly measures how hard the code is to understand and change. Change count comes second (20%) because code that is both complex and frequently edited is where maintenance cost actually lands, the idea behind hotspot analysis (Tornhill, 2015). Missed coverage, rule findings, duplication and coupling (15%, 15%, 10%, 10%) are supporting signals.

Because the weights are not derived from theory, we checked how much the result depends on them (`score_sensitivity.py`, standard library only, reading `raw/debt_summary_by_file.csv`):

- The same top three files (`core.py`, `cli/argparser.py`, `client.py`) appear under the reported weights, under equal weights, under the spec's four signals alone (complexity, churn, coverage, duplication), and under complexity alone. Only a churn-only weighting changes them (6 of 7 weightings agree).
- Over 5,000 random weightings, `core.py` ranks first in about 90% when each weight is drawn uniformly from 0 to 1 and then normalised, and in about 77% when the weights are drawn uniformly over all possible weight sets (fixed seed). The share depends on how the random weights are drawn, so both are reported.

The ranking is therefore reasonably stable, but the exact score values should not be read as precise.
