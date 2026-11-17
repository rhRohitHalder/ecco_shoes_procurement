# Phase 2 Gold Layer Schema Design & Technical Specifications

**Document version:** 1.0  
**Phase:** Phase 2 (Gold Layer Analytics Marts)  
**Schema:** `gold`  
**Database:** `ecco_procurement` on PostgreSQL 18.4  
**Primary Engine:** PostgreSQL 18.4 (persistent SQL execution)  
**Orchestration Interface:** `data_report/notebooks/03_gold_analytics.ipynb`  
**Author:** Antigravity Data Engineering  
**Date:** 2026-11-17  

---

## 1. Architectural Overview & Context

The **ECCO Procurement Analytics** data platform follows a strict **Medallion (Bronze/Silver/Gold) Architecture**:

```text
[Raw / Source CSVs & Database Loader]
                 |
                 v
       PostgreSQL: public schema
       (12 source tables; strictly unmodified)
                 |
                 v
       PostgreSQL: silver schema
       (source-preserving, typed, standardized, quality-flagged)
                 |
          +------+------+
          |             |
          v             v
  PostgreSQL: audit   PostgreSQL: gold
  (run history,       (curated business marts,
   exceptions,         reconciled dimensions,
   duplicate reviews)  forecast panel)
```

### Purpose of the Gold Layer
While the **Silver layer** preserves source records with 1:1 fidelity and comprehensive anomaly flagging, the **Gold layer** serves business users, category managers, procurement leadership, and downstream machine learning models by providing:
1. **Aggregated Business Marts:** Pre-calculated expenditures, quantities, and price benchmarks grouped by strategic business entities.
2. **Strict Analytical Eligibility Gating:** Separates total reported financial expenditure from unit-price comparable volume to prevent false vendor price rankings.
3. **Transparent Governance:** Preserves duplicate candidate records, currency alias flags, and raw observation counts rather than silently deleting or collapsing them.
4. **Machine Learning Readiness:** Implements a continuous, bounded panel matrix for Phase 3 price forecasting.

---

## 2. Gold Data Models Summary

| Table Name | Primary Business Purpose | Grain / Primary Key | Source Tables | Row Count |
|---|---|---|---|---:|
| `gold.agg_vendor_material_plant_monthly` | Relationship-level monthly procurement mart | `(vendor_material_id, source_plant_id, procurement_month)` | `silver.procurement_clean` | 174,481 |
| `gold.agg_vendor_monthly` | Vendor spend concentration and portfolio breadth | `(canonical_vendor_id, procurement_month)` | `silver.procurement_clean`, `silver.vendor` | 7,663 |
| `gold.agg_material_monthly` | SKU price benchmarking and competition index | `(material_id, procurement_month)` | `silver.procurement_clean`, `silver.material` | 87,611 |
| `gold.agg_commodity_exposure_monthly` | Upstream raw material commodity exposure | `(material_id, commodity_id, procurement_month)` | `silver.material_commodity_monthly`, `silver.commodity`, `silver.material` | 291,600 |
| `gold.dim_vendor_performance_quarterly` | Reconciled supplier performance scorecards | `(vendor_id, plant_id, quarter_start)` | `public.fact_vendor_performance_quarterly` | 15,228 |
| `gold.panel_forecast_base_monthly` | Continuous matrix for price forecasting | `(vendor_material_id, procurement_month)` | `silver.procurement_relationship`, `silver.procurement_clean`, `silver.material` | 212,448 |

---

## 3. Detailed Model Specifications

### 3.1 `gold.agg_vendor_material_plant_monthly`
- **Purpose:** Primary granular analytical mart representing monthly sourcing relationships. Evaluates plant-level spend, delivery quantities, weighted average unit prices, and quality flags.
- **Grain:** One row per `(vendor_material_id, source_plant_id, procurement_month)`.
- **Primary Key:** `(vendor_material_id, source_plant_id, procurement_month)`.
- **Source Lineage:** `silver.procurement_clean`.
- **Key Transformation Rules:**
  - `total_spend_eur`: Sum of `eur_expenditure`. Reconciles exactly to Silver.
  - `eligible_spend_eur`: Spend from transactions with valid FX conversion and non-null values.
  - `pending_spend_local`: Unconverted spend from `ALIAS_PENDING` EURO records; never converted to EUR without approved commercial authorization.
  - `comparable_po_quantity`: Sum of standardized PO quantities where `eur_unit_price IS NOT NULL`.
  - `weighted_unit_price_eur`: $rac{\sum (	ext{eligible eur\_expenditure})}{\sum (	ext{comparable standardized\_po\_qty})}$.
  - `has_duplicate_candidate`: `TRUE` if any underlying transaction belongs to the 157 candidate duplicate groups.
  - `has_vendor_mismatch`: `TRUE` if reported vendor disagrees with canonical sourcing bridge vendor.

### 3.2 `gold.agg_vendor_monthly`
- **Purpose:** Vendor-level monthly procurement mart. Enables supplier management to assess spend concentration, active plant footprints, category coverage, and data quality exceptions.
- **Grain:** One row per `(canonical_vendor_id, procurement_month)`.
- **Primary Key:** `(canonical_vendor_id, procurement_month)`.
- **Source Lineage:** `silver.procurement_clean` joined with `silver.vendor`.
- **Key Transformation Rules:**
  - `canonical_vendor_id`: Uses authoritative bridge vendor ID.
  - `active_materials_count`: `COUNT(DISTINCT source_material_id)`.
  - `active_plants_count`: `COUNT(DISTINCT source_plant_id)`.
  - `active_relationships_count`: `COUNT(DISTINCT vendor_material_id)`.
  - `duplicate_record_count`: Number of underlying duplicate candidate records for the vendor in the month.
  - `vendor_mismatch_record_count`: Number of records where reported vendor differed from canonical vendor.

