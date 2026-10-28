-- PostgreSQL schema for the synthetic ECCO procurement data package.
-- Run this file once before running load_postgres.sql.

CREATE TABLE IF NOT EXISTS dim_purchasing_org (
    purch_org_id TEXT PRIMARY KEY,
    purch_org_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_plant (
    plant_id TEXT PRIMARY KEY,
    plant_name TEXT NOT NULL,
    country_code TEXT NOT NULL,
    local_currency TEXT NOT NULL,
    purch_org_id TEXT NOT NULL REFERENCES dim_purchasing_org (purch_org_id)
);

CREATE TABLE IF NOT EXISTS dim_vendor (
    vendor_id TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    vendor_country TEXT NOT NULL,
    preferred_currency TEXT NOT NULL,
    approved_status TEXT NOT NULL,
    payment_terms_days INTEGER NOT NULL,
    incoterm TEXT NOT NULL,
    vendor_tier TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_material (
    material_id TEXT PRIMARY KEY,
    material_7 TEXT NOT NULL,
    material_description TEXT NOT NULL,
    material_group_id TEXT NOT NULL,
    material_group_name TEXT NOT NULL,
    base_uom TEXT NOT NULL,
    product_category TEXT NOT NULL,
    active_from DATE NOT NULL,
    active_to DATE
);

CREATE TABLE IF NOT EXISTS dim_commodity (
    commodity_id TEXT PRIMARY KEY,
    commodity_name TEXT NOT NULL,
    index_unit TEXT NOT NULL,
    source_label TEXT NOT NULL,
    source_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bridge_vendor_material (
    vendor_material_id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL REFERENCES dim_material (material_id),
    vendor_id TEXT NOT NULL REFERENCES dim_vendor (vendor_id),
    plant_id TEXT NOT NULL REFERENCES dim_plant (plant_id),
    contract_id TEXT NOT NULL,
    approved_from DATE NOT NULL,
    approved_to DATE,
    contract_currency TEXT NOT NULL,
    quoted_unit_price NUMERIC,
    lead_time_days INTEGER,
    min_order_qty INTEGER,
    allocation_target_pct NUMERIC
);

CREATE TABLE IF NOT EXISTS bridge_material_commodity (
    material_id TEXT NOT NULL REFERENCES dim_material (material_id),
    commodity_id TEXT NOT NULL REFERENCES dim_commodity (commodity_id),
    exposure_weight NUMERIC NOT NULL,
    lag_months INTEGER NOT NULL,
    mapping_confidence TEXT NOT NULL,
    valid_from DATE NOT NULL,
    PRIMARY KEY (material_id, commodity_id)
);

CREATE TABLE IF NOT EXISTS fact_commodity_monthly (
    commodity_id TEXT NOT NULL REFERENCES dim_commodity (commodity_id),
    month DATE NOT NULL,
    index_price NUMERIC,
    index_currency TEXT NOT NULL,
    index_unit TEXT NOT NULL,
    publication_status TEXT NOT NULL,
    benchmark_region TEXT NOT NULL,
    PRIMARY KEY (commodity_id, month)
);

CREATE TABLE IF NOT EXISTS fact_fx_monthly (
    month DATE NOT NULL,
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    units_per_eur NUMERIC NOT NULL,
    rate_type TEXT NOT NULL,
    source_label TEXT NOT NULL,
    PRIMARY KEY (month, from_currency, to_currency)
);

CREATE TABLE IF NOT EXISTS fact_procurement_monthly (
    procurement_id TEXT PRIMARY KEY,
    purch_org_id TEXT NOT NULL REFERENCES dim_purchasing_org (purch_org_id),
    material_7 TEXT NOT NULL,
    material_id TEXT NOT NULL REFERENCES dim_material (material_id),
    -- This is the source-system value. It is intentionally not an FK:
    -- DQ07 contains invalid vendor keys that must remain loadable for QA.
    vendor_id TEXT NOT NULL,
    vendor_material_id TEXT NOT NULL REFERENCES bridge_vendor_material (vendor_material_id),
    material_description TEXT NOT NULL,
    plant_id TEXT NOT NULL REFERENCES dim_plant (plant_id),
    material_group_id TEXT NOT NULL,
    month DATE NOT NULL,
    order_value_local NUMERIC,
    order_currency TEXT NOT NULL,
    po_qty NUMERIC,
    po_uom TEXT NOT NULL,
    gr_qty NUMERIC NOT NULL,
    gr_uom TEXT NOT NULL,
    unit_price_local NUMERIC,
    order_value_eur NUMERIC,
    is_zero_activity INTEGER NOT NULL,
    source_system TEXT NOT NULL,
    document_grain TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_vendor_performance_quarterly (
    performance_id TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL REFERENCES dim_vendor (vendor_id),
    plant_id TEXT NOT NULL REFERENCES dim_plant (plant_id),
    quarter_start DATE NOT NULL,
    quarter_end DATE NOT NULL,
    delivery_lines INTEGER NOT NULL,
    on_time_delivery_pct NUMERIC NOT NULL,
    defect_rate_pct NUMERIC NOT NULL,
    avg_actual_lead_days INTEGER NOT NULL,
    price_variance_pct NUMERIC NOT NULL,
    capacity_utilization_pct NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_issue_register (
    issue_id TEXT PRIMARY KEY,
    issue_code TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    business_key TEXT NOT NULL,
    description TEXT NOT NULL,
    recommended_handling TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_procurement_month
    ON fact_procurement_monthly (month);
CREATE INDEX IF NOT EXISTS idx_procurement_material
    ON fact_procurement_monthly (material_id);
CREATE INDEX IF NOT EXISTS idx_procurement_vendor_material
    ON fact_procurement_monthly (vendor_material_id);
CREATE INDEX IF NOT EXISTS idx_performance_vendor_quarter
    ON fact_vendor_performance_quarterly (vendor_id, quarter_start);
