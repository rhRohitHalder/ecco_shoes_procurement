# Phase 2 Gold Transformation Summary

**Execution Date:** 2026-11-17  
**Status:** `SUCCEEDED`  
**Target Schema:** `gold`  
**Database:** `ecco_procurement` on PostgreSQL 18.4  
**Implementation Interface:** `data_report/notebooks/03_gold_analytics.ipynb`  

---

## 1. Summary of Implemented Models

The Phase 2 Gold Layer has been implemented and validated in live PostgreSQL. All six planned models were created with explicit DDL, constraints, primary keys, and indexing:

| Model / Table Name | Table Type | Primary Key / Grain | Implemented Rows | Validated Status |
|---|---|---|---:|:---:|
| `gold.agg_vendor_material_plant_monthly` | Aggregated Mart | `(vendor_material_id, source_plant_id, procurement_month)` | **174,481** | **PASS** |
| `gold.agg_vendor_monthly` | Aggregated Mart | `(canonical_vendor_id, procurement_month)` | **7,663** | **PASS** |
| `gold.agg_material_monthly` | Aggregated Mart | `(material_id, procurement_month)` | **87,611** | **PASS** |
| `gold.agg_commodity_exposure_monthly` | Aggregated Mart | `(material_id, commodity_id, procurement_month)` | **291,600** | **PASS** |
| `gold.dim_vendor_performance_quarterly` | Reconciled Dimension | `(vendor_id, plant_id, quarter_start)` | **15,228** | **PASS** |
| `gold.panel_forecast_base_monthly` | ML Feature Panel | `(vendor_material_id, procurement_month)` | **212,448** | **PASS** |

---

## 2. Key Transformation Logic & Architectural Achievements

### 2.1 Perfect Spend Conservation
Total EUR expenditure across all three spend aggregation marts reconciles exactly to `silver.procurement_clean`:
$$\sum 	ext{Silver Procurement Spend} = \mathbf{€232,347,252.96}$$
$$\sum 	ext{agg\_vendor\_material\_plant\_monthly} = \mathbf{€232,347,252.96} \quad (\Delta = €0.00)$$
$$\sum 	ext{agg\_vendor\_monthly} = \mathbf{€232,347,252.96} \quad (\Delta = €0.00)$$
$$\sum 	ext{agg\_material\_monthly} = \mathbf{€232,347,252.96} \quad (\Delta = €0.00)$$

### 2.2 Analytical Eligibility Enforcement
- **Expenditure Eligibility:** 174,257 transactions (€232,347,252.96) have valid FX conversions.
- **Pending EURO Alias:** 188 transactions are preserved in `pending_spend_local` and are excluded from converted EUR spend.
- **Unit Price Eligibility:** Exactly 107,459 transactions meet the strict multi-criteria price eligibility standard (valid expenditure, positive standardized quantity, compatible UOM, valid reconciliation).
- **Ineligible Volume Gating:** Ineligible records contribute to total spend reporting but do NOT distort `weighted_unit_price_eur`.

### 2.3 Duplicate Candidate Key Handling
- The 157 candidate duplicate groups (314 rows) sharing `(vendor_material_id, procurement_month)` are aggregated with `total_record_count = 2` and `has_duplicate_candidate = true`.
- No records were dropped, deleted, or silently collapsed.

### 2.4 Reconciled Vendor Performance Scorecards
- Resolves the 14,661 duplicate groups in `public.fact_vendor_performance_quarterly` (78,570 raw rows) into 15,228 unique quarterly scorecards.
- Computes delivery-lines-weighted scores alongside simple arithmetic averages.
- Explicitly flags all rows with `kpi_publication_status = 'PROVISIONAL_PENDING_APPROVAL'` to prevent joining to procurement until weighting rules are signed off.

### 2.5 Machine Learning Forecast Panel
- Generates 212,448 grid points bounded by active relationship windows `[approved_from, approved_to]`.
- Categorizes:
  - `OBSERVED`: 108,244 months with active purchasing transactions.
  - `EXPLICIT_ZERO`: 66,237 months with explicit zero volume.
  - `NO_SOURCE_ROW`: 37,967 months where no record was captured (spend remains NULL, never 0).

---

## 3. Data Integrity & Non-Mutation Audit

All existing repository and database assets were verified completely intact:
- `public` schema: All 12 source tables retain exact baseline row counts (e.g. 174,638 procurement rows, 78,570 performance rows).
- `silver` schema: All 10 silver tables retain exact baseline row counts (e.g. 174,638 clean procurement rows, 291,600 commodity rows).
- `audit` schema: All 5 audit tables retain complete historical run logs and exception registers.
- Zero destructive scripts (`TRUNCATE ... CASCADE`) were executed.

---

## 4. Known Limitations & Next Steps

### 4.1 Pending Approvals Retained as Open Flags
1. **EURO Currency Alias:** 188 records remain isolated in `pending_spend_local` pending commercial confirmation.
2. **Pending UOM Conversions:** 181 records remain in original UOMs without price derivation.
3. **Price Outliers:** 199 records remain flagged as price reconciliation outliers.
4. **Performance Weighting:** Delivery-lines weighting vs simple average requires business confirmation.
5. **Missing Commodity Prices:** 1,900 missing monthly benchmark prices remain NULL without imputation.

### 4.2 Preparation for Phase 3 (Price Forecasting)
With `gold.panel_forecast_base_monthly` and `gold.agg_material_monthly` validated, the project is ready for:
1. Feature engineering (lagged commodity exposure indices, rolling price volatility).
2. Train/validation/test chronological splitting (avoiding lookahead leakage).
3. Evaluating baseline forecasters (Seasonal Naive, Moving Average) against gradient-boosted time-series models.
