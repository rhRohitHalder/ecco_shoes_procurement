# ECCO Procurement Analytics — Project Codebase Audit

**Audit mode:** Read-only inspection  
**Repository:** `rhRohitHalder/ecco_shoes_procurement`  
**Local root:** `C:\Users\Rohit Halder\projects\INDIUM_INTERNSHIP`  
**Audit date:** 2026-11-16  
**Evidence labels:** **Verified** = directly observed; **Inferred** = interpretation of observed implementation; **Unverified** = unavailable evidence; **Pending Confirmation** = business decision required.

## 1. Executive Summary

**Verified:** The repository is a synthetic ECCO-style procurement analytics package, not an application or production integration. It contains 11 source CSV assets, a reproducible Python generator, PostgreSQL DDL/load scripts, two PostgreSQL-backed notebooks, generated quality/readiness reports, dependency metadata, and ER diagrams.

**Verified:** A local PostgreSQL 18.4 database named `ecco_procurement` was reachable using the existing environment-variable configuration. Read-only inspection found one user schema (`public`), 12 base tables, no user views, no materialized views, and no user-defined functions. Database row counts match the documented/generated counts.

**Verified:** The current database is a single-layer operational analytical store. There are no explicit staging, Bronze, Silver, Gold, audit-log, transformation-run, or curated exception schemas/tables. The load scripts replace all project tables with `TRUNCATE ... CASCADE` followed by `\copy`.

**Verified:** The strongest existing work is discovery, descriptive EDA, relationship validation, and issue documentation. No permanent transformation pipeline, forecast model, API, dashboard, or frontend was found.

**Verified:** Procurement data is intentionally imperfect. Key findings include 193 missing local order values, 175 missing PO quantities, 10,036 raw GR>PO candidates, 186 negative GR rows, 188 invalid `EURO` currency aliases/missing direct FX matches, 181 UOM mismatches, 198 reported/canonical vendor mismatches, 314 duplicate-key excess rows across 157 groups, 199 price-reconciliation outliers, and 61,229 structural missing vendor-material-month observations.

**Conclusion:** The project is ready for controlled Phase 1 design and curated-layer implementation, but not for unqualified comparable unit-price analysis, FX-normalized analysis, supplier-performance joins, causal commodity analysis, or forecasting. Business rules must be approved before any source values are repaired or excluded.

## 2. Project Overview

The project models procurement at an intended `vendor_material_id × month` aggregate, with material, vendor, plant, purchasing organization, commodity exposure, monthly commodity history, monthly EUR FX, and quarterly vendor performance context.

The data package is explicitly synthetic:

- Historical range: 2020-01 through 2026-09, 81 months.
- 1,200 materials/SKUs.
- 95 vendors.
- 6 plants and 2 purchasing organizations.
- 13 commodity indices.
- 2,910 vendor-material-plant relationships.
- 174,638 procurement fact rows.
- 78,570 quarterly performance rows.
- 2,054 injected issue annotations.

The source documentation states that procurement is not a PO-line ledger and that synthetic values must not be interpreted as authentic ECCO transactions or evidence of real-world model accuracy.

## 3. Complete Repository Folder Tree

Generated environments and caches are intentionally grouped rather than expanded.