### 3.3 `gold.agg_material_monthly`
- **Purpose:** Material/SKU-level monthly procurement mart. Analyzes commodity price trends, volume inflation/deflation, portfolio benchmark prices, and vendor competition.
- **Grain:** One row per `(material_id, procurement_month)`.
- **Primary Key:** `(material_id, procurement_month)`.
- **Source Lineage:** `silver.procurement_clean` joined with `silver.material`.
- **Key Transformation Rules:**
  - `weighted_unit_price_eur`: Weighted average unit price across all plants and vendors for the SKU.
  - `min_unit_price_eur` / `max_unit_price_eur`: Minimum and maximum unit prices observed for the material in the month.
  - `active_vendors_count`: Number of distinct suppliers delivering the material in the month.
  - `active_plants_count`: Number of distinct manufacturing plants consuming the material.
  - `price_outlier_record_count`: Count of transactions flagged as price reconciliation outliers.

### 3.4 `gold.agg_commodity_exposure_monthly`
- **Purpose:** Connects procurement materials to international commodity benchmark indices (e.g., rubber, leather, polyurethane, cotton). Evaluates cost sensitivity to upstream market shifts.
- **Grain:** One row per `(material_id, commodity_id, procurement_month)`.
- **Primary Key:** `(material_id, commodity_id, procurement_month)`.
- **Source Lineage:** `silver.material_commodity_monthly`, `silver.commodity`, `silver.material`.
- **Key Transformation Rules:**
  - `exposure_weight`: Verified material-to-commodity exposure factor from the bridge.
  - `index_price`: Benchmark market index value. Preserved as `NULL` when missing (1,900 observations); no arbitrary mathematical imputation.
  - `weighted_index_contribution`: $	ext{exposure\_weight} 	imes 	ext{index\_price}$ (NULL when price is missing).
  - `weight_validation_status`: Validated status from Silver ($100\%$ `VALIDATED`).

### 3.5 `gold.dim_vendor_performance_quarterly`
- **Purpose:** Reconciled quarterly vendor scorecard dimension. Solves the 14,661 duplicate groups in raw performance data by computing delivery-lines-weighted scores alongside simple averages.
- **Grain:** One row per `(vendor_id, plant_id, quarter_start)`.
- **Primary Key:** `(vendor_id, plant_id, quarter_start)`.
- **Source Lineage:** `public.fact_vendor_performance_quarterly`.
- **Key Transformation Rules:**
  - `observation_count`: Total raw performance records for this vendor, plant, and quarter.
  - `total_delivery_lines`: Sum of delivery lines across observations.
  - `weighted_on_time_delivery_pct`: $rac{\sum (	ext{on\_time\_delivery\_pct} 	imes 	ext{delivery\_lines})}{\sum 	ext{delivery\_lines}}$.
  - `weighted_defect_rate_pct`: $rac{\sum (	ext{defect\_rate\_pct} 	imes 	ext{delivery\_lines})}{\sum 	ext{delivery\_lines}}$.
  - `has_multiple_observations`: `TRUE` if `observation_count > 1` (14,661 groups).
  - `kpi_publication_status`: Preserved as `'PROVISIONAL_PENDING_APPROVAL'` to enforce safety guardrail F (no direct join to procurement until weighting is approved).

### 3.6 `gold.panel_forecast_base_monthly`
- **Purpose:** Machine learning feature and target matrix for Phase 3 price forecasting. Constructs a complete, continuous panel bounded by active sourcing relationship timelines.
- **Grain:** One row per `(vendor_material_id, procurement_month)`.
- **Primary Key:** `(vendor_material_id, procurement_month)`.
- **Source Lineage:** `silver.procurement_relationship`, `silver.procurement_clean`, `silver.material`.
- **Key Transformation Rules:**
  - Bounded Timeline: Generated via `generate_series` between `date_trunc('month', COALESCE(approved_from, min_date))` and `date_trunc('month', COALESCE(approved_to, max_date))`.
  - `observation_status`:
    - `OBSERVED`: Active procurement with non-zero expenditure/quantity (108,244 rows).
    - `EXPLICIT_ZERO`: Active relationship with explicit 0 purchase/quantity recorded (66,237 rows).
    - `NO_SOURCE_ROW`: Unobserved month within active contract window (37,967 rows).
  - `target_unit_price_eur`: Populated only for `OBSERVED` months with valid comparable price; `NULL` for `EXPLICIT_ZERO` and `NO_SOURCE_ROW`.
  - `eur_expenditure`: Populated for observed months; `NULL` for `NO_SOURCE_ROW` (never zero).

---

## 4. Known Analytical Limitations & Pending Approvals

1. **EURO Currency Alias Pending:**
   - 188 records retain `pending_spend_local` in local units.
   - Pending confirmation: Formal commercial sign-off confirming `EURO` $\equiv$ `EUR`.
2. **UOM Conversion Pending:**
   - 181 records have unverified UOM conversion factors (e.g. PCS vs PAA).
   - Pending confirmation: Engineering sign-off on standardized conversion multipliers.
3. **Price Reconciliation Outliers:**
   - 199 records remain flagged as `has_price_outlier = TRUE` and are excluded from comparable unit price benchmarks.
   - Pending confirmation: Procurement audit of outlier purchase contracts.
4. **Supplier Performance Weighting:**
   - 14,661 quarterly scorecards contain multiple observation rows.
   - Pending confirmation: Stakeholder approval of delivery-lines weighting vs simple unweighted average.
5. **Commodity Index Prices:**
   - 1,900 monthly index prices are missing from benchmark sources.
   - Guardrail: Preserved as NULL without synthetic linear or polynomial interpolation.
