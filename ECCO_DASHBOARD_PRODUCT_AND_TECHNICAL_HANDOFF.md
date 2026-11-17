# ECCO Procurement Analytics
## Dashboard Product and Technical Handoff

**Status:** Documentation-only handoff  
**Repository:** `rhRohitHalder/ecco_shoes_procurement`  
**Database:** PostgreSQL 18.4, database `ecco_procurement`  
**Evidence basis:** repository inspection, executed notebooks, published reports, read-only database validation, and `FINAL_VALIDATION_REPORT.md`  
**Scope boundary:** This document proposes the dashboard/API/application design. It does not create a React application, modify database objects, alter notebooks or SQL, or commit/push changes.

---

## 1. Executive summary

ECCO Procurement Analytics is a synthetic procurement data platform that has progressed through:

1. source-data audit and procurement-grain reconciliation;
2. Silver source-preserving transformation;
3. Gold business marts and a forecasting panel;
4. forecasting readiness and a first result-artifact pipeline;
5. independent cross-layer validation.

The current platform is suitable for a dashboard proof of concept for historical procurement, spend, data quality, commodity exposure, supplier performance, and forecast-readiness exploration. Silver and Gold database claims are validated. Phase 3 forecast mathematics and CSV identities are partly validated, but the published forecasting narrative is not yet a trustworthy production KPI source.

The first dashboard milestone should therefore be a **read-only historical procurement and data-quality dashboard**, backed by curated Gold marts and explicit evidence labels. Forecast pages should initially be marked **qualified / draft** and expose provenance and limitations rather than presenting forecast accuracy as certified.

### Evidence labels used in the dashboard

| Label | Meaning |
|---|---|
| **Verified live** | Reproduced from the current PostgreSQL database or a read-only database validation script. |
| **Executed artifact** | Produced by an executed notebook or pipeline and structurally inspected. |
| **Artifact mathematics verified** | Derived CSV columns recompute correctly, but this does not prove training provenance. |
| **Reported, not independently verified** | A report claim not reproduced from the database or a canonical artifact. |
| **Proposed** | Product, API, UX, or deployment design not currently implemented. |

---

## 2. Project journey and current status

| Phase | Main artifacts | Current assessment |
|---|---|---|
| Audit / preflight | `PROJECT_CODEBASE_AUDIT.md`, `PROJECT_FILE_INVENTORY.csv` | Repository and source structure documented. |
| Phase 1A | `phase1_*` rule register, mapping, schema, pilot and plan reports | Transformation rules and unresolved approvals documented. |
| Phase 1B | `02_silver_transformation.ipynb`, Silver summary and quality CSV | **Validated.** Source-row preservation, IDs, exception counts, constraints, rerun history and provenance were remediated. |
| Phase 2 | `03_gold_analytics.ipynb`, Gold summary and dictionary | **Validated.** Six Gold models, grains, foreign keys, spend conservation and QA indicators reproduce. |
| Phase 3 Session 1 | `04_price_forecasting.ipynb`, readiness report and eligibility CSV | Readiness, profiling and leakage-safe design documented. The report itself includes superseded or narrative issues identified later. |
| Phase 3 result artifacts | forecast CSVs, pipeline modules and model metrics | Artifact formulas validate, but the published result set is not fully reproducible from committed code and contains incompatible Ridge AR series. |
| Dashboard | This document | **Proposed.** No frontend, API or deployment implementation currently exists. |

---

## 3. Repository and artifact inventory

### 3.1 Source and governance

- `.env`: local connection configuration; credentials must never be exposed to the frontend, logs, reports or API responses.
- `requirements.txt`: Python dependency declaration.
- `load_data/postgres_schema.sql`: public source DDL.
- `load_data/load_postgres.sql`: replace-style loader using `TRUNCATE ... CASCADE`; it is not a transformation script.
- `load_data/Database_loader.sql`: existing bootstrap/load script.
- `data/README.md`, `data/DATA_QUALITY_GUIDE.md`, `data/data_dictionary.csv`: source semantics, quality rules and field definitions.
- Synthetic data and source builders under `data/source/`; these are source-generation assets, not dashboard runtime sources.

### 3.2 Investigation and transformation notebooks