```text
INDIUM_INTERNSHIP/
├── .env
├── .git/
├── .gitignore
├── .vscode/
│   └── settings.json
├── .ecco/                       [ignored Python virtual environment]
├── .venv/                       [ignored Python virtual environment]
├── __pycache__/                 [ignored Python cache]
├── data/
│   ├── DATA_QUALITY_GUIDE.md
│   ├── README.md
│   ├── data_dictionary.csv
│   ├── data_quality_issue_register.csv
│   ├── dim_commodity.csv
│   ├── dim_material.csv
│   ├── dim_plant.csv
│   ├── dim_purchasing_org.csv
│   ├── dim_vendor.csv
│   ├── er_diagram.mmd
│   ├── fact_commodity_monthly.csv
│   ├── fact_fx_monthly.csv
│   ├── fact_procurement_monthly.csv
│   ├── fact_vendor_performance_quarterly.csv
│   ├── manifest.json
│   └── source/
│       └── build_ecco_dataset.py
├── data_report/
│   ├── notebooks/
│   │   ├── ecco_data_report.ipynb
│   │   └── ecco_procurement_data_quality_assessment.ipynb
│   └── reports/
│       ├── DATA_QUALITY_REPORT_GUIDE.md
│       ├── analytical_readiness.csv
│       ├── column_profile.csv
│       ├── data_quality_report.csv
│       ├── data_quality_scorecard.csv
│       ├── dataset_inventory.csv
│       ├── existing_issue_register_comparison.csv
│       ├── in_notebook_before_after_validation.csv
│       ├── in_notebook_quality_summary.csv
│       ├── in_notebook_remediation_recommendations.csv
│       ├── issue_register.csv
│       ├── key_grain_validation.csv
│       ├── relationship_validation.csv
│       ├── report_metadata.json
│       ├── source_manifest.csv
│       └── transformation_specification.csv
├── ecco_final_er.drawio.png
├── load_data/
│   ├── Database_loader.sql
│   ├── load_postgres.sql
│   └── postgres_schema.sql
├── requirements.txt
├── PROJECT_CODEBASE_AUDIT.md
└── PROJECT_FILE_INVENTORY.csv
```

**Working-tree note — Verified:** Git status before this audit showed the tracked root-level `data_report/ecco_data_report.ipynb` deleted, while `data_report/notebooks/` and `data_report/reports/` were untracked. The current notebook under `data_report/notebooks/` is 74 cells and approximately 1.63 MB; the deleted `HEAD` version was a separate 3-cell, approximately 14 KB notebook. This is a repository-state discrepancy, not silently resolved by this audit.

## 4. File-by-File Inventory

The companion [PROJECT_FILE_INVENTORY.csv](PROJECT_FILE_INVENTORY.csv) contains one row per relevant file with path, type, purpose, dependencies, status, and observations.

Important groups:

1. **Source data:** dimensions, bridges, facts, data dictionary, manifest, and issue register under `data/`.
2. **Generation:** [build_ecco_dataset.py](data/source/build_ecco_dataset.py) creates a separate synthetic package directory and ZIP; it does not load the repository CSVs into PostgreSQL.
3. **Database:** [postgres_schema.sql](load_data/postgres_schema.sql), [load_postgres.sql](load_data/load_postgres.sql), and [Database_loader.sql](load_data/Database_loader.sql).
4. **Investigation:** [ecco_data_report.ipynb](data_report/notebooks/ecco_data_report.ipynb) and [ecco_procurement_data_quality_assessment.ipynb](data_report/notebooks/ecco_procurement_data_quality_assessment.ipynb).
5. **Generated evidence:** CSV/JSON reports under `data_report/reports/`.
6. **Configuration:** [.env](.env) exists locally and is ignored; its values were not reported.

No Excel files, JSON business datasets beyond the manifest, application/API files, Docker/deployment files, test suite, or separate Python modules were found.

## 5. Current Project Architecture

### Implemented

- Synthetic data generation with deterministic seed `27102026`.
- CSV source package with documented grains, relationships, and injected DQ conditions.
- PostgreSQL schema in `public`.
- Replace-load process from CSV to PostgreSQL.
- Foreign keys for dimensions/bridges and selected facts.
- Indexes on procurement month/material/vendor-material and performance vendor-quarter.
- Database discovery and descriptive profiling notebooks.
- Generated quality findings, transformation specification, readiness report, and remediation recommendations.
- ER diagram in Mermaid and PNG form.

### Partially implemented

- A proposed curated transformation specification exists, but no SQL/Python implementation of Silver/Gold layers exists.
- Notebook code constructs integrated analytical queries with flags, but does not persist a curated table or view.
- Quality reporting is reproducible in concept, but the current notebook artifacts contain saved outputs while notebook summaries report cells as not executed in the current editor state.
- PostgreSQL constraints enforce structural referential integrity but do not encode most business rules such as valid currencies, UOM equivalence, active periods, duplicate natural grain, or FX completeness.

### Planned or not implemented

- Explicit Bronze/Silver/Gold layers.
- Permanent transformation orchestration and run metadata.
- Reconciliation and exception workflow.
- Forecasting, backtesting, feature store, model registry, API, dashboard, or frontend.
- Production source ingestion and external commodity/FX connectivity.

