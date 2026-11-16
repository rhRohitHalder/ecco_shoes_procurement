# Phase 1B Silver Transformation Summary

- Run ID: `9e1ff202-33e5-4384-90f7-b42a5ec75bf7`
- Status: `SUCCEEDED`
- Target schemas: `silver`, `audit`
- Source procurement rows: **174638**
- Silver procurement rows: **174638**
- Silver distinct source IDs: **174638**
- Missing source IDs: **0**
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
- Pending UOM rows: **181**.
- Duplicate groups: **157**, preserved and not aggregated.
- Performance duplicate groups audited: **14661**;
  no KPI aggregate published.
- Missing commodity index prices: **1900**;
  no imputation.
- Exception rows written for this run: **77913**.

## Validation

Source-to-Silver row preservation, distinct source-ID preservation, source-ID
completeness, and invalid-price checks passed against the live database. Monthly FX
remains a provisional proxy because payment-date FX is unavailable. Pending approvals
are EURO semantics, UOM factors, duplicate reconciliation, missing-month
interpretation, supplier-performance weighting, and commodity-weight interpretation.
