# Illustrative propensity baseline

The seed `20260417` produces exactly 1,000 profiles. Inputs are visits in 30 days, purchases in 180 days, days since purchase, and average order value. Region is displayed but not scored. Eligibility is a separate deterministic policy flag and is checked before scoring. No protected attributes, raw identifiers, consent, or agent confidence are model features.

The baseline is a fixed logistic expression: `sigmoid(-2.2 + .055*visits + .24*purchases - .003*recency + .0012*AOV)`. An example synthetic outcome label for offline experimentation is “upgrade within 30 days”; this reference does not fit against that label, claim calibration, or choose an operating threshold. Determinism is tested by fixed generation and expression code.

These scores are illustrative ranks, not validated predictions. Synthetic evaluation cannot establish generalization, fairness, calibration, causal effect, or incremental campaign lift. A real deployment must define temporal train/test splits, leakage checks, precision/recall and calibration by relevant cohorts, drift monitoring, fairness review, and a randomized holdout for incremental lift. Consent remains a hard independent input regardless of score.