### End-to-end current flow

```text
build_ecco_dataset.py
        ↓
synthetic CSV package in data/
        ↓
postgres_schema.sql or Database_loader.sql
        ↓
public PostgreSQL tables
        ↓
data_report notebooks
        ↓
generated CSV quality/readiness reports
```

The flow stops at investigation/reporting. It does not continue to persisted Silver or Gold outputs.

## 6. Notebook and EDA Audit

### 6.1 Chronological investigation notebook

[ecco_data_report.ipynb](data_report/notebooks/ecco_data_report.ipynb) is a 74-cell chronological PostgreSQL investigation. Saved outputs show connection to `ecco_procurement` using PostgreSQL 18.4, discovery of 12 public tables, schema metadata, table-by-table inspection, relationship checks, cross-table validation, integrated analytical SQL, and readiness assessment.

Main stages:

1. **Business framing:** explains procurement-price analysis, commodity movements, FX, contracts, UOM, receipts, and supplier performance.
2. **Database discovery:** discovers schemas, tables, exact row counts, columns, constraints, indexes, and ER documentation.
3. **Independent table research:** profiles material, vendor, plant, purchasing organization, commodity, sourcing bridge, commodity exposure, procurement, FX, and performance.
4. **Finding consolidation:** builds an investigation log with evidence, severity, actions, and mentor clarifications.
5. **Relationship validation:** tests material joins, sourcing joins, commodity mappings, FX coverage, and performance joins.
6. **Cross-table validation:** tests UOM, currency, active periods, price reconciliation, and structural missing months.
7. **Integrated analytical view:** joins source data without overwriting fields and adds quality flags; it is not persisted.
8. **Readiness:** classifies future analytical use cases and explicitly avoids forecasting or causal claims.

Important notebook evidence:

- All 174,638 procurement rows matched material and sourcing keys.
- 198 procurement rows disagreed with the canonical bridge vendor.
- Commodity exposure covered all 1,200 materials; weights summed correctly in the report.
- Commodity history had 1,900 mapping-history rows with missing prices because six commodity-month prices repeat across 3,600 mappings.
- Direct FX matching missed 188 rows, all associated with the `EURO` alias; recovery via bridge contract currency was observed but is not yet a formally approved rule.
- The performance relationship query produced 1,094,633 joined rows from 174,638 procurement rows because performance has repeated vendor-plant-quarter observations. This is a material fan-out risk.
- Cross-table checks found 181 UOM mismatches, 198 vendor mismatches, 2,678 rows outside material validity dates, 188 missing direct FX rows, 199 price-reconciliation outliers, and 61,229 missing expected panel months.

### 6.2 Data quality assessment notebook

[ecco_procurement_data_quality_assessment.ipynb](data_report/notebooks/ecco_procurement_data_quality_assessment.ipynb) is a 30-cell database-backed descriptive quality report. It dynamically discovers public tables, reads exact counts, profiles columns and missing values, checks primary-key uniqueness, validates discovered foreign keys, calculates descriptive summaries and date coverage, and records limitations.

It reports:

- 12 discovered public tables.
- Missing values in seven columns across four tables.
- Primary-key checks pass for populated tables.
- Declared foreign-key checks pass against live data.
- It does not implement business-grain validation, source correction, forecasting, or business recommendations.

### 6.3 Notebook status and portability observations

**Verified:** Current notebook summaries state that cells are not executed in the current notebook session even though saved outputs are embedded. Treat embedded outputs and generated CSV reports as historical evidence from prior executions, not a guarantee that a fresh run currently succeeds.

**Verified:** The notebooks load `.env` and use SQLAlchemy/psycopg2. The database report guide documents required keys without exposing values.

**Potential issue:** [ecco_procurement_data_quality_assessment.ipynb](data_report/notebooks/ecco_procurement_data_quality_assessment.ipynb) uses broad `except Exception` in discovery/profiling paths and retains errors as report state; this is acceptable for an audit notebook but should be tightened before production pipeline use.

## 7. Dataset and Data Asset Inventory

