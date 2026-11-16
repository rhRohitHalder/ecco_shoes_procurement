# Phase 1A Silver and Gold Schema Design

## Evidence and grain decision

The public source schema remains unchanged. `bridge_vendor_material.vendor_material_id`
identifies one approved vendor-material-plant sourcing relationship. The intended source
record grain is therefore vendor-material-plant-month, represented by
`fact_procurement_monthly.procurement_id`. The candidate analytical key is
`(vendor_material_id, month)`, but it is not unique: the current source has 157 repeated
groups affecting 314 rows. Silver must preserve those technical rows rather than
silently aggregate them.

The current bridge query found no `(vendor_id, material_id)` combination assigned to
more than one plant. The design still retains plant explicitly because the relationship
key and future source data may support that case, and plant-level price differences must
be assessed before any plant roll-up.

## Schemas

- `public`: existing source tables only; no changes, migrations, or loader execution.
- `silver`: source-preserving, typed, traceable transformations.
- `gold`: approved analytical grains and aggregates.
- `audit`: rule outcomes, exceptions, duplicate decisions, and run metadata.
- `raw`: not proposed in Phase 1A; the existing public source is not migrated. A raw
  snapshot schema would require a separately approved versioned-ingestion requirement.

## Silver tables

### `silver.procurement_clean`

**Grain:** one row per source `procurement_id`.

**Key:** primary key `source_procurement_id`; non-unique candidate key
`(vendor_material_id, procurement_month)`.

**Identifiers and relationship fields:** `source_procurement_id`,
`vendor_material_id`, `reported_vendor_id`, `canonical_vendor_id`,
`source_material_id`, `source_plant_id`, `purch_org_id`, `material_description`,
`material_group_id`, `source_system`, and `document_grain`.

**Original measures:** `order_value_local`, `original_order_currency`,
`original_po_qty`, `original_po_uom`, `original_gr_qty`, `original_gr_uom`,
`unit_price_local`, and `source_order_value_eur`.

**Reference context:** `material_base_uom`, `contract_currency`,
`approved_from`, and `approved_to`.

**Derived measures:** `normalized_currency`, `applied_units_per_eur`,
`eur_expenditure`, `po_to_base_factor`, `standardized_po_qty`, and
`eur_unit_price`.

**Statuses and flags:** `fx_conversion_status`, `uom_conversion_status`,
`price_reconciliation_status`, `duplicate_group_id`,
`duplicate_investigation_status`, `vendor_resolution_status`,
`zero_quantity_positive_spend_flag`, `missing_quantity_flag`,
`missing_value_flag`, `negative_gr_flag`, `gr_exceeds_po_flag`, and
`exception_count`.

Currency and UOM originals are never overwritten. EURO remains unresolved until
approved as an EUR alias. No contract-currency fallback is permitted. EUR expenditure
uses `order_value_local / applied_units_per_eur` only when the currency mapping and
monthly rate are valid. Unit price requires positive standardized quantity and valid
expenditure.

### `silver.procurement_relationship`

**Grain:** one row per `vendor_material_id`.

**Key:** `vendor_material_id`.

Copies the bridge relationship context needed for reproducibility: canonical vendor,
material, plant, contract, approval dates, contract currency, quoted price, lead time,
minimum order quantity, and allocation target. This avoids repeating unchanged
relationship fields as an independent copy on every downstream table while allowing
Silver joins to remain stable.

### `silver.vendor`, `silver.material`, `silver.plant`, `silver.purchasing_org`,
and `silver.commodity`

Each table preserves its corresponding public dimension at the source primary-key grain,
with ingestion metadata and no business-value correction. `silver.material` is the
authority for base UOM; `silver.vendor` is descriptive master data, not the authority
for procurement relationship resolution.

### `silver.fx_monthly`

**Grain:** `(month, from_currency, to_currency)`.

