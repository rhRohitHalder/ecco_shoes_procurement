# ECCO-style raw material procurement forecasting — synthetic data package

**IMPORTANT: This is fully synthetic demonstration data, NOT authentic ECCO procurement, vendor, commodity or currency data.** The user-provided sample supplied field conventions, not verified transactions. Supplier names except the illustrative first sample are invented; even that sample is not asserted to be an ECCO supplier. All prices, FX rates, lead times, quality and performance observations are simulated. Do not present model accuracy on this dataset as real-world evidence.

## Scope
- Historical monthly range: **2020-01 through 2026-09**, inclusive (81 months).
- **1,200 SKUs**, **95 vendors**, **6 plants**, **13 commodity indices**; individual SKUs have 2–4 possible vendors.
- Source-like procurement fact reflects order values and PO/GR quantities at **SKU × vendor × plant × month**, with explicit zero months and absent months. PO aggregation is *not* a PO-line transaction ledger.
- Commodity mapping supports material-weighted lag features, and monthly FX enables EUR normalization.
- Vendor performance is synthetic quarterly information. For true production use, aggregate its entries correctly to distinct vendor–plant–quarter records (the sample intentionally models relationship-level observations).

## Files and rows
- `dim_plant.csv`: 6 rows
- `dim_purchasing_org.csv`: 2 rows
- `dim_commodity`: 13 rows
- `dim_vendor.csv`: 95 rows
- `dim_material.csv`: 1,200 rows
- `bridge_vendor_material.csv`: 2,910 rows
- `bridge_material_commodity.csv`: 3,600 rows
- `fact_commodity_monthly.csv`: 1,053 rows
- `fact_fx_monthly.csv`: 729 rows
- `fact_procurement_monthly.csv`: 174,638 rows
- `fact_vendor_performance_quarterly.csv`: 78,570 rows
- `data_quality_issue_register.csv`: 2,054 rows
- `data_dictionary.csv`: 99 rows
- `er_diagram.mmd`: editable Mermaid ER diagram
- `er_diagram.svg`: rendered ER diagram if local rendering available
- `data_dictionary.csv`: all field definitions, keys, types and grains
- `DATA_QUALITY_GUIDE.md`: injection catalogue and interpretation
- `build_ecco_dataset.py`: reproducible generator

## Important joins
1. `fact_procurement_monthly.vendor_material_id` → `bridge_vendor_material.vendor_material_id`, then material, vendor, plant dimensions. In bad rows, fact vendor_id may disagree; use relationship key as canonical but **flag** mismatch.
2. `bridge_material_commodity.material_id` → `dim_material.material_id` and `commodity_id` → `fact_commodity_monthly.commodity_id`; join commodity observations on requested lagged month for time-causal modeling.
3. `fact_fx_monthly`: `month = procurement.month`, `to_currency = procurement.order_currency`, `from_currency = EUR`. Divide local order value by `units_per_eur` to convert to EUR. Do not re-convert existing `order_value_eur`.
4. Procurement unit price: order value / PO quantity where both are valid, and PO qty > 0. Do not treat missing months or zero-PO months as observed price = 0.
5. Vendor quarterly KPIs should be aggregated (weighted by delivery_lines for on-time and defect percentages); lag signals when predicting future months to avoid data leakage.

## Forecasting / data engineering cautions
- Build forecasting panel over **vendor × material × plant × month**, retain `purchased_this_month` and missingness flags. Forecasting **unit price conditional on a purchase** differs from demand / procurement occurrence forecasting.
- Resolve PAA / PCS / KG / SQM unit mismatches before EUR-per-base-unit price comparisons.
- Check vendor contracts' start/end dates and avoid future vendor performance, commodity publication and spot FX leakage.
- The material and vendor master have plausible structural features but are generated with patterns; synthetic data can be used to test ETL, joins, UI and pipeline behavior, not procurement decisions.
- No material-price forecasts are included: all months are simulated historical observations.

## Reproducibility
Run `python3 build_ecco_dataset.py` in the directory above this folder. It deterministically recreates the CSVs (Python 3.10+). The exported records may have intentional discrepancies recorded in the issue register.

## Load into PostgreSQL

For a single-file setup that creates the database, creates the schema, and
loads every CSV, use the root-level [Database_loader.sql](../Database_loader.sql):

```powershell
psql -d postgres -v ON_ERROR_STOP=1 -f Database_loader.sql
```

Run this command from the repository root. It creates `ecco_procurement` if it
does not exist, connects to it, follows the ER diagram's dependency order, and
loads the unchanged CSV files. Running it again replaces the rows in these
project tables.

The repository also includes the separate schema and loader files below when
you need to run those phases independently.

The repository includes [postgres_schema.sql](./postgres_schema.sql) and
[load_postgres.sql](./load_postgres.sql). The loader uses PostgreSQL `\copy`, so
the CSV files are read by the `psql` client from the repository working
directory.

1. Install PostgreSQL and make sure `psql` is available on `PATH`.
2. Create a database:

   ```powershell
   createdb ecco_procurement
   ```

3. From the repository root, create the tables:

   ```powershell
   psql -d ecco_procurement -v ON_ERROR_STOP=1 -f data\postgres_schema.sql
   ```

4. Load or reload all CSV files:

   ```powershell
   psql -d ecco_procurement -v ON_ERROR_STOP=1 -f data\load_postgres.sql
   ```

   The load is a replace-load: it truncates the project tables before importing
   the CSVs. Do not run it against tables containing unrelated data.

5. Verify the import:

   ```sql
   SELECT 'dim_material' AS table_name, count(*) FROM dim_material
   UNION ALL SELECT 'dim_vendor', count(*) FROM dim_vendor
   UNION ALL SELECT 'fact_procurement_monthly', count(*) FROM fact_procurement_monthly
   UNION ALL SELECT 'fact_vendor_performance_quarterly', count(*) FROM fact_vendor_performance_quarterly
   UNION ALL SELECT 'data_quality_issue_register', count(*) FROM data_quality_issue_register;
   ```

The reported `fact_procurement_monthly.vendor_id` is intentionally not a
foreign key because the dataset contains DQ07 invalid vendor keys. Use
`vendor_material_id` as the canonical relationship and compare the reported
vendor to the bridge when auditing source quality. Blank CSV fields are loaded
as SQL `NULL`; this is important for missing values and dates. The exported records may have intentional discrepancies recorded in the issue register.