| Asset | Rows | Columns | Grain / purpose | Date coverage |
|---|---:|---:|---|---|
| `dim_purchasing_org.csv` | 2 | 2 | One purchasing organization | Not temporal |
| `dim_plant.csv` | 6 | 5 | One production plant | Not temporal |
| `dim_vendor.csv` | 95 | 8 | One vendor | Not temporal |
| `dim_material.csv` | 1,200 | 9 | One full SKU/material | `active_from` 2020-01 to 2020-08; `active_to` mostly NULL |
| `dim_commodity.csv` | 13 | 5 | One commodity index | Not temporal |
| `bridge_vendor_material.csv` | 2,910 | 12 | One approved vendor-SKU-plant relationship | `approved_from` 2020-01 to 2021-03; optional end date |
| `bridge_material_commodity.csv` | 3,600 | 6 | One material-commodity exposure | `valid_from` 2020-01 |
| `fact_commodity_monthly.csv` | 1,053 | 7 | One commodity-month | 2020-01 to 2026-09 |
| `fact_fx_monthly.csv` | 729 | 6 | One EUR-to-currency-month rate | 2020-01 to 2026-09 |
| `fact_procurement_monthly.csv` | 174,638 | 21 | Intended vendor-material-plant-month aggregate | 2020-01 to 2026-09 |
| `fact_vendor_performance_quarterly.csv` | 78,570 | 11 | Relationship-level vendor-plant-quarter observations | 2020-Q1 to 2026-Q3 |
| `data_quality_issue_register.csv` | 2,054 | 7 | One injected issue annotation | No independent time grain |

### Dataset relationships and discrepancies

**Verified:** CSV counts match `manifest.json`, generated dataset inventory, and live PostgreSQL row counts.

**Verified:** All source CSVs have zero exact duplicate rows according to the generated inventory, but procurement has 157 duplicate natural-key groups with 314 rows and performance has 14,661 repeated candidate vendor-plant-quarter groups with 78,003 duplicate-key rows.

**Verified:** `fact_procurement_monthly.vendor_id` intentionally includes invalid/mismatched values. `vendor_material_id → bridge_vendor_material.vendor_id` is the canonical sourcing path for analysis.

**Verified:** Local CSV quality reports and PostgreSQL notebook outputs are consistent on core counts, but independent quality checks aggregate issue annotations differently. The source issue register has row-level injected records; the report findings contain one consolidated finding per rule. The comparison report explicitly says they supplement rather than replace each other.

## 8. PostgreSQL Schema and Table Inventory

### Live database scope

**Verified:** Connected to database `ecco_procurement`, PostgreSQL 18.4, schema `public`. The inspection used read-only access and exact `COUNT(*)` queries.

**Verified:** 12 base tables; no user views; no materialized views; no user-defined functions/procedures discovered.

### Tables

| Table | Rows | Columns | Grain / key |
|---|---:|---:|---|
| `dim_purchasing_org` | 2 | 2 | `purch_org_id` |
| `dim_plant` | 6 | 5 | `plant_id`; FK to purchasing org |
| `dim_vendor` | 95 | 8 | `vendor_id` |
| `dim_material` | 1,200 | 9 | `material_id` |
| `dim_commodity` | 13 | 5 | `commodity_id` |
| `bridge_vendor_material` | 2,910 | 12 | `vendor_material_id` |
| `bridge_material_commodity` | 3,600 | 6 | `(material_id, commodity_id)` |
| `fact_commodity_monthly` | 1,053 | 7 | `(commodity_id, month)` |
| `fact_fx_monthly` | 729 | 6 | `(month, from_currency, to_currency)` |
| `fact_procurement_monthly` | 174,638 | 21 | technical PK `procurement_id`; analytical candidate `(vendor_material_id, month)` |
| `fact_vendor_performance_quarterly` | 78,570 | 11 | technical PK `performance_id`; candidate `(vendor_id, plant_id, quarter_start)` repeats |
| `data_quality_issue_register` | 2,054 | 7 | `issue_id` |

### Implemented constraints and indexes

**Verified:** Primary keys exist on all listed tables. Foreign keys exist for plant-to-purchasing organization, sourcing bridge to material/vendor/plant, material-commodity bridge, commodity fact, procurement material/bridge/plant/purchasing organization, and performance vendor/plant.

**Verified:** `fact_procurement_monthly.vendor_id` deliberately has no FK, preserving invalid source vendor values for DQ07 auditing. The schema comments identify `vendor_material_id` as the canonical relationship.

