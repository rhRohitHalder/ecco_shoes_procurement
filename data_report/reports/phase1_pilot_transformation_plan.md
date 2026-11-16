# Phase 1A Pilot Transformation Plan

## Scope and guardrails

This is a design for a read-only pilot, not an executed transformation. The pilot uses
real source IDs from the existing PostgreSQL `public` schema and does not create
Silver or Gold tables. Existing loaders are prohibited because they use
`TRUNCATE ... CASCADE`. Existing notebooks, source files, SQL scripts, and
configuration remain unchanged.

The pilot records source `procurement_id` as the technical identity. The target Silver
grain is one row per source record, not one row per `(vendor_material_id, month)`.
The latter is a candidate business key with verified duplicate violations.

## Source-to-target flow

1. Read `public.fact_procurement_monthly` in a read-only transaction.
2. Join `public.bridge_vendor_material` on `vendor_material_id`.
3. Validate source material and plant against the bridge relationship.
4. Join `public.dim_material` for `base_uom`.
5. Normalize the month to the existing first-of-month value.
6. Retain all original vendor, currency, UOM, quantity, receipt, value, and price
   fields.
7. Resolve canonical vendor from the bridge while retaining the reported vendor.
8. Normalize currency only through an approved alias mapping. EURO is not silently
   treated as EUR in the pilot until approval.
9. Join monthly FX by normalized order currency and month. The rate direction is
   EUR-to-quote currency, so `eur_expenditure = order_value_local /
   units_per_eur`.
10. Join UOM factors only from an approved mapping. Without a factor,
    `standardized_po_qty` and comparable unit price remain NULL.
11. Assign duplicate group and exception flags without aggregating.

## Confirmed and provisional formulas

For a valid non-EUR row:

```text
eur_expenditure = order_value_local / applied_units_per_eur
```

For EUR:

```text
eur_expenditure = order_value_local
```

For a comparable row with a positive standardized quantity:

```text
eur_unit_price = eur_expenditure / standardized_po_qty
```

These formulas are technically confirmed by the generator, schema, and current FX
direction. Monthly average FX is still a provisional proxy because the procurement
fact has no payment-date column. Contract currency is never a fallback for a missing
or unresolved order-currency rate.

## Pilot cases and expected outcomes

The selected source IDs are listed in
`phase1_pilot_selection.csv`. Expected outcomes below are assertions, not executed
Silver results.

| Case | Source evidence | Expected Silver behavior |
|---|---|---|
| Multi-plant vendor-material | Current bridge-wide query returned zero pairs with more than one plant | Record source-coverage limitation; do not fabricate a case. Plant remains a required field. |
| Repeated business key | `POA0002323` and `POA10002323`, `VM00162`, 2022-11 | Two source rows remain; same duplicate group; no automatic sum or winner. |
| EUR row | `POA0001056`, EUR, value 5429.52 | Rate 1 and EUR expenditure 5429.52 if quantity/value gates permit; unit price remains NULL because PO quantity is zero. |
| Non-EUR FX | `POA0000247`, BRL value 834.09, rate 4.449 | Recomputed expenditure is `834.09 / 4.449`; retain source EUR value separately and preserve rate provenance. |
| EURO alias | `POA0001364`, EURO, contract currency EUR | Keep original EURO and set alias-pending status; use EUR rate only after business approval. |
| EURO with different contract currency | `POA0002355`, EURO, contract currency VND | Demonstrates that contract currency must not be silently substituted for order currency. |
| UOM mismatch | `POA0000591`, PO PCS, material base PAA | Keep PCS and PAA; no standardized quantity or comparable price without an approved factor. |
| Zero quantity with spend | `POA0001056` and `POA0001265` | Preserve spend, set zero-quantity-positive-spend, and leave unit price NULL. |
| Missing value | `POA0000311` | Preserve NULL local value; no EUR expenditure or derived price. |
| Missing quantity | `POA0001292` | Preserve NULL quantity; expenditure may be derived if FX is valid, unit price remains NULL. |
| Missing expected month | `VM00011`, missing 2020-03-01 | Gold panel may emit `NO_SOURCE_ROW`; no zero spend or fabricated Silver procurement row. |
| Vendor mismatch | `POA0000247`, reported 999999, canonical 100032 | Retain both IDs and set mismatch status; do not rewrite source vendor. |

## Exception handling

- **Missing order value:** retain NULL, set `missing_value_flag`, and exclude from
  expenditure totals until resolved.
- **Missing or zero PO quantity:** retain original quantity, set flags, and suppress
  unit price. GR is not substituted for PO quantity.
- **EURO:** retain original alias and block FX conversion until alias approval.
- **Missing FX:** retain local value and unresolved FX status; never use contract
  currency as a fallback.
- **UOM mismatch:** retain both UOMs and suppress standardization until a factor is
  approved. PCS is observed in procurement but not in material base UOMs.
- **Vendor mismatch:** canonical relationship is a provisional analytical resolution;
  reported ID remains available for audit.
- **Duplicate candidate key:** preserve every technical row and assign a review group.
  Any Gold aggregation requires an approved reconciliation method.
- **Missing month:** represent absence only in the forecast panel, bounded by approved
  relationship dates and source coverage. Absence is not explicit zero activity.

## Validation queries

The implementation should run these validations before publishing any Silver pilot:

```sql
-- Technical row preservation
SELECT COUNT(*) AS source_rows,
       COUNT(DISTINCT procurement_id) AS distinct_source_ids
FROM public.fact_procurement_monthly;

-- Candidate duplicate groups
SELECT vendor_material_id, month, COUNT(*) AS row_count
FROM silver.procurement_clean
GROUP BY vendor_material_id, month
HAVING COUNT(*) > 1;

-- Canonical vendor mismatch
SELECT COUNT(*)
FROM silver.procurement_clean
WHERE reported_vendor_id <> canonical_vendor_id;

-- EUR recomputation
SELECT source_procurement_id,
       order_value_local / applied_units_per_eur AS expected_eur_expenditure,
       eur_expenditure
FROM silver.procurement_clean
WHERE applied_units_per_eur IS NOT NULL
  AND order_value_local IS NOT NULL;

-- Price comparability gate
SELECT COUNT(*)
FROM silver.procurement_clean
WHERE eur_unit_price IS NOT NULL
  AND (standardized_po_qty IS NULL OR standardized_po_qty <= 0);
```

The last query must return zero. Additional checks must confirm that no raw quarterly
performance row is joined directly to procurement and that every Gold aggregate is
reconcilable to its Silver source rows.

## Business decisions required before implementation

1. Approve EURO as an alias for EUR.
2. Confirm order currency as the expenditure authority when it differs from contract
   currency.
3. Provide approved UOM definitions and conversion factors, especially PCS/PAA.
4. Define duplicate reconciliation for repeated `(vendor_material_id, month)` rows.
5. Confirm missing-month panel boundaries and whether no source row means inactivity,
   missing capture, or an out-of-scope event.
6. Approve delivery-line weighting and reconciliation for repeated supplier
   performance observations.
7. Approve commodity weight semantics and treatment of missing index prices.

Until these decisions are approved, the pilot can safely produce source-preserving
Silver records and exception audit output, but comparable Gold unit-price and supplier
performance analytics remain blocked.