Copies the public monthly FX reference with `units_per_eur`, rate type, and source label.
The design requires `from_currency = EUR`; the rate means quote-currency units per EUR.

### `silver.uom_conversion`

**Grain:** one approved conversion direction per `(from_uom, to_uom, effective period)`.

No rows are invented in Phase 1A. PCS-to-PAA and every other unresolved relationship
remain pending until an approved factor and semantic definition exist.

### `silver.material_commodity_monthly`

**Grain:** one material-commodity-month observation after the bridge and index joins.

Retains exposure weight, index price, missing-index status, and weighted contribution.
Weight denominators must be validated before publishing a weighted index.

### `silver.supplier_performance_quarterly`

**Grain:** one reconciled vendor-plant-quarter only after duplicate performance rows
are investigated. Raw source rows and reconciliation status belong in
`audit.performance_duplicate_review`; raw quarterly rows must not be joined directly
to procurement.

## Audit tables

- `audit.procurement_duplicate_review`: duplicate group, source IDs, measure totals,
  comparison fields, reviewer decision, and reconciliation status.
- `audit.procurement_exceptions`: one row per source record and rule ID, with original
  value, exception reason, severity, and resolution status.
- `audit.transformation_run`: read-only source snapshot metadata, rule-register version,
  row counts, and validation outcomes.
- `audit.performance_duplicate_review`: repeated vendor-plant-quarter rows,
  delivery-line totals, and approved weighting decision.

## Gold tables

All Gold tables retain separate expenditure and unit-price measures. Weighted-average
pricing is allowed only after quantities share an approved unit and source rows have
passed duplicate and currency gates.

| Table | Grain and key | Dependencies and logic |
|---|---|---|
| `gold.vendor_material_plant_monthly` | `(vendor_material_id, month)` after duplicate policy | Source-preserving relationship-level monthly aggregation; retain plant and duplicate/reconciliation metrics. |
| `gold.vendor_material_monthly` | `(vendor_id, material_id, month)` | Roll up only after plant differences and duplicate decisions are assessed; preserve plant count and source coverage. |
| `gold.vendor_monthly` | `(vendor_id, month)` | Aggregate EUR expenditure and comparable quantities; weighted unit price only for comparable units. |
| `gold.material_monthly` | `(material_id, month)` | Aggregate across vendors/plants with provenance counts; never mix unresolved UOMs in weighted price. |
| `gold.business_monthly` | `(purch_org_id, month)` | Procurement expenditure and quantity by purchasing organization; missing source rows are not zero spend. |
| `gold.material_commodity_monthly` | `(material_id, commodity_id, month)` | Approved exposure weights times commodity index; missing index prices remain flagged. |
| `gold.vendor_performance_quarterly` | `(vendor_id, plant_id, quarter_start)` | One reconciled KPI row after performance duplicate and delivery-line weighting approval. |
| `gold.forecast_base_monthly` | `(vendor_material_id, month)` | Expected panel bounded by approved relationship dates; distinguishes observed, explicit zero, and no-source-row. |

`gold.vendor_material_plant_monthly` is the first aggregation target. It must not be
published as a unique row until the duplicate rule is approved; a provisional audit
view can expose duplicate groups without collapsing them. The vendor-material,
vendor, material, and business tables inherit that decision.

## Validation criteria

1. Every Silver source row has a unique `source_procurement_id`.
2. No source table is updated, deleted, truncated, or loaded by an existing replace
   script.
3. Every canonical relationship join is explainable; unmatched relationships are
   exceptions.
4. EURO, UOM mismatch, missing FX, missing values, zero quantities, and vendor
   mismatches remain queryable flags.
5. EUR expenditure is independently recomputable from retained local value and rate.
6. Unit price is NULL whenever quantity is non-positive, missing, incomparable, or
   unresolved.
7. Gold row counts and sums reconcile to Silver after explicit inclusion/exclusion
   rules.
8. Performance joins occur only after quarterly reconciliation and never directly from
   raw performance to procurement.