**Verified:** Indexes include procurement month, procurement material, procurement vendor-material, and performance vendor/quarter, in addition to PostgreSQL-created primary-key indexes.

**Gap:** There are no database-level checks for ISO currencies, valid UOM aliases, nonnegative/valid metric ranges, active-date validity, duplicate analytical grain, exposure-weight sums, quarterly uniqueness, or data lineage/run IDs.

## 9. Existing SQL Transformation Audit

### `postgres_schema.sql`

- Creates all 12 project tables with `CREATE TABLE IF NOT EXISTS`.
- Creates primary keys and selected foreign keys.
- Creates four non-PK analytical indexes.
- Does not create staging, Silver, Gold, audit, logging, or exception-resolution objects.
- Does not transform or clean data.

### `load_postgres.sql`

- Starts a transaction.
- Truncates all project tables with `CASCADE`.
- Loads CSVs using client-side `\copy` in dependency order.
- Commits.
- It is a destructive replace-load for the project tables, although it is not a schema-destructive operation.
- It assumes execution from the repository root.

### `Database_loader.sql`

- Creates `ecco_procurement` if absent using `\gexec`.
- Connects to it.
- Repeats schema DDL and replace-load logic.
- Prints row counts after loading.
- It duplicates most of `postgres_schema.sql` and `load_postgres.sql`; divergence risk exists.

### Existing transformation rules

Documented/proposed rules include:

- Retain NULL order values and investigate before aggregation.
- Derive price only for positive PO quantity.
- Preserve and classify negative GR; do not cap automatically.
- Use `vendor_material_id` for canonical vendor identity.
- Reconcile duplicate natural keys before aggregation.
- Resolve currency aliases and use `units_per_eur` in the documented direction.
- Preserve structural missing months as missingness, not zero spend/price.
- Validate commodity weights and lags.
- Weight supplier KPIs by `delivery_lines` only after denominator validation.

**Verified:** These rules are in documentation/reports and notebook SQL. No permanent transformation SQL implementing them was found.

## 10. Python Code and Dependency Audit

### Generator

[build_ecco_dataset.py](data/source/build_ecco_dataset.py) uses standard-library modules (`csv`, `random`, `math`, `calendar`, `zipfile`, `os`, `json`, `shutil`, `pathlib`, `collections`, `datetime`). It:

- Defines synthetic plants, organizations, vendors, materials, commodities, sourcing relationships, mappings, commodity histories, FX rates, procurement rows, performance rows, and issue annotations.
- Intentionally injects DQ01-DQ12 patterns.
- Writes a separate output directory and ZIP.
- Uses a deterministic random seed.

It is a generator, not a reusable ingestion library. It contains hardcoded synthetic business values and output paths relative to the working directory.

### Notebook code

The notebooks contain duplicated connection, profiling, quoting, SQL, plotting, and validation helpers. They rely on:

- `pandas`, `numpy`
- `matplotlib`, `seaborn`
- `SQLAlchemy`, `psycopg2-binary`
- `python-dotenv`
- Jupyter/IPython

### Configuration and maintainability observations

- `requirements.txt` has no version pins, reducing reproducibility.
- `.env` is ignored correctly; values were not exposed.
- There is no application logging framework or pipeline run manifest in Python.
- SQL and Python validation logic is embedded in notebooks rather than tested modules.
- Table names and business rules are repeated across notebook cells.
- The current source generator has no command-line argument interface.
- No automated unit/integration tests were found.

## 11. Consolidated Data Quality Findings

The following are independently computed findings from the generated reports and notebook outputs. They are not claims that source data has been fixed.

