-- Replace-load all CSV data into PostgreSQL.
-- Run from the repository root with:
--   psql -d ecco_procurement -v ON_ERROR_STOP=1 -f data/load_postgres.sql

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE TABLE
    data_quality_issue_register,
    fact_vendor_performance_quarterly,
    fact_procurement_monthly,
    fact_fx_monthly,
    fact_commodity_monthly,
    bridge_material_commodity,
    bridge_vendor_material,
    dim_commodity,
    dim_material,
    dim_vendor,
    dim_plant,
    dim_purchasing_org
CASCADE;

\copy dim_purchasing_org FROM 'data/dim_purchasing_org.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy dim_plant FROM 'data/dim_plant.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy dim_vendor FROM 'data/dim_vendor.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy dim_material FROM 'data/dim_material.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy dim_commodity FROM 'data/dim_commodity.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy bridge_vendor_material FROM 'data/bridge_vendor_material.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy bridge_material_commodity FROM 'data/bridge_material_commodity.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy fact_commodity_monthly FROM 'data/fact_commodity_monthly.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy fact_fx_monthly FROM 'data/fact_fx_monthly.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy fact_procurement_monthly FROM 'data/fact_procurement_monthly.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy fact_vendor_performance_quarterly FROM 'data/fact_vendor_performance_quarterly.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy data_quality_issue_register FROM 'data/data_quality_issue_register.csv' WITH (FORMAT csv, HEADER true, NULL '')

COMMIT;

