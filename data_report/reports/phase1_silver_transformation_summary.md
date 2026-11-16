# Phase 1B Silver Transformation Summary

- Run ID: `a46283ee-3219-4b82-a2ac-18cf95799aea`
- Status: `SUCCEEDED`
- Target schemas: `silver`, `audit`
- Source procurement rows: **174638**
- Silver procurement rows: **174638**
- Silver distinct source IDs: **174638**
- Source-to-Silver missing IDs: **0**
- Silver-to-source extra IDs: **0**
- Source duplicate IDs: **0**
- Silver duplicate IDs: **0**
- Invalid non-null unit prices: **0**

## Implemented

Created Silver dimensions/reference tables, `silver.procurement_relationship`,
source-preserving `silver.procurement_clean`, and
`silver.material_commodity_monthly`. Created transformation-run, exception,
procurement-duplicate, and supplier-performance investigation audit tables.
Gold tables were not created.

## Actual treatment

- Vendor mismatches: **198**.
- EURO alias rows: **188**, retained as
  `ALIAS_PENDING` without contract-currency fallback.
- FX provenance: EUR rows use `IDENTITY_RATE`; non-EUR rows use
  `MONTHLY_AVERAGE_PROXY`; EURO remains `ALIAS_PENDING`.
- Pending UOM rows: **181**.
- Duplicate groups: **157**, preserved and not aggregated.
- Duplicate history runs retained: **5**.
- Performance duplicate groups audited: **14661**;
  no KPI aggregate published.
- Missing commodity index prices: **1900**;
  no imputation.
- Exception rows written for this run: **77913**.
- Exception-count mismatches: **0**.
- Price reconciliation: **107629** matches,
  **199** outliers, and
  **66810** not testable. Outliers were retained
  for investigation; source values were not overwritten.

## Correction status

- Commodity weight validation: **PASS** (`{'VALIDATED': 291600}`).
- UOM mapping preservation: **PASS**.
- Exception counts: **PASS**.
- Dimension/reference constraints and indexes: **PASS**.
- Duplicate investigation history: **PASS**.
- Pilot source/transformed-value validation: **PASS**
  for 10 records.
- Missing-month Gold-scope readiness check: **PASS**; no Silver row was created.
- Source-ID anti-joins and uniqueness: **PASS**.
- Price reconciliation and known outlier investigation: **PASS**; outliers remain open.
- Failed-run metadata path: **PASS**; failure status is persisted outside the publication transaction.

Monthly FX remains a provisional proxy because payment-date FX is unavailable.
Pending approvals are EURO semantics, UOM factors, duplicate reconciliation,
missing-month interpretation, supplier-performance weighting, commodity-weight
interpretation, and price outlier disposition.