| ID | Finding | Affected rows/groups | Severity | Existing treatment |
|---|---|---:|---|---|
| DQ01 | Missing `order_value_local` | 193 rows | High | Retain NULL; investigate |
| DQ02 | Missing/non-positive PO quantity population | 66,617 rows in consolidated rule; 175 explicit NULLs | High | Separate zero/missing/reversal states |
| DQ03 | `gr_qty > po_qty` raw numeric candidates | 10,036 rows | High | Investigate timing, UOM, reversal context |
| DQ04 | Negative goods receipt | 186 rows | Medium | Preserve sign and classify |
| DQ05 | Price spike / reconciliation candidates | 199 computed price-reconciliation outliers; 199 injected annotations | Medium | Review against contract/currency/UOM |
| DQ06 / FX-MISSING | Invalid `EURO` order currency and missing direct FX | 188 rows | High | Pending alias approval; no guessing |
| DQ07 | Reported vendor differs from bridge vendor | 198 rows | High | Use bridge canonical vendor and flag |
| DQ08 | Duplicate procurement natural key | 314 excess/affected rows across 157 groups; independent report uses 314 affected rows | High | Reconcile before summing |
| DQ09 | PO UOM differs from material base UOM | 181 rows | High | Require approved conversion map |
| DQ10 | Missing expected vendor-material-month panel rows | 61,229 of 235,710 expected rows | Medium | Keep missingness explicit |
| DQ11 / ZERO-FLAG | Zero PO quantity with positive spend and flag disagreement | 205 rows | Medium | Investigate document type; recompute curated flag only |
| DQ12 | Positive PO with zero same-month GR | 197 source annotations; notebook derives comparable candidates | Medium | Investigate delayed receipt semantics |

Additional cross-table observations:

- 2,678 procurement rows fall outside the material active period.
- 6 commodity-month records have NULL `index_price`.
- Commodity exposure mapping covers all 1,200 materials and reported weight sums pass.
- Declared FK relationships have no orphan rows in the inspected database.
- Performance candidate grain is not unique, creating six-to-many fan-out in the notebook join example.

## 12. Existing Data Transformation Status

| Capability | Status | Evidence |
|---|---|---|
| Raw/source layer | Implemented | CSV package and loaded PostgreSQL tables |
| Schema DDL | Implemented | `postgres_schema.sql` |
| Replace-load | Implemented | `load_postgres.sql`, `Database_loader.sql` |
| Basic referential integrity | Implemented | PostgreSQL FKs and passing live checks |
| Source profiling | Implemented | Two notebooks and generated reports |
| Quality issue annotation | Implemented | Source register with 2,054 injected annotations |
| Curated exception flags | Partially implemented | Notebook queries and proposed reports only |
| Currency normalization | Partially implemented / blocked | Cached EUR values exist; 188 direct FX gaps/aliases |
| UOM normalization | Not implemented | 181 mismatches; no approved conversion table |
| Duplicate reconciliation | Not implemented | Candidate natural-key duplicates remain |
| Silver layer | Not implemented | No schema/table/view |
| Gold layer | Not implemented | No schema/table/view |
| Validation persistence | Not implemented | CSV reports only; no database run/audit tables |
| Analytics application | Not implemented | No API/frontend/dashboard |
| Forecasting | Not implemented | No model or backtesting code |

## 13. Unresolved Business Assumptions

All items below are **Pending Confirmation** unless explicitly stated otherwise:

1. Whether `EURO` is an approved alias for `EUR`.
2. Whether monthly average FX is acceptable when transaction-date FX is unavailable.
3. Whether existing cached `order_value_eur` is authoritative, recalculated, or only a comparison field.
4. Whether `vendor_material_id` is the formal natural relationship key.
5. How duplicate vendor-material-month aggregates should be reconciled.
6. Whether missing months mean no activity, missing extract data, inactive relationship, or excluded observation.
7. Approved UOM aliases and material-specific conversion factors for PAA, PCS, KG, SQM, and other observed values.
8. Treatment of negative goods receipts and receipt quantities greater than PO quantity.
9. Whether contract dates define analytical eligibility.
10. Whether material active dates may be violated by historical postings.
11. Whether commodity exposure weights are business-approved or analytical proxies.
12. Whether commodity publication gaps should be excluded, imputed, or flagged.
13. Whether supplier performance is intended to be vendor-plant-quarter or relationship-level and how to aggregate repeated rows.
14. Whether performance should be lagged before use in forecasting to avoid leakage.
15. Which price field is authoritative: local unit price, order value divided by PO quantity, contract quote, or another source field.
16. Whether supplier preferred currency, contract currency, or order currency is authoritative when they differ.
17. Whether plants remain separate dimensions or are rolled to purchasing organization/region.

## 14. Technical Risks and Limitations