- `data_report/notebooks/ecco_data_report.ipynb`: chronological PostgreSQL investigation and schema/data-quality evidence. Its table qualification was corrected to respect the actual schema.
- `data_report/notebooks/ecco_procurement_data_quality_assessment.ipynb`: database-backed source quality assessment.
- `data_report/notebooks/02_silver_transformation.ipynb`: Silver publication, audit metadata, exception handling and rerun checks.
- `data_report/notebooks/03_gold_analytics.ipynb`: Gold mart creation and validation.
- `data_report/notebooks/04_price_forecasting.ipynb`: Phase 3 readiness, profiling and feature-design notebook.

Notebook outputs are evidence of execution at a point in time. A dashboard must not execute notebooks per request.

### 3.3 Key reports and validation scripts

- `data_report/reports/phase1_silver_transformation_summary.md`
- `data_report/reports/phase1_silver_quality_summary.csv`
- `data_report/reports/phase2_gold_transformation_summary.md`
- `data_report/reports/phase2_independent_audit_report.md`
- `data_report/reports/phase2_gold_data_dictionary.csv`
- `data_report/reports/phase3_forecasting_report.md`
- `data_report/reports/phase3_model_metrics_summary.csv`
- `data_report/reports/phase3_forecast_business_results.csv`
- `data_report/reports/phase3_material_forecast_reliability.csv`
- `data_report/reports/phase3_commodity_enhancement_comparison.csv`
- `data_report/reports/phase3_12month_forward_forecast.csv`
- `data_report/reports/FINAL_VALIDATION_REPORT.md`
- `data_report/audit/validate_db.py`
- `data_report/audit/validate_csv.py`
- `data_report/audit/validate_cross.py`
- `data_report/audit/inspect_notebooks.py`
- `data_report/audit/dump_schema.py`

### 3.4 Forecasting pipeline modules

- `data_report/pipeline/config.py`: time windows, horizons, eligibility and clipping constants.
- `data_report/pipeline/db_io.py`: database reads for Gold inputs.
- `data_report/pipeline/features.py`: origin-indexed price and commodity feature store.
- `data_report/pipeline/models.py`: NumPy closed-form Ridge, SES and baseline forecasters.
- `data_report/pipeline/metrics.py`: MASE, sMAPE and WAPE implementations.
- `data_report/pipeline/run_forecast.py`: result-generation entry point.

The existence of these modules does not by itself prove that the published CSVs were generated by this exact committed pipeline. The final validation report found no committed model-training/CSV-generation path that fully explains the published Phase 3 result set.

### 3.5 Visual assets

The repository includes an ER diagram (`ecco_final_er.drawio.png`) and report/notebook visual outputs. No production chart component library, dashboard route, frontend source tree, API service, or chart-generation contract currently exists. Dashboard visualizations described below are therefore proposed views over verified tables, not existing implemented screens.

---

## 4. PostgreSQL architecture

| Schema | Role | Dashboard access |
|---|---|---|
| `public` | Immutable synthetic source tables | Normally indirect; use only for detailed lineage or source-audit views. |
| `silver` | Cleaned, source-grain records and reference dimensions | Restricted operational/audit access; primary dashboard use should prefer Gold. |
| `gold` | Business marts, reconciled performance and forecast panel | Primary read-only dashboard source. |
| `audit` | Runs, exceptions, duplicate review, price reconciliation and validation history | Read-only quality/governance pages and admin diagnostics. |

### Source scale

- 1,200 materials
- 95 vendors
- 6 plants
- 2 purchasing organizations
- 13 commodities
- 2,910 vendor-material-plant relationships
- 174,638 procurement source rows
- 78,570 raw supplier-performance rows
- 729 FX rows
- 1,053 commodity-month source rows

### Verified source grain

The procurement technical grain is one row per `public.fact_procurement_monthly.procurement_id`. The row represents a source procurement observation associated with a vendor-material-plant relationship and month. `(vendor_material_id, procurement_month)` is an analytical candidate key but is not unique: 157 repeated groups affect 314 source rows. Legitimate source records are retained.

---

## 5. Data lineage and business semantics

### 5.1 Procurement lineage

`public.fact_procurement_monthly`  
→ `silver.procurement_clean` (one source row per `source_procurement_id`)  
→ Gold relationship, vendor and material marts  
→ forecast panel and forecast features.

Canonical vendor mapping comes from the sourcing bridge. Original/reported vendor IDs remain available, and 198 source rows have a reported/canonical mismatch.

### 5.2 Currency

- FX source semantics: `from_currency = EUR` and `units_per_eur` means quote-currency units per EUR.
- Confirmed conversion: `eur_expenditure = order_value_local / units_per_eur`.
- EUR identity rows use `IDENTITY_RATE`.
- Other currencies use a monthly-average proxy and must be labeled `MONTHLY_AVERAGE_PROXY`.
- `EURO` remains `ALIAS_PENDING`; 188 rows are not silently treated as EUR and remain pending local spend.
- The dashboard must show converted EUR spend separately from pending local spend.

