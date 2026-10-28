# Deliberately injected data quality conditions

The dataset contains two kinds of sparse procurement: **explicit zero-quantity monthly rows** and **entirely missing months**. Neither is equivalent to a measured market price of zero.

| Code | Issue | Correct interpretation / suggested rule |
|---|---|---|
| DQ01 | Missing order value | NULL numeric; retained as missing, not zero |
| DQ02 | Missing PO quantity | Cannot calculate unit price |
| DQ03 | GR exceeds PO | Possible timing, returns, unit or reconciliation issue |
| DQ04 | Negative goods receipt | Return or reversal; do not discard without event context |
| DQ05 | Price spike | Extreme unit-price outlier |
| DQ06 | Invalid currency | Non-ISO currency code |
| DQ07 | Invalid vendor key | FK mismatch requires master-data resolution |
| DQ08 | Duplicate business key | Repeated aggregate row; avoid double counting |
| DQ09 | Incorrect quantity unit | Unit conversion needed |
| DQ10 | Missing month for expected series | No row exists, not equivalent to zero purchase |
| DQ11 | Zero quantity with spend | Possible freight, adjustment or posting error |
| DQ12 | Delayed GR | PO in month but receipt delayed or unmatched |


Other authentic-looking challenges: supplier changes and contract expirations; variable currencies across vendors; unequal purchase frequency; different base units; time-lagged commodity exposure; receipt delays; seasonality, COVID-period dip and 2022 commodity shocks; no vendor-performance guarantee for every SKU/month.

The issue register records **injected row-level errors**, not a complete output of a data-quality scanner. Run independent checks for duplicates, referential integrity, non-negative metrics, date continuity, contract validity, normalized units and FX consistency. `DQ10` is a **structural missing-month pattern**, so there is no row-level `record_id` to enumerate it; generate the expected panel to detect these gaps. Pricing anomalies can make cached `order_value_eur` and `unit_price_local` disagree with the raw value; treat independently as fields to validate.

Suggested quality KPIs: valid FX join rate, unit price derivation rate on positive-PO rows, missing month rate by vendor–SKU, invalid vendor foreign keys, duplicate natural keys, GR/PO discrepancy ratio, and commodity-index coverage. Document tolerances and remediation ownership before fitting models.