1. **Synthetic-data risk:** all values and findings describe a demonstration dataset.
2. **Layering risk:** no persisted Bronze/Silver/Gold separation means source and analytical semantics are easy to mix.
3. **Replace-load risk:** loaders truncate all project tables and should not be run against shared/unrelated tables.
4. **Notebook production risk:** core logic is embedded in notebooks without automated tests.
5. **Dependency reproducibility risk:** requirements are unpinned.
6. **Duplicate logic risk:** two database loader paths duplicate DDL/load behavior.
7. **Grain risk:** technical primary keys do not guarantee analytical grain.
8. **Fan-out risk:** performance joins can multiply procurement rows and inflate spend.
9. **Currency risk:** `EURO` is syntactically non-standard and direct FX lookup fails.
10. **Unit risk:** UOM mismatches make unit-price comparisons unsafe.
11. **Temporal leakage risk:** future commodity, performance, contract, or FX information must not enter historical forecasting features.
12. **Missingness risk:** absent months and explicit zero rows have different meanings.
13. **Source lineage risk:** no ingestion batch, source file hash, run ID, or row-level transformation lineage is stored in PostgreSQL.
14. **Unverified live-state risk:** database inspection reflects the available local instance at audit time, not an independently managed production environment.

## 15. Transformation Readiness Assessment

| Area | Classification | Evidence |
|---|---|---|
| Source data availability | Ready | 11 CSV assets and live PostgreSQL tables available |
| Master-data quality | Partially Ready | Keys and FKs pass; business validity and UOM semantics remain |
| Procurement fact readiness | Partially Ready | Data is loaded and documented, but duplicate grain, NULLs, DQ flags remain |
| Currency normalization | Blocked | 188 invalid/alias rows lack direct FX match |
| UOM normalization | Blocked | 181 PO UOM mismatches; no approved conversion table |
| Vendor-material relationship | Partially Ready | 2,910 unique bridge relationships and full join coverage; 198 vendor mismatches |
| Commodity mapping | Partially Ready | All materials mapped and weights pass; mappings/lags are assumptions |
| Supplier performance | Blocked for direct join | Repeated vendor-plant-quarter observations cause fan-out |
| Database architecture | Partially Ready | Public relational schema exists; no layered/observability architecture |
| SQL/Python reuse | Ready with refactoring | Strong notebook queries and generator/report logic exist |
| Lineage and audit readiness | Blocked | No persisted transformation runs, exceptions, or lineage |
| PostgreSQL persistence | Partially Ready | Raw tables persist; curated layers do not |
| Spend trend analysis | Conditionally Ready | Use EUR values with source-quality exclusions/flags |
| Comparable price analysis | Blocked | Requires UOM, currency, duplicate, and outlier decisions |
| Forecasting | Not yet ready | Sparse panel and leakage/business-rule decisions unresolved |

## 16. Recommended Phase 1 Implementation Plan

1. **Freeze source evidence:** preserve the existing CSVs, manifest, hashes, issue register, and loaded raw tables as a versioned raw layer.
2. **Define transformation rule register:** convert the proposed specification into approved rules with owner, status, tolerance, and effective date.
3. **Create layered PostgreSQL schemas:** at minimum `raw`, `silver`, `gold`, and `audit`; do not repurpose `public` raw tables without an explicit migration plan.
4. **Create a run/control framework:** batch ID, source file hash, load timestamp, row counts, rejected counts, and rule version.
5. **Build Silver dimensions/bridges:** typed, standardized, canonical keys, validity flags, and source lineage.
6. **Build Silver procurement:** preserve raw fields; add canonical vendor, derived quantity state, UOM match, currency alias, FX match, contract validity, duplicate-group, and missing-month flags.
7. **Implement exception handling:** no silent imputation; retain unresolved source values and route exceptions to an auditable issue table.
8. **Resolve duplicate natural grain:** define an explicit aggregation/reconciliation rule before producing spend totals.
9. **Implement FX normalization:** approve aliases and direction; create `eur_value_derived`, `fx_rate_used`, `fx_status`, and reconciliation-to-cached-value fields.
10. **Implement UOM normalization:** obtain approved conversion factors and separate comparable from non-comparable price populations.
11. **Aggregate performance safely:** first produce one vendor-plant-quarter row using validated denominators and weights, then apply lag rules.
12. **Create Gold analytical marts:** spend, price, sourcing, commodity exposure, supplier performance, and quality marts with documented grains.
13. **Validate and reconcile:** compare raw-to-Silver-to-Gold row counts, spend totals, key coverage, exception counts, and duplicate handling.
14. **Only then begin Phase 2 analytics and Phase 3 forecasting.**