### 5.3 UOM and price

- Material base UOMs: 600 `PAA`, 500 `KG`, 100 `SQM`.
- Observed procurement UOMs include `KG`, `PAA`, `PCS`, and `SQM`.
- Only approved/identity-compatible conversions enter comparable quantity and unit-price calculations.
- 181 rows remain pending UOM approval.
- Weighted price is only meaningful where EUR spend and standardized quantity are eligible:

```text
weighted_unit_price_eur
  = eligible EUR expenditure / comparable standardized PO quantity
```

Expenditure and unit price must remain separate measures in every API response and chart.

### 5.4 Gold observation semantics

The forecast panel contains 212,448 bounded relationship-month rows:

- `OBSERVED`: 108,244
- `EXPLICIT_ZERO`: 66,237
- `NO_SOURCE_ROW`: 37,967

`NO_SOURCE_ROW` is not an implicit zero purchase. The dashboard must preserve this distinction.

### 5.5 Supplier performance

Raw quarterly performance contains repeated vendor-plant-quarter observations. Gold reconciles them to 15,228 rows and exposes both simple and delivery-lines-weighted metrics. Publication remains `PROVISIONAL_PENDING_APPROVAL`; performance must not be joined directly to raw procurement without a signed weighting decision.

---

## 6. Verified Silver and Gold status

### 6.1 Silver

The latest successful Silver run is `a46283ee-3219-4b82-a2ac-18cf95799aea`.

| Check | Verified result |
|---|---:|
| Source procurement rows | 174,638 |
| Silver procurement rows | 174,638 |
| Distinct Silver source IDs | 174,638 |
| Source → Silver missing IDs | 0 |
| Silver → source extra IDs | 0 |
| Invalid non-null unit prices | 0 |
| Vendor mismatches | 198 |
| `EURO` aliases pending | 188 |
| Pending UOM rows | 181 |
| Duplicate candidate groups / rows | 157 / 314 |
| Supplier-performance duplicate groups audited | 14,661 |
| Latest audit exception records | 77,913 |

Silver supports source traceability, exception investigation, and drill-through. It should not be exposed as an unrestricted general-purpose API surface.

### 6.2 Gold

| Table | Grain / key | Rows |
|---|---|---:|
| `gold.agg_vendor_material_plant_monthly` | vendor-material-plant-month | 174,481 |
| `gold.agg_vendor_monthly` | canonical-vendor-month | 7,663 |
| `gold.agg_material_monthly` | material-month | 87,611 |
| `gold.agg_commodity_exposure_monthly` | material-commodity-month | 291,600 |
| `gold.dim_vendor_performance_quarterly` | vendor-plant-quarter | 15,228 |
| `gold.panel_forecast_base_monthly` | vendor-material-month | 212,448 |

Confirmed EUR spend is **€232,347,252.96** and reconciles exactly across Silver and the relevant Gold spend marts. 188 EURO transactions remain outside converted EUR spend pending approval.

---

## 7. Forecasting status and limitations

### 7.1 What is supported

- Primary target: `gold.agg_material_monthly.weighted_unit_price_eur`.
- Secondary panel target: `gold.panel_forecast_base_monthly.target_unit_price_eur`.
- History: January 2020 through September 2026, 81 months.
- 1,200 materials profiled.
- Recommended readiness threshold: 36 valid priced months, 1,169 materials.
- Advanced 60-month cohort: 658 materials.
- Price observations: 71,695; unpriced material-months: 15,916.
- Price outliers: 199.
- Feature code uses origin-indexed history and commodity features; the documented design avoids future target values in predictive features.

### 7.2 Governing validation verdict

`FINAL_VALIDATION_REPORT.md` is the governing Phase 1–3 validation record. It reports 324 checks: 266 PASS, 44 FAIL, 12 INFO and 2 WARN.

- Database-level Silver/Gold/forecast-input claims: validated.
- CSV arithmetic and derived-column identities: largely validated.
- Phase 3 report narrative: **not validated**.
- Phase 3 reproducibility: **not validated**.

### 7.3 Required forecast caveats

1. Two incompatible result sets are both labeled `Ridge AR`. The model comparison series and business-results/commodity series disagree for all 1,195 compared materials.
2. The report headline values (including median MASE, sMAPE and evaluated-series count) match neither canonical artifact consistently.
3. The BQ3 peak/trough counts were hard-coded and do not match recomputed values.
4. BQ6 concentration statistics are wrong, although the reported correlations are reproducible.
5. Some commodity evaluated-material counts are wrong.
6. No canonical committed training/export path proves which process generated every published Phase 3 result CSV.
7. `phase3_12month_forward_forecast.csv` is an artifact with a 2026-09 origin and 2026-10 onward forecast horizon; it must not be presented as a current live forecast without an issue timestamp and model approval.
8. Forecast prices can be highly unstable for very low origin prices; users need uncertainty, eligibility and reliability context.

**Dashboard policy:** show forecast artifacts only with a `DRAFT / QUALIFIED` banner until one canonical pipeline is selected, rerun, parity-checked and approved.

---

## 8. Proposed dashboard product

The application should be a read-only decision-support product with global filters:

- month/date range;
- vendor;
- material;
- plant;
- purchasing organization;
- base UOM;
- commodity;
- currency/provenance status;
- quality status;
- forecast evidence status.

Every page should show data freshness, source table, query/model version, and evidence label.

### Page 1 — Executive procurement overview

**Purpose:** portfolio-level spend and procurement activity.  
**KPIs:** EUR spend, eligible spend, pending local spend, transactions, active vendors/materials/plants, priced share.  
**Visuals:** spend trend, vendor/material Pareto, monthly transaction status.  
**Source:** `gold.agg_vendor_monthly`, `gold.agg_material_monthly`, `silver.procurement_clean`.  
**Status:** verified live, subject to date/filter semantics.

### Page 2 — Spend and currency control tower

**Purpose:** explain EUR conversion and unresolved currency exposure.  
**Visuals:** spend by original currency, FX provenance, pending EURO amount/count, monthly converted spend.  
**Source:** Silver procurement, FX reference and audit exceptions.  
**Warning:** never label EURO pending as EUR.

### Page 3 — Vendor performance and sourcing

**Purpose:** compare suppliers and sourcing relationships.  
**Visuals:** vendor spend, active materials/plants, supplier scorecards, performance trend.  
**Source:** `gold.agg_vendor_monthly`, `gold.dim_vendor_performance_quarterly`.  
**Banner:** performance metrics are provisional pending weighting approval.

### Page 4 — Material price intelligence

**Purpose:** monitor material-level unit price and expenditure.  
**Visuals:** weighted price trend, spend trend, min/max price range, UOM and eligibility badges.  
**Source:** `gold.agg_material_monthly`.  
**Rule:** do not interpolate unpriced months as zero.

### Page 5 — Vendor-material-plant price comparison

**Purpose:** retain plant detail and identify sourcing price differences.  
**Visuals:** relationship-month price matrix, plant comparison, supplier spread, transaction drill-through.  
**Source:** `gold.agg_vendor_material_plant_monthly`.  
**Rule:** preserve plant-level detail until plant-wise price differences are assessed.

### Page 6 — Commodity exposure and benchmark context

**Purpose:** relate material composition to benchmark indices.  
**Visuals:** exposure weights, benchmark trend, weighted contribution, missing-index flags.  
**Source:** `gold.agg_commodity_exposure_monthly`.  
**Rule:** missing index prices remain visible as missing, not silently imputed.

### Page 7 — Procurement quality and exceptions

**Purpose:** operational data-quality triage.  
**KPIs:** exception count, EURO aliases, UOM pending, vendor mismatches, price outliers, duplicate candidates, negative GR and GR>PO.  
**Visuals:** exception trend and severity/status breakdown.  
**Source:** `audit.procurement_exceptions`, Silver status columns and latest run metadata.

### Page 8 — Duplicate and reconciliation workbench

**Purpose:** investigate repeated natural-key groups and source-vs-derived price differences.  
**Visuals:** duplicate group details, source rows, reconciliation status, historical run association.  
**Source:** `audit.duplicate_records_review`, `audit.price_reconciliation_review`.  
**Rule:** never aggregate unresolved duplicate records in the UI as if they were resolved.

### Page 9 — Relationship activity and missing months

**Purpose:** distinguish observed, explicit-zero and no-source months.  
**Visuals:** activity calendar, relationship coverage, approval windows, missing-month readiness count.  
**Source:** `gold.panel_forecast_base_monthly`.  
**Rule:** no-source rows are not Silver procurement rows and must not be presented as zero purchases.

### Page 10 — Forecast readiness