## 17. Proposed Silver and Gold Table Design

### Silver

- `silver.dim_purchasing_org`
- `silver.dim_plant`
- `silver.dim_vendor`
- `silver.dim_material`
- `silver.dim_commodity`
- `silver.bridge_vendor_material`
- `silver.bridge_material_commodity`
- `silver.fact_fx_monthly`
- `silver.fact_commodity_monthly`
- `silver.fact_procurement_monthly`
- `silver.fact_vendor_performance_quarterly`
- `silver.procurement_quality_flags`
- `silver.vendor_performance_quarterly_aggregated`

Silver facts should retain raw identifiers and values, plus typed/standardized values and explicit flags. Do not overwrite source values.

### Gold

- `gold.procurement_monthly_vendor_material_plant`
- `gold.procurement_monthly_material`
- `gold.procurement_monthly_vendor`
- `gold.procurement_monthly_plant`
- `gold.procurement_monthly_business`
- `gold.material_commodity_lag_features`
- `gold.vendor_performance_quarterly`
- `gold.forecasting_panel_vendor_material_plant_month`
- `gold.data_quality_scorecard`

Each Gold table needs a declared grain, inclusion/exclusion policy, currency/UOM semantics, and reconciliation totals.

## 18. Recommended Project Folder Structure

```text
src/
  config/
  ingestion/
  transformations/
  quality/
  marts/
  forecasting/
sql/
  raw/
  silver/
  gold/
  audit/
tests/
notebooks/
reports/
data/
  raw/
  reference/
```

The existing generator and notebooks should be preserved as evidence/prototyping assets while reusable logic moves into tested modules.

## 19. Files to Reuse, Modify, or Create

### Reuse

- `data/*.csv`, `data/manifest.json`, `data/data_dictionary.csv`
- `data/DATA_QUALITY_GUIDE.md`, `data/README.md`
- `data/source/build_ecco_dataset.py` for synthetic test fixtures
- Notebook SQL checks and generated report schemas
- `data/er_diagram.mmd`

### Modify later, after approval

- `load_data/postgres_schema.sql`: add layered schemas and audit/control objects.
- `load_data/load_postgres.sql` and `load_data/Database_loader.sql`: consolidate duplicate loader paths and add controlled batch metadata.
- `requirements.txt`: pin compatible versions.
- Notebooks: extract reusable validation functions and update references after schema changes.

### Create in Phase 1

- Transformation rule register with approval states.
- Raw ingestion/run-control tables.
- Silver typed/flagged tables.
- Exception and reconciliation tables.
- UOM conversion reference.
- Currency alias/reference table.
- Curated performance aggregation.
- Gold marts and validation SQL.
- Automated tests for key grain, joins, FX, UOM, totals, and leakage controls.

## 20. Final Technical Conclusions and Next Actions

The project has a strong synthetic source package, clear relational design, useful notebooks, and unusually explicit quality cautions. The existing work should not be recreated. The immediate next step is to formalize and implement the proposed transformation rules in a layered, auditable PostgreSQL design.

Before implementation begins, obtain confirmation for the assumptions in Section 13, especially currency aliasing, UOM conversions, duplicate reconciliation, missing-month semantics, contract validity, authoritative price field, commodity exposure, and supplier-performance aggregation.

The first implementation milestone should be a read-only or dual-write Silver prototype that preserves raw values, emits quality flags, and reconciles row counts and spend totals. Gold analytics and forecasting should remain downstream of that validation boundary.

## Evidence and Limitations

- Repository files, generated reports, notebooks, SQL scripts, and local PostgreSQL metadata were inspected.
- No credentials or `.env` values are included.
- No SQL modifying statement, loader script, notebook execution, package installation, or source-data mutation was performed for this audit.
- PostgreSQL findings apply to the reachable local `ecco_procurement` instance at audit time.
- The companion CSV inventory is the authoritative file-level deliverable for this audit.