**Purpose:** explain which materials are eligible for forecasting.  
**Visuals:** valid-month distribution, UOM distribution, price coverage, volatility cohorts, eligibility tiers.  
**Source:** eligibility/readiness CSVs and Gold material mart.  
**Status:** readiness is supported; forecast accuracy claims remain qualified.

### Page 11 — Forecast results (qualified)

**Purpose:** inspect forecast artifacts with explicit provenance.  
**Visuals:** historical/forecast line, origin marker, forecast horizon, reliability band, model name and artifact timestamp.  
**Source:** forecast CSV artifacts only until a canonical forecast table is approved.  
**Banner:** `DRAFT / QUALIFIED — Phase 3 narrative not independently validated`.

### Page 12 — Governance, lineage and audit

**Purpose:** make trust and limitations visible.  
**Content:** run IDs, source-to-target lineage, validation totals, open approvals, known defects, report versions, database freshness and access policy.  
**Source:** audit tables, validation reports and deployment metadata.

---

## 9. Page-to-database traceability

| Page | Primary source | Key measures | Evidence |
|---|---|---|---|
| Overview | Gold vendor/material marts | spend, counts, transactions | Verified live |
| Currency | Silver procurement + FX | local value, EUR value, FX status | Verified live |
| Vendor performance | Gold vendor mart + performance | spend, delivery, defects, lead time | Verified live / provisional KPI |
| Material price | Gold material mart | spend, comparable quantity, weighted price | Verified live |
| Plant comparison | Gold relationship mart | relationship spend/price/flags | Verified live |
| Commodity | Gold commodity mart | weight, index, contribution | Verified live |
| Quality | Silver + audit | exception categories and counts | Verified live, latest run filter required |
| Duplicate workbench | Audit duplicate/reconciliation tables | groups, source IDs, statuses | Verified live |
| Missing months | Gold forecast panel | observation status, record count | Verified live |
| Readiness | Phase 3 eligibility/readiness artifacts | valid months, tiers, volatility | Executed artifact / verified calculations |
| Forecast results | Phase 3 forecast CSVs | forecast price and model metrics | Qualified artifact only |
| Governance | Audit + validation reports | run IDs, validation status | Verified report/database evidence |

---

## 10. Proposed FastAPI contract

The API is not implemented. The following is the recommended read-only contract.

### Conventions

- `GET` only for dashboard data.
- Strict parameter validation and bounded date ranges.
- Pagination for detail endpoints.
- Responses include `data`, `meta`, `source`, `evidence_status`, `as_of`, and `warnings`.
- No credentials, connection strings or unrestricted SQL in responses.
- Server-side query allowlists; no client-supplied table names.

### Endpoint groups

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/metadata` | Dataset freshness, run IDs, supported filters, evidence status. |
| `GET /api/v1/overview` | Portfolio KPIs and trend series. |
| `GET /api/v1/spend` | Spend by month/vendor/material/currency/provenance. |
| `GET /api/v1/vendors` | Vendor ranking, spend and activity. |
| `GET /api/v1/vendors/{vendor_id}/performance` | Quarterly supplier scorecard, with provisional warning. |
| `GET /api/v1/materials` | Material search and summary. |
| `GET /api/v1/materials/{material_id}/prices` | Material price/spend history. |
| `GET /api/v1/relationships` | Vendor-material-plant relationship summaries. |
| `GET /api/v1/commodities` | Commodity exposure and benchmark series. |
| `GET /api/v1/quality/summary` | Latest-run exception counts. |
| `GET /api/v1/quality/exceptions` | Paginated exception details. |
| `GET /api/v1/quality/duplicates/{group_id}` | Duplicate investigation details/history. |
| `GET /api/v1/panel/activity` | Observed/explicit-zero/no-source activity. |
| `GET /api/v1/forecast/readiness` | Eligibility and reliability metadata. |
| `GET /api/v1/forecast/materials/{material_id}` | Qualified forecast artifact for one material. |
| `GET /api/v1/governance/lineage` | Table/column lineage and evidence labels. |

### API response example

```json
{
  "data": [],
  "meta": {
    "filters": {},
    "row_count": 0,
    "as_of": "2026-11-17T00:00:00Z"
  },
  "source": ["gold.agg_material_monthly"],
  "evidence_status": "VERIFIED_LIVE",
  "warnings": []
}
```

Forecast responses should additionally include `model_name`, `model_artifact_version`, `origin_month`, `horizon_end`, `training_window`, `reliability_status`, and `forecast_disclaimer`.

---

## 11. Proposed frontend architecture

### Stack

- Next.js with React and TypeScript.
- Tailwind CSS for layout and design tokens.
- Recharts (or an equivalent maintained chart library) for time series, bars, scatterplots and heatmaps.
- TanStack Query for API caching, loading/error states and refetch control.
- Zod or equivalent runtime validation for API payloads.

### Suggested structure

```text
app/
  (dashboard)/
    overview/
    spend/
    vendors/
    materials/
    commodities/
    quality/
    forecasts/
    governance/
components/
  charts/
  filters/
  kpi/
  tables/
  evidence/
lib/
  api-client.ts
  schemas.ts
  formatters.ts
  permissions.ts
```

### UX requirements

- Persistent filter bar and URL-shareable filter state.
- Evidence badge on every page and forecast card.
- Clear `NULL`, `NO_SOURCE_ROW`, `PENDING`, and `PROVISIONAL` rendering.
- Drill-through from KPI → aggregation row → source procurement IDs where authorized.
- Export only filtered, bounded result sets; exports must include source and as-of metadata.
- Do not use client-side aggregation for financial totals where server-side Gold measures exist.

---

## 12. Proposed deployment architecture

```text
Browser
  -> CDN / HTTPS
  -> Next.js application
  -> FastAPI service
  -> read-only PostgreSQL role
       -> public / silver / gold / audit
```

Recommended controls:

- dedicated read-only database role;
- private database network placement;
- secret manager for connection credentials;
- API rate limits and structured audit logging;
- query timeouts and bounded result sizes;
- database views or stored query modules rather than arbitrary SQL;
- CI checks for TypeScript, API schemas, SQL query plans and evidence metadata;
- no notebook execution in request handlers;
- separate batch job for approved Gold/forecast refreshes.

---

## 13. Open decisions and implementation gates

| Decision | Why it matters | Current status |
|---|---|---|
| Approve `EURO` alias semantics | Determines whether 188 local rows can enter EUR spend | Pending business approval |
| Approve UOM conversions | Determines comparability and price eligibility | 181 rows pending |
| Resolve 199 price outliers | Determines source-vs-derived price treatment | Investigate; do not overwrite source |
| Define duplicate reconciliation | Determines relationship-month aggregation policy | 157 groups retained and flagged |
| Approve supplier weighting | Determines published performance KPI | Provisional |
| Choose canonical Ridge AR result set | Required before forecast accuracy claims | Blocking |
| Regenerate forecast artifacts from one pipeline | Required for reproducibility | Blocking |
| Decide current forecast issue date | Prevents stale forward results being shown as current | Required |
| Define dashboard access roles | Controls source-row and exception visibility | Required |
| Decide refresh cadence/SLA | Controls freshness badge and operational ownership | Required |

---

## 14. Recommended delivery sequence

### Milestone 1 — Verified historical dashboard

Implement Overview, Spend/Currency, Material Price, Vendor, Plant Comparison, Commodity and Quality pages using Gold/Silver/audit read-only queries. Add evidence labels, freshness metadata, filter contracts and source drill-through.

### Milestone 2 — Governance and investigation

Implement duplicate/reconciliation workbench, missing-month activity page, run history, lineage and approval queues. Keep all unresolved records visible and avoid silent transformations.

### Milestone 3 — Forecast qualification

First reconcile the two Ridge AR series, correct report claims, derive BQ3/BQ6 metrics from data, persist model/version/origin metadata, and regenerate artifacts from a single committed pipeline. Then expose forecasts with reliability and uncertainty fields.

### Milestone 4 — Production hardening

Add authentication/authorization, read replicas or workload isolation, observability, caching, contract tests, data freshness alerts and approved refresh orchestration.

---

## 15. Final handoff verdict

The repository and PostgreSQL platform provide a strong foundation for a read-only procurement analytics dashboard. The source-preserving Silver layer and six-table Gold layer are validated, financially conserved and traceable. The dashboard should start with verified historical and quality use cases.

Forecasting should not yet be marketed as production-certified. The available Phase 3 artifacts contain useful readiness, feature and scenario evidence, but the governing validation report identifies material inconsistencies in model result sets and narrative claims. Treat the forecast pages as qualified exploratory views until the canonical pipeline and result lineage are corrected.

**First recommended dashboard milestone:** deliver a read-only Next.js/FastAPI slice for Pages 1, 2, 4 and 7 (overview, currency, material price and data quality), using verified Gold/Silver/audit sources and evidence metadata throughout.
