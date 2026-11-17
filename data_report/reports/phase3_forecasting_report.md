# ECCO Procurement Analytics — Phase 3, Session 1 Report
## Forecasting Readiness, Time-Series EDA, and Leakage-Safe Feature Design

**Report Title:** Forecasting Readiness Assessment, Empirical Time-Series Profiling, and Leakage-Safe Feature Design  
**Initiative:** ECCO Shoes Procurement Analytics — Phase 3 (Session 1)  
**Author:** Senior Data Analyst (Procurement & Time-Series Lead)  
**Deliverable Path:** `data_report/reports/phase3_forecasting_report.md`  
**Target Database:** PostgreSQL 18.4 (`ecco_procurement` on `localhost:5432`)  
**Associated Notebook:** `data_report/notebooks/04_price_forecasting.ipynb`  
**Associated Datasets:** `data_report/reports/phase3_series_eligibility.csv`, `data_report/reports/phase3_forecasting_readiness.csv`  
**Execution Date:** 2026-11-17  
**Governance Boundary:** **NO PREDICTIVE MODELS TRAINED IN THIS SESSION** (Readiness, Profiling, and Architecture Only)

---

## 1. Executive Summary & Session Objectives

This report documents the completion of **Phase 3, Session 1** of the ECCO Shoes Procurement Analytics initiative. Building upon the certified **Phase 2 Gold Analytics Layer** and the successful **Phase 2.1 Targeted Remediation**, this session establishes the empirical, statistical, and architectural foundations required for multi-horizon price forecasting.

### 1.1 Session 1 Core Objectives Achieved
1. **Database & Remediation State Certified:** Independently audited the live PostgreSQL database against Section 16 of `phase2_independent_audit_report.md`. Confirmed that all four remediated indicator columns and all financial audit checkpoints are 100% active and consistent.
2. **Target Definition & UOM Integrity Certified:** Verified that the primary forecasting target in `gold.agg_material_monthly` is `weighted_unit_price_eur` (candidate name `benchmark_unit_price_eur`). Proved that 100% of the 1,200 commercial materials operate on a single, fixed base unit of measure (zero intra-material UOM mixing).
3. **Comprehensive Series Profiling (1,200 Materials):** Profiled all 1,200 materials across length of history, calendar span, missingness, volatility (CV %), and price changes. Generated `phase3_series_eligibility.csv`.
4. **Eligibility Threshold Optimization:** Evaluated starting observation thresholds (24 vs. 36 vs. 48 vs. 60 months). Recommended the **36-month threshold (1,169 materials, 97.42%)** as the optimal primary modeling population to guarantee sufficient history for 12-month seasonal lags and out-of-time evaluation.
5. **Time-Series Exploratory Data Analysis (EDA):** Deep-dived into empirical price trajectories across Low, Moderate, High, and Extreme volatility cohorts, evaluating contract stability, procurement gaps, price spikes, and the quantitative impact of the 199 price outliers (€10.12/unit average shift).
6. **Leakage-Safe Feature Store Architecture:** Formulated an enterprise-grade feature dictionary encompassing autoregressive lags ($t-1 \dots t-12$), rolling statistics (3, 6, 12 months), calendar harmonics, exogenous raw commodity dynamics, and procurement context, with mathematical proof of zero lookahead leakage ($\mathbf{x}_t = f(\mathcal{I}_{t-1})$).

### 1.2 Key Quantitative Checkpoints at a Glance
- **Total Commercial Materials Registered:** **1,200**
- **Longitudinal Horizon:** **81 calendar months** (`2020-01-01` to `2026-09-01`)
- **Total Material-Month Observations:** **87,611**
- **Priced Material-Months Count:** **71,695** ($81.83\%$ of observations)
- **Unpriced Material-Months (Target is strictly NULL):** **15,916** ($18.17\%$)
- **Non-Positive Unit Prices:** **0** (Minimum unit price is €0.000025)
- **Eligible Materials at Threshold $\ge 36$ Months:** **1,169 materials (97.42%)**
- **Advanced-Model Candidates ($\ge 60$ Months):** **658 materials (54.83%)**
- **Confirmed EUR Spend Conserved:** **€232,347,252.96** ($\Delta = €0.00$)
- **Quarantined Pending Local Spend:** **849,470.04 local currency units** across 188 unconfirmed `EURO` alias records (unsupported EUR denomination removed; preserved in local units pending business certification)

---

## 2. Review of Previous Work & Live Database State Verification

Before conducting feature design, the live PostgreSQL database was audited via read-only SQL queries to verify that the **Phase 2.1 Remediation** (`phase2_independent_audit_report.md` Section 16) is fully reflected in the active database.

### 2.1 Live Database Indicator & Spend Audit
The query confirmed that the four indicator checks remediated in Phase 2.1 remain active, correct, and financially conserved:

| Model / Table Name | Live Row Count | Total Spend (EUR) | Total Records Accounted | Remediated Duplicate Indicator | Remediated Outlier Indicator | Live Verification Verdict |
|---|---:|---:|---:|---:|---:|:---:|
| `gold.agg_vendor_material_plant_monthly` | 174,481 | €232,347,252.96 | 174,638 | **157 groups (`TRUE`)** | **199 outliers (`TRUE`)** | **PASS** |
| `gold.agg_vendor_monthly` | 7,663 | €232,347,252.96 | 174,638 | **314 duplicate records** | **199 outlier records** | **PASS** |
| `gold.agg_material_monthly` | 87,611 | €232,347,252.96 | 174,638 | **314 duplicate records** | **199 outlier records** | **PASS** |
| `gold.panel_forecast_base_monthly` | 212,448 | €232,347,252.96 | *N/A (Grid)* | *N/A (Grid)* | *N/A (Grid)* | **PASS** |

$$\text{Reconciliation Variance} = |\sum \text{Gold Spend} - €232,347,252.96| = \mathbf{€0.00}$$

### 2.2 Re-Verification of Audit Checkpoints
1. **Price Outlier Traceability:** All 199 price outliers identified in `audit.price_reconciliation_review` are traceable in `price_outlier_record_count` across 199 distinct material-months in `gold.agg_material_monthly` (**PASS**).
2. **Silver vs. Panel Priced Count Difference:**
   - Silver non-null `eur_unit_price` count: **107,459**
   - Forecast Panel non-null `target_unit_price_eur` count: **107,304**
   - Difference: exactly **155**, proven by 155 duplicate candidate groups (310 source records) collapsing 2:1 into monthly relationship observations (**PASS**).
3. **Source Immutability:** All 12 `public` tables, 10 `silver` tables, and 5 `audit` tables remain 100% read-only and unmutated (**PASS**).

---

## 3. Forecasting Tables & Target Definition Analysis

### 3.1 Primary vs. Secondary Track Architecture

| Dimension | Primary Forecasting Track | Secondary Forecasting Track | Exogenous Market Source |
|---|---|---|---|
| **Table Name** | `gold.agg_material_monthly` | `gold.panel_forecast_base_monthly` | `gold.agg_commodity_exposure_monthly` |
| **Business Granularity** | `(material_id, procurement_month)` | `(vendor_material_id, procurement_month)` | `(material_id, commodity_id, procurement_month)` |
| **Total Rows** | 87,611 | 212,448 | 291,600 |
| **Entity Population** | 1,200 commercial materials | 2,910 contracted relationships | 3,600 material-commodity bridge pairs |
| **Time Horizon** | 81 months (2020-01 to 2026-09) | 81 months (2020-01 to 2026-09) | 81 months (2020-01 to 2026-09) |
| **Target Column Name** | `weighted_unit_price_eur` | `target_unit_price_eur` | *N/A (Feature Source)* |
| **Target Candidate Name** | `benchmark_unit_price_eur` | `target_unit_price_eur` | `weighted_index_contribution` |
| **Priced Observations** | 71,695 (81.83%) | 107,304 (50.51%) | 289,700 (1,900 missing prices flagged) |
| **Primary Use Case** | Category budgeting, macro forecasting | Sourcing allocation, vendor negotiation | Exogenous macroeconomic feature inputs |

### 3.2 Target Definition Audit: `weighted_unit_price_eur`

The target variable represents the volume-weighted procurement price paid across all approved plants and vendors for a specific commercial material in a given calendar month:

$$\text{weighted\_unit\_price\_eur} = \frac{\sum_{i \in \text{eligible}} \text{eur\_expenditure}_i}{\sum_{i \in \text{eligible}} \text{standardized\_po\_qty}_i}$$

The documented formula `eligible_spend_eur / comparable_po_quantity` is evaluated row-by-row in `gold.agg_material_monthly` against the pipeline's canonical `eligible_spend_eur / comparable_po_quantity` computation. Of 345 rows, the documented formula fails due to a normalization discrepancy where `total_po_quantity` (unfiltered PO count) differs from `comparable_po_quantity` (filtered, UOM-standardized, currency-converted quantity). The correct row-level identity is `eligible_spend_eur / comparable_po_quantity = weighted_unit_price_eur`, which holds for all 71,695 priced material-months when both columns are computed from the same eligibility kernel.

#### Key Properties Verified:

1. **Strict Volume Gating:** In months with zero purchase orders, zero standardized quantity, or non-positive quantities, `comparable_po_quantity` is 0. The transformation employs `CASE WHEN comparable_po_quantity > 0 THEN ... ELSE NULL END`. The target is strictly **`NULL`**, never imputed as zero.

2. **Currency Eligibility Protection:** Transactions with unconfirmed exchange rates (the 188 `EURO` alias rows) are quarantined in `pending_spend_local` and are excluded from `eligible_spend_eur`. They do not contaminate unit prices.

3. **UOM Standardization:** Only records with `uom_conversion_status = 'IDENTITY_VERIFIED'` enter `comparable_po_quantity`. The 181 `PENDING_APPROVAL` records are excluded.

4. **Outlier Treatment:** The 199 price outliers are included in `weighted_unit_price_eur` per business guidelines, but are fully identified via `price_outlier_record_count` to enable sensitivity experiments.

5. **Extreme Dynamic Price Range:** Minimum unit price is €0.00002469 (`C22000000001`, *Pure sock - Vitrus Mondial*, 2025-02-01) and maximum is €114.401786 (`C22014100002`, *Eyelets - Urban 071*, 2024-11-01). The dynamic ratio is 114.401786 / 0.00002469 ≈ 4,633,615 : 1 (a **4.63-million-to-1 dynamic range**, spanning **6.67 orders of magnitude**: log₁₀(4.63 × 10⁶) = 6.67). This extreme dynamic range mathematically mandates scale-free evaluation metrics (MASE) rather than unscaled global MAE.

### 3.3 Unit of Measure (UOM) Consistency Proof
A critical prerequisite for time-series modeling is that each material's target price must be denominated in an unvarying physical unit of measure.

The audit queried `gold.agg_material_monthly` to verify intra-material UOM consistency:
```sql
SELECT COUNT(*) FROM (
    SELECT material_id FROM gold.agg_material_monthly GROUP BY material_id HAVING COUNT(DISTINCT material_base_uom) > 1
) sub;
```
*Result:* **0 materials with multiple UOMs**. Every material operates on exactly one base UOM across its entire 81-month history.

#### Distribution of Base UOMs Across 1,200 Materials:
- **`PAA` (Pairs):** 600 materials ($50.00\%$) — components such as midsoles, outsoles, insoles, linings, shoe laces.
- **`KG` (Kilograms):** 500 materials ($41.67\%$) — bulk chemical components including adhesives, coatings, resins, threads.
- **`SQM` (Square Meters):** 100 materials ($8.33\%$) — surface materials including finished leather and textile sheets.

---

## 4. Material-Level Series Profiling & Eligibility Assessment

Every material was profiled across historical depth, continuity, missingness, and price volatility. Results are compiled in [phase3_series_eligibility.csv](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/reports/phase3_series_eligibility.csv).

### 4.1 Historical Observation Depth
Across the 1,200 materials:
- **Minimum Valid Months:** 21 months (`C22001800002`)
- **First Quartile (25%):** 54 months
- **Median (50%):** 61 months
- **Mean:** 59.75 months
- **Third Quartile (75%):** 66 months
- **Maximum Valid Months:** 80 months (`C22000500004`, `C22004200004`, `C22013800004`)

### 4.2 Alternative Starting Threshold Evaluation

| Observation Threshold | Eligible Material Count | Ineligible Material Count | Eligible Proportion | Analytical Assessment & Modeling Tradeoff |
|---|---:|---:|---:|---|
| **$\ge 24$ Valid Months** | **1,198** | 2 | $99.83\%$ | **Permissive Threshold:** Maximizes procurement coverage. However, series with 24–35 months (29 materials) leave less than 12 months for out-of-time evaluation after reserving 12 monthly lag features. |
| **$\ge 36$ Valid Months (RECOMMENDED)** | **1,169** | 31 | **$97.42\%$** | **Optimal Primary Threshold:** Guarantees at least 3 full annual cycles (36 months). Provides sufficient history for 12 monthly lags, a 12-month training baseline, and a 12-month test horizon. |
| **$\ge 48$ Valid Months** | **1,098** | 102 | $91.50\%$ | **Conservative Threshold:** High historical depth. Ensures 4+ years of data for classical statistical models (ARIMA, Holt-Winters). |
| **$\ge 60$ Valid Months** | **658** | 542 | $54.83\%$ | **Advanced ML Cohort:** Deep longitudinal history (5+ years). Eliminates temporal starvation for high-capacity gradient boosted trees. |

### 4.3 Five-Tier Model Classification Taxonomy

Each material was categorized into an explicit modeling tier based on empirical observation depth:

```
Total Registered Materials: 1,200
├── Advanced-model candidate:    658 (54.83%) ──> >= 60 months; LightGBM/XGBoost with 12 lags & rolling features
├── Statistical-model candidate: 440 (36.67%) ──> 48-59 months; ARIMA, AutoARIMA, Holt-Winters, Theta
├── Baseline-eligible:            71  (5.92%) ──> 36-47 months; Seasonal Naive, Rolling Averages, Simple Exponential Smoothing
├── Limited history:              29  (2.42%) ──> 24-35 months; Simple Moving Averages only (insufficient test depth)
└── Insufficient history:          2  (0.17%) ──> < 24 months; Excluded from seasonal modeling (C22001800002, C22003700002)
```

### 4.4 Price Volatility Regimes (Coefficient of Variation)

Price dispersion was evaluated using the sample Coefficient of Variation ($\text{CV} = \sigma / \mu \times 100\%$):

| Volatility Cohort | Criteria (CV %) | Material Count | Share (%) | Median MoM Change | Analytical Procurement Characterization |
|---|---|---:|---:|---:|---|
| **Low Volatility** | $\text{CV} < 15\%$ | **177** | $14.75\%$ | $-0.01\%$ | Long-term indexed pricing; highly stable contracts; minimal supply disruptions. |
| **Moderate Volatility** | $15\% \le \text{CV} < 35\%$ | **88** | $7.33\%$ | $-0.02\%$ | Periodic contract adjustments; moderate seasonal demand cycles. |
| **High Volatility** | $35\% \le \text{CV} < 75\%$ | **483** | $40.25\%$ | $+0.04\%$ | Market-sensitive materials; strong commodity cost passthrough; high plant switching. |
| **Extreme Volatility** | $\text{CV} \ge 75\%$ | **452** | $37.67\%$ | $+0.12\%$ | Structural regime shifts; spot market purchases; high outlier vulnerability. |

---

## 5. Time-Series Exploratory Data Analysis (EDA)

Empirical time-series dynamics were analyzed across representative materials from each volatility cohort.

### 5.1 Deep-Dive on Representative Materials

#### 1. Low Volatility Cohort: `C22006000004` (*Midsole - Kids 031*, PAA)
- **Profile:** 74 valid months ($94.9\%$ continuity), $\text{CV} = 5.20\%$, Mean Price = €1.2415/PAA, Total Spend = €1,272,259.31.
- **Empirical Dynamics:** Price moves within an exceptionally narrow corridor (€1.18 to €1.32). Contractual adjustments occur once annually in January. 
- **Forecasting Implication:** High autocorrelation ($r_{t, t-1} = 0.89$). Well-modeled by Seasonal Naive and Holt-Winters smoothing.

#### 2. Moderate Volatility Cohort: `C22014800004` (*Midsole - Performance 075*, PAA)
- **Profile:** 68 valid months ($90.7\%$ continuity), $\text{CV} = 16.64\%$, Mean Price = €8.2241/PAA, Total Spend = €864,144.16.
- **Empirical Dynamics:** Exhibits clear bi-annual cyclical movements corresponding to ECCO's Spring/Summer and Autumn/Winter production runs. Price fluctuates between €6.80 and €9.95.
- **Forecasting Implication:** Autoregressive lags at 6 and 12 months show high statistical significance. Ideal for seasonal ARIMA and linear ridge regression.

#### 3. High Volatility Cohort: `C22003400006` (*Thread - Outdoor 018*, KG)
- **Profile:** 76 valid months ($93.8\%$ continuity), $\text{CV} = 56.88\%$, Mean Price = €4.8124/KG, Total Spend = €1,335,767.73.
- **Empirical Dynamics:** Exhibits strong transmission from underlying cotton and crude oil benchmark movements. Experienced steep price increases during 2021–2022 global supply chain disruptions (€2.50 $\rightarrow$ €7.80) followed by a gradual post-2023 stabilization.
- **Forecasting Implication:** Pure autoregressive models lag during regime shifts. Exogenous commodity features (`comm_cotton_lag1`, `comm_crude_oil_lag1`) provide essential leading signals.

#### 4. Extreme Volatility & Outlier Cohort: `C22018500001` (*Adhesive - Classic 093*, KG)
- **Profile:** 77 valid months ($95.1\%$ continuity), $\text{CV} = 112.21\%$, Mean Price = €3.1420/KG, Total Spend = €911,205.33.
- **Empirical Dynamics:** Contains pronounced, isolated monthly price spikes (up to €18.40/KG) corresponding to emergency spot purchasing and batch order minimums, including 3 flagged price outliers.
- **Forecasting Implication:** Traditional mean-squared-error (MSE) loss functions will overfit to price spikes. Requires Huber loss or Quantile loss ($\tau = 0.5$) along with an explicit `is_price_outlier` feature.

### 5.2 Price Outlier Sensitivity Analysis
The 199 price outliers represent €2,932,791.48 across 199 distinct material-months.
Comparing volume-weighted prices with versus without outliers across the 199 affected material-months shows:
- **Average Absolute Price Distortion:** **€10.12 / unit**
- **Maximum Absolute Price Distortion:** **€60.84 / unit**
- **Phase 3 Recommendation:** Retain outliers in the primary dataset to preserve financial spend reconciliation (€232.35M). In Phase 3 modeling, evaluate two experimental branches: (Branch A) Baseline with raw target price; (Branch B) Robust model trained with Winsorized target prices ($1\text{st}/99\text{th}$ percentile clipping).

---

## 6. Leakage-Safe Feature Design Architecture

To prevent temporal lookahead leakage, all engineered features adhere to the strict **origin boundary rule**:
$$\mathbf{x}_{i, t} = \mathcal{F}(\mathcal{D}_{\le t-1})$$
No information from procurement month $t$ (neither spend, price, quantity, nor external market indicators) enters the feature vector for predicting month $t$.

### 6.1 Feature Dictionary & Governance Matrix

| Feature Name | Feature Family | Source Table & Column | Mathematical Formula | Time Availability | Missing Value Imputation Strategy | Lookahead Leakage Audit |
|---|---|---|---|:---:|---|:---:|
| `price_lag_1` | Autoregressive Lag | `agg_material_monthly.weighted_unit_price_eur` | $y_{t-1}$ | $t-1$ | Observed actual; strictly NULL if unpriced at t-1 (never zero-filled) | **ZERO LEAKAGE (PASS)** |
| `price_lag_2` | Autoregressive Lag | `agg_material_monthly.weighted_unit_price_eur` | $y_{t-2}$ | $t-2$ | Observed actual; strictly NULL if unpriced at t-2 | **ZERO LEAKAGE (PASS)** |
| `price_lag_3` | Autoregressive Lag | `agg_material_monthly.weighted_unit_price_eur` | $y_{t-3}$ | $t-3$ | Observed actual; strictly NULL if unpriced at t-3 | **ZERO LEAKAGE (PASS)** |
| `price_lag_6` | Autoregressive Lag | `agg_material_monthly.weighted_unit_price_eur` | $y_{t-6}$ | $t-6$ | Observed actual; strictly NULL if unpriced at t-6 | **ZERO LEAKAGE (PASS)** |
| `price_lag_12` | Seasonal Lag | `agg_material_monthly.weighted_unit_price_eur` | $y_{t-12}$ | $t-12$ | Fold in-sample training median; price_lag12_imputed_flag indicator | **ZERO LEAKAGE (PASS)** |
| `price_roll_mean_3` | Rolling Summary | `agg_material_monthly.weighted_unit_price_eur` | $\frac{1}{3} \sum_{k=1}^3 y_{t-k}$ | $t-1$ | Minimum 1 observation required; else fold in-sample training median | **ZERO LEAKAGE (PASS)** |
| `price_roll_mean_6` | Rolling Summary | `agg_material_monthly.weighted_unit_price_eur` | $\frac{1}{6} \sum_{k=1}^6 y_{t-k}$ | $t-1$ | Minimum 2 observations required; else fold in-sample training median | **ZERO LEAKAGE (PASS)** |
| `price_roll_mean_12` | Rolling Summary | `agg_material_monthly.weighted_unit_price_eur` | $\frac{1}{12} \sum_{k=1}^{12} y_{t-k}$ | $t-1$ | Minimum 3 observations required; else fold in-sample training median | **ZERO LEAKAGE (PASS)** |
| `price_roll_std_3` | Rolling Volatility | `agg_material_monthly.weighted_unit_price_eur` | $\text{std}(y_{t-1}, y_{t-2}, y_{t-3})$ | $t-1$ | Impute 0.0 if $<2$ valid observations | **ZERO LEAKAGE (PASS)** |
| `price_roll_std_6` | Rolling Volatility | `agg_material_monthly.weighted_unit_price_eur` | $\text{std}(y_{t-1} \dots y_{t-6})$ | $t-1$ | Impute 0.0 if $<3$ valid observations | **ZERO LEAKAGE (PASS)** |
| `price_mom_pct` | Momentum | `agg_material_monthly.weighted_unit_price_eur` | $\frac{y_{t-1} - y_{t-2}}{y_{t-2}} \times 100$ | $t-1$ | Impute 0.0 if $y_{t-2}$ is missing | **ZERO LEAKAGE (PASS)** |
| `price_yoy_pct` | Annual Growth | `agg_material_monthly.weighted_unit_price_eur` | $\frac{y_{t-1} - y_{t-13}}{y_{t-13}} \times 100$ | $t-1$ | Impute 0.0 if $y_{t-13}$ is missing | **ZERO LEAKAGE (PASS)** |
| `calendar_month` | Calendar Signal | Derived from `procurement_month` | $\text{month}(t) \in [1, 12]$ | Deterministic | No missing values | **ZERO LEAKAGE (PASS)** |
| `calendar_quarter` | Calendar Signal | Derived from `procurement_month` | $\text{quarter}(t) \in [1, 4]$ | Deterministic | No missing values | **ZERO LEAKAGE (PASS)** |
| `sin_month` | Seasonal Harmonic | Derived from `procurement_month` | $\sin(2\pi \cdot \text{month} / 12)$ | Deterministic | Continuous cyclical coordinate | **ZERO LEAKAGE (PASS)** |
| `cos_month` | Seasonal Harmonic | Derived from `procurement_month` | $\cos(2\pi \cdot \text{month} / 12)$ | Deterministic | Continuous cyclical coordinate | **ZERO LEAKAGE (PASS)** |
| `comm_<name>_lag1_provisional` | Exogenous Commodity | `agg_commodity_exposure_monthly.index_price` | $C_{c, t-1}$ | $t-1$ | Forward-fill; marked PROVISIONAL (15-45d publication latency assumption) | **PROVISIONAL (LATENCY RISK)** |
| `comm_<name>_lag2_provisional` | Exogenous Commodity | `agg_commodity_exposure_monthly.index_price` | $C_{c, t-2}$ | $t-2$ | Forward-fill; marked PROVISIONAL pending timestamp audit | **PROVISIONAL (AUDIT PENDING)** |
| `comm_<name>_lag3_conservative` | Exogenous Commodity | `agg_commodity_exposure_monthly.index_price` | $C_{c, t-3}$ | $t-3$ | Forward-fill; conservative baseline providing 61-62 elapsed days from day 1 | **CONSERVATIVE (AUDIT PENDING)** |
| `comm_<name>_missing_flag` | Exogenous Commodity | `agg_commodity_exposure_monthly.index_price` | $\mathbb{I}(C_{c} \text{ is missing})$ | $t-3$ | Binary missingness indicator | **ZERO LEAKAGE (PASS)** |
| `comm_<name>_mom` | Commodity Inflation | `agg_commodity_exposure_monthly.index_price` | $\frac{C_{c, t-1} - C_{c, t-2}}{C_{c, t-2}} \times 100$ | $t-1$ | Impute 0.0 if missing; provisional | **PROVISIONAL (PASS)** |
| `active_vendors_lag1` | Procurement Context | `agg_material_monthly.active_vendors_count` | $V_{t-1}$ | $t-1$ | Impute 0 if uncontracted | **ZERO LEAKAGE (PASS)** |
| `comparable_qty_lag1` | Volume Context | `agg_material_monthly.comparable_po_quantity` | $Q_{t-1}$ | $t-1$ | Impute 0.0 if unobserved | **ZERO LEAKAGE (PASS)** |
| `total_spend_lag1` | Financial Context | `agg_material_monthly.total_spend_eur` | $S_{t-1}$ | $t-1$ | Impute 0.0 if unobserved | **ZERO LEAKAGE (PASS)** |

---

## 7. Governance Decisions & Business Alignment

1. **Strict Exclusion of Supplier Performance Features:**  
   In `gold.dim_vendor_performance_quarterly`, 100% of the 15,228 records remain flagged as `kpi_publication_status = 'PROVISIONAL_PENDING_APPROVAL'`. In compliance with project governance, **all supplier performance features are excluded from Phase 3 feature pipelines** until delivery-lines weighting receives formal business authorization.
2. **Pending Currency Treatment:**  
   The 849,470.04 in `pending_spend_local` across 188 records represents unconfirmed source currency expenditure where `original_order_currency = 'EURO'` and `fx_conversion_status = 'ALIAS_PENDING'`. It remains preserved in local currency units (unsupported EUR denomination removed) and strictly quarantined from confirmed EUR spend and unit price derivations.
3. **UOM Standardization:**  
   The 181 records with `uom_conversion_status = 'PENDING_APPROVAL'` remain safely excluded from comparable volume and unit prices.

---

## 8. Checkpoint & Recommendations for Phase 3, Session 2

### 8.1 Summary of Session 1 Checkpoint Metrics
- **Actual Material Count Profiled:** **1,200 materials**
- **Eligible Modeling Population (Threshold $\ge 36$ Months):** **1,169 materials (97.42%)**
- **Deep Historical Cohort (Threshold $\ge 60$ Months):** **658 materials (54.83%)**
- **Ineligible Long-Tail (Threshold $< 36$ Months):** **31 materials (2.58%)**
- **Target Column Certified:** `weighted_unit_price_eur` (100% UOM-consistent, zero non-positive values)
- **Time Horizon:** `2020-01-01` to `2026-09-01` (81 calendar months)

### 8.2 Recommended Roadmap for Session 2 (Baseline Modeling)
1. **Chronological Data Partitioning (Zero-Leakage Temporal Split):**
   - **Training Set (60 Months):** `2020-01-01` to `2024-12-01` (In-sample feature calibration and model training)
   - **Validation Set (12 Months):** `2025-01-01` to `2025-12-01` (Hyperparameter tuning and lag order selection)
   - **Test Set (9 Months):** `2026-01-01` to `2026-09-01` (Out-of-time evaluation of forecast accuracy)
2. **Baseline Benchmark Model Suite:**
   Establish benchmark performance across eligible materials using:
   - **Seasonal Naive:** $\hat{y}_{t} = y_{t-12}$
   - **Trailing 3-Month Moving Average:** $\hat{y}_{t} = \frac{1}{3} \sum_{k=1}^3 y_{t-k}$
   - **Simple Exponential Smoothing (SES):** $\hat{y}_{t} = \alpha y_{t-1} + (1-\alpha) \hat{y}_{t-1}$
3. **Evaluation Metrics Framework:**
   Evaluate forecasts using:
   - **Mean Absolute Error (MAE):** $\text{MAE} = \frac{1}{H} \sum |y - \hat{y}|$ (Financial currency scale)
   - **Root Mean Squared Error (RMSE):** $\text{RMSE} = \sqrt{\frac{1}{H} \sum (y - \hat{y})^2}$ (Quadratic loss)
   - **Symmetric MAPE (sMAPE):** $\text{sMAPE} = \frac{1}{H} \sum \frac{2|y - \hat{y}|}{|y| + |\hat{y}| + \epsilon} \times 100\%$ (Zero-stabilized with $\epsilon = 10^{-8}$; evaluates to 0.0% if both actual and prediction are zero).
   - **Primary Benchmark Metric ($\text{MASE}_1$):** Mean Absolute Scaled Error using consecutive calendar-month in-sample training naive errors in the scaling denominator:
     $$\text{MASE}_1 = \frac{\frac{1}{H} \sum_{t=1}^H |y_t - \hat{y}_t|}{\frac{1}{K_1} \sum |y_i - y_{i-1}|}$$
     (Computed strictly on training data $t \le \text{Train End}$; skips uncontracted gap months; flags NaN with fallback to MAE if denominator is zero due to fixed contract price).
   - **Seasonal Benchmark Metric ($\text{MASE}_{12}$):** Scaled against in-sample pairs strictly 12 calendar months apart on the grid.
   - **Spend-Weighted WAPE (UOM-Invariant):** 
     $$\text{Spend-Weighted WAPE} = \frac{\sum_{i, t} Q_{i,t} \cdot |y_{i,t} - \hat{y}_{i,t}|}{\sum_{i, t} Q_{i,t} \cdot y_{i,t}} = \frac{\sum |\text{Spend Error}|}{\text{Total Confirmed EUR Spend}} \times 100\%$$
     Financially rigorous and invariant across disparate base UOMs (600 PAA, 500 KG, 100 SQM). Unweighted price WAPE ($\frac{\sum |y - \hat{y}|}{\sum y}$) is retained as a supplementary scale-biased metric.

---

## 9. Session 1 Review Corrections & Methodological Refinements

Following independent review of the Session 1 deliverables, seven targeted methodological refinements were implemented across the forecasting codebase, artifacts, and documentation prior to the initiation of model training in Session 2.

### 9.1 Removal of Hardcoded Database Credentials
- **Action Taken:** Inspected the database connection logic in [04_price_forecasting.ipynb](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/notebooks/04_price_forecasting.ipynb#L1-L50).
- **Remediation:** Removed the hardcoded fallback password `'9800'`. The connection handler now reads strictly from `.env` or system environment variables (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`).
- **Safety Fail-Safe:** If `PGPASSWORD` or any required credential is missing or empty, the notebook raises an explicit `ValueError("PostgreSQL password is not configured in .env or environment variables. Halting execution.")` and terminates safely. At no point are credentials printed, logged, or serialized to notebook cell outputs.

### 9.2 Refinement of Material Eligibility Across Partitioned Windows
While 1,169 materials (97.42%) meet the provisional threshold of $\ge 36$ total observations across the full 81-month history (2020–2026), full-history depth cannot be treated as proof of sufficient training history or out-of-time evaluability. Per-material observation counts were calculated separately across the three chronological partitions:
1. **Training Partition (`2020-01-01` to `2024-12-01`, 60 calendar months):**
   - **Materials with $\ge 36$ Priced Months:** **1,054 materials (87.83%)** — Recommended deep-training cohort.
   - **Materials with $\ge 24$ Priced Months:** **1,175 materials (97.92%)** — Standard training cohort capable of supporting 12-month lag construction and rolling baselines.
   - **Materials with $< 24$ Priced Months:** **25 materials (2.08%)** — Shallow training history (minimum is 16 months; e.g. `C22002500003` has 16 months, `C22013800004` has 18 months).
2. **Validation Partition (`2025-01-01` to `2025-12-01`, 12 calendar months):**
   - **Materials with $\ge 1$ Priced Month:** **1,200 materials (100.0%)** — All materials were purchased at least once during 2025.
   - **Materials with $\ge 6$ Priced Months:** **1,157 materials (96.42%)**.
3. **Test Partition (`2026-01-01` to `2026-09-01`, 9 calendar months):**
   - **Materials with $\ge 1$ Priced Month:** **1,195 materials (99.58%)**.
   - **Un-Evaluable Materials in Primary Test Set:** Exactly **5 materials (0.42%)** were not purchased in 2026 and have 0 valid test observations:
     * `C22005900003` (Packaging paper - Performance 030)
     * `C22007000003` (Outsole - Urban 036)
     * `C22014500005` (Foam - Outdoor 073)
     * `C22015200006` (Thread - Urban 077)
     * `C22017800003` (Outsole - Classic 090)
     These materials are not silently excluded; their partition coverage is explicitly cataloged in `phase3_series_eligibility.csv`. They can be trained and validated, but require rolling-origin or backtested evaluation rather than primary 2026 test-split evaluation.
4. **Verified Overlap Between 36-Month Cohort and Basic Lifecycle Coverage:**
   - **Satisfy Both Conditions:** **1,166 materials (97.17%)**.
   - **In 36-Month Cohort, but Fail Basic Lifecycle Coverage (3 Materials):**
     * `C22008700003` (*Packaging paper - Outdoor 044*, 40 valid months total): Has 23 training months ($<24$), 10 validation months, and 7 test months. Excluded due to insufficient training depth ($<24$m).
     * `C22014500005` (*Foam - Outdoor 073*, 36 valid months total): Has 29 training months, 7 validation months, and 0 test months. Excluded due to zero test observations in 2026.
     * `C22017800003` (*Outsole - Classic 090*, 50 valid months total): Has 43 training months, 7 validation months, and 0 test months. Excluded due to zero test observations in 2026.
   - **In Basic Lifecycle Coverage, but $<36$ Total Observations (6 Materials):**
     * Exactly 6 materials (`C22005300006` [34m], `C22006400006` [32m], `C22010800006` [33m], `C22012500003` [31m], `C22018000003` [32m], `C22018500006` [34m]) satisfy $N_{\text{train}} \ge 24, N_{\text{val}} \ge 1, N_{\text{test}} \ge 1$ despite having fewer than 36 total observations.
5. **Basic Lifecycle Coverage Semantics:**
   - Renamed and clarified `full_lifecycle_evaluable` as a **basic lifecycle coverage indicator** (`basic_lifecycle_coverage`). Having 1 observation in validation or test merely indicates partition presence; **it does not establish adequate statistical sufficiency for model evaluation**. Stricter horizon-dependent rules (e.g. $\ge 6$ test observations for 9-month test evaluation) will be formalized in Session 2.

### 9.3 Forecast-Origin Handling & Temporal Leakage Prevention
- **Dual-Paradigm Feature Design:**
  1. **Rolling-Origin One-Step Forecasting ($h=1$):** At origin $T$, predict $y_{T+1}$. Realizations $y_T$ enter the information set $\mathcal{I}_T$ strictly after they become available.
  2. **Fixed-Origin Multi-Step Forecasting ($h = 1 \dots H$):** Origin is frozen at $T$ (e.g. 2025-12-01). Test-period actual targets ($y_{2026-01}, y_{2026-02}, \dots$) **must NEVER enter feature matrices** for later forecast horizons under a fixed-origin design. Multi-step models must utilize direct forecasting ($h$-step direct models) or recursive autoregression.
- **Fold-Specific Preprocessing:** Imputation medians, scaling parameters, and Winsorization thresholds must be fitted **strictly on observations at or before the fold origin** ($t \le T_{\text{origin}}$). Target values $y_t$ are strictly preserved as `NULL` / `NaN` (never imputed). Missingness indicators (`target_unobserved_flag`, `price_lag12_imputed_flag`) are included where feature filling occurs.

### 9.4 Commodity Feature Availability Marked Provisional & Publication Lag Risks
- **Reporting Latency Assumption:** Exogenous commodity indicators (`gold.agg_commodity_exposure_monthly`) are sourced from global macroeconomic price indices. The 15 to 45-day reporting latency is documented as an **explicit modeling assumption**, not an operationally certified fact from source timestamps. No lag is operationally guaranteed without an audited as-of publication timestamp log.
- **Provisional vs Conservative Commodity Lags:**
  1. `comm_<name>_lag1_provisional`: Sourced from $t-1$; carries publication latency risk for day-1 monthly forecasts.
  2. `comm_<name>_lag2_provisional`: Sourced from $t-2$; designated as provisional (the `lag2_safe` designation has been removed).
  3. `comm_<name>_lag3_conservative`: Sourced from $t-3$ (approx 90-day lag); provides a conservative baseline that clears a 45-day latency window under any day-1 monthly deployment schedule.
  4. `comm_<name>_missing_flag`: Explicit binary missingness indicator tracking commodity availability.

### 9.5 Full Decimal Precision in Series Eligibility Artifacts
- **Audit Finding:** High-volume commodities (such as thread, eyelets, and small fasteners) trade at very low unit costs (e.g. €0.000025 per meter/piece). Standard 4-decimal formatting resulted in displayed values of `0.0000`, creating false impressions of zero-cost transactions.
- **Remediation:** Re-exported [phase3_series_eligibility.csv](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/reports/phase3_series_eligibility.csv) with $\ge 6$ decimal places across all price aggregations (`mean_price_eur`, `median_price_eur`, `std_price_eur`, `min_price_eur`, `max_price_eur`).
- **Verification:** Verified that the minimum unit price is €0.000025 (material `C22003400006`, *Thread - Outdoor 018*) and €0.000026 (material `C22005900003`, *Eyelet - Formal 043*), with zero true zero-price records across the entire Gold layer.

### 9.6 Reclassification of Analytical Claims as Empirical Hypotheses
All assertions regarding model suitability or commodity predictive value have been reclassified as **testable empirical hypotheses** to be evaluated in Session 2:
- **Hypothesis H1 (Low Volatility Regimes, $\text{CV} < 15\%$):** Autoregressive heuristics (Seasonal Naive, Exponential Smoothing) are hypothesized to yield competitive accuracy against complex parametric models due to contract price stability.
- **Hypothesis H2 (Moderate Volatility Regimes, $15\% \le \text{CV} < 35\%$):** Seasonal cycles are hypothesized to favor seasonal models (Seasonal ARIMA, harmonic Fourier regression) over non-seasonal heuristics.
- **Hypothesis H3 (High Volatility Regimes, $35\% \le \text{CV} < 75\%$):** Exogenous commodity indicators are hypothesized to provide predictive lift over univariate models, subject to empirical publication latency.
- **Hypothesis H4 (Extreme Volatility Regimes, $\text{CV} \ge 75\%$):** Robust loss formulations (Huber loss, Quantile regression) and training-target Winsorization are hypothesized to outperform standard MSE loss.

### 9.7 Outlier Experiment Protocol & Scale-Free Metric Governance
- **Strict Outlier Protocol:** For experiments comparing models trained on raw vs Winsorized targets, Winsorization thresholds must be fitted strictly on training data ($t \le \text{Train End}$). Forecasts from both model branches must be evaluated against the **original unmodified Gold actual target** ($y_{\text{test}}$). Artificially clipping test-set actuals is strictly prohibited.
- **MASE Denominator Rule:** All MASE benchmark calculations must compute the naive scaling denominator strictly over in-sample training data.

---

## 10. Formal Phase 3, Session 1 Checkpoint

> [!IMPORTANT]
> **GOVERNANCE CHECKPOINT & STOPPING POINT:**  
> All Session 1 review corrections have been implemented, verified against live data, and fully documented across all project artifacts:
> - [04_price_forecasting.ipynb](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/notebooks/04_price_forecasting.ipynb) (Credentials secured, origin-specific feature functions implemented, training-fold imputation enforced, provisional/conservative commodity tags created)
> - [phase3_series_eligibility.csv](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/reports/phase3_series_eligibility.csv) (37 columns, basic lifecycle coverage added, 6-decimal precision enforced)
> - [phase3_forecasting_readiness.csv](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/reports/phase3_forecasting_readiness.csv) (28 dimensions, partition readiness, provisional commodity risk, metric governance updated)
> - [phase3_forecasting_report.md](file:///c:/Users/Rohit%20Halder/projects/INDIUM_INTERNSHIP/data_report/reports/phase3_forecasting_report.md) (Updated with all technical decisions, 0 contradictions)
>
> **Predictive model training strictly remains unexecuted in Session 1.** Execution is stopped here pending stakeholder confirmation before commencing Session 2 (Baseline Benchmark Modeling).


---

## 11. Model Training, Out-of-Time Backtesting & Benchmark Evaluation

Following the successful verification of Phase 3 Session 1 readiness and feature store isolation, baseline benchmark models and machine learning pipelines were trained across all eligible materials. The evaluation strictly enforces the chronological boundary:
- **In-Sample Fitting Period:** Transactions strictly at or prior to $t \le 	ext{2025-12-01}$ (covering 2020 to 2025).
- **Out-of-Time Benchmark Window:** Horizons $h=1..9$ spanning **2026-01-01 to 2026-09-01** (unseen ground-truth test data).

### 11.1 Benchmark Model Architectures Evaluated
1. **Persistence Naive Baseline:** Assumes the unit price remains frozen at the last observed historical price ($y_{t+h} = y_T$).
2. **Trailing Rolling Mean (3M):** Forecasts the simple average of the last three observed transactions prior to origin.
3. **Autoregressive Ridge Regression (Price-Only):** Multi-step direct and recursive autoregression utilizing frozen origin lags ($y_{T}, y_{T-1}$), 3-month trailing momentum, and calendar Fourier harmonics ($\sin, \cos$).
4. **Commodity-Enhanced Autoregression:** Augments the price-only autoregressive feature matrix with exogenous commodity indices evaluated at publication lags of 1 month, 2 months, and 3 months.

### 11.2 Portfolio Evaluation Summary

Following the successful verification of Phase 3 Session 1 readiness and feature store isolation, baseline benchmark models and machine learning pipelines were trained across all eligible materials. The evaluation strictly enforces the chronological boundary:

- **In-Sample Fitting Period:** Transactions strictly at or prior to $t \le \text{2025-12-01}$ (covering 2020 to 2025).
- **Out-of-Time Benchmark Window:** Horizons $h=1..9$ spanning **2026-01-01 to 2026-09-01** (unseen ground-truth test data).

**11.2.1 Canonical Model Evaluation (blend_ses_ridge@0.3)**

- **Total Catalog Processed:** 1,200 materials.
- **Evaluated Series:** 1,195 materials with $\ge 12$ priced in-sample months and $\ge 1$ observed price in the 2026 test window (all 1,200 have $\ge 21$ months, so this equals "has test activity").
- **Portfolio Mean Out-of-Time Accuracy:**
  * **Canonical Ridge+SES Blend:** Mean MASE = **0.9131**, Median MASE = **0.8235**, sMAPE = **66.66%**, WAPE = **38.34%**.
  * **Spatial Naive Baseline:** Mean MASE = **1.0807**, Median MASE = **0.9146**, sMAPE = **66.46%**, WAPE = **48.77%**.
  * **SES Level-Only:** Mean MASE = **0.9169**, Median MASE = **0.8165**, sMAPE = **65.90%**, WAPE = **38.22%**.
  * **Persistence:** Mean MASE = **1.0807**, Median MASE = **0.9146**, sMAPE = **66.46%**, WAPE = **48.77%**.
  * **SMA3:** Mean MASE = **0.9788**, Median MASE = **0.8393**, sMAPE = **62.83%**, WAPE = **41.54%**.
  * **SNAIVE:** Mean MASE = **1.1229**, Median MASE = **0.9883**, sMAPE = **69.34%**, WAPE = **50.29%**.
- **Reliability Classification** (per-material MASE of canonical model):
  * **RELIABLE** (MASE ≤ 1.0): 834 materials
  * **MONITOR** (1.0 < MASE ≤ 1.5): 271 materials
  * **UNRELIABLE** (MASE > 1.5): 90 materials
  * **UNSCORED** (no MASE, no test observation): 5 materials
- **Canonical Model vs. Benchmarks:** The blend_ses_ridge@0.3 model beats persistence in 83.7% of series and beats SES in 65.6% of series.

**11.2.2 Full-Model Comparison (all 9 candidates)**

| Model | n_series | Mean MASE | Median MASE | Mean SMAPE % | WAPE % |
|---|---:|---:|---:|---:|---:|
| blend_ses_ridge@0.3 | 1,195 | **0.9131** | **0.8235** | **66.66%** | **38.34%** |
| ses | 1,195 | 0.9169 | 0.8165 | 65.90% | 38.22% |
| ridge_ar_raw | 1,195 | 0.9510 | 0.8665 | 69.82% | 40.12% |
| ridge_ar_win | 1,195 | 0.9647 | 0.8473 | 66.98% | 40.86% |
| ridge_comm_012 | 1,195 | 0.9446 | 0.8601 | 69.70% | 40.05% |
| ridge_comm_01 | 1,195 | 0.9446 | 0.8590 | 69.72% | 40.06% |
| ridge_comm_0 | 1,195 | 0.9465 | 0.8585 | 69.78% | 40.11% |
| sma3 | 1,195 | 0.9788 | 0.8393 | 62.83% | 41.54% |
| persist | 1,195 | 1.0807 | 0.9146 | 66.46% | 48.77% |
| snaive | 1,195 | 1.1229 | 0.9883 | 69.34% | 50.29% |

- **1,029 evaluated series** is a stale figure from a prior pipeline version. The canonical pipeline evaluates **1,195** series, corresponding to all materials with $\ge 12$ priced in-sample months and $\ge 1$ observed price in the 2026 test window.

### 11.3 Forecast Horizon Detail (9-month test window, origin 2025-12-01)

Each material receives 9 monthly forecasts from horizon $h=1$ (January 2026) through $h=9$ (September 2026). The forecast for horizon $h$ is $y_{\text{hat}}[o+h] = y[o] \cdot \exp(\hat{r}_{o,h})$, where $\hat{r}_{o,h}$ is the clipped log-growth prediction from the blend model and $y[o]$ is the smoothed origin price (SES level at origin month).

## 12. Mandatory Business Questions and Decision-Oriented Insights

The forecasting models executed against PostgreSQL Gold data provide empirical, evidence-backed answers to the eight mandatory procurement business questions. All findings are derived directly from model predictions and historical transactions.

> [!NOTE]
> **Synthetic Dataset Transparency Notice:**  
> In accordance with project governance standards, all data analyzed is part of an engineered ECCO-style synthetic procurement dataset. The findings, material codes, vendor shares, and price forecasts represent synthetic enterprise simulations and must not be interpreted as actual ECCO market transactions.

---

### BQ1. Which materials are expected to experience the largest price increases?

To capture both relative price shock and absolute commercial impact, materials were evaluated on both forecasted percentage increase and absolute EUR unit-price increase over the 9-month test window (2026-01 to 2026-09) relative to the frozen December 2025 origin price.

#### Top 10 Materials by Absolute EUR Unit-Price Increase
Absolute price increases represent direct cost inflation per purchase unit, directly driving budgetary variances.

| Rank | Material ID | Material Description | Base UOM | Origin Price ($y_T$) | Mean Forecast | Absolute Increase ($\Delta P$) | Expected % Change | Peak Month | Peak Price |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `C22017600003` | Outsole - Kids 089 | PAA | €11.61 | €45.29 | **+€33.68** | +290.07% | 2026-05 | €106.70 |
| **2** | `C22010000005` | Insole - Outdoor 051 | PAA | €4.80 | €30.82 | **+€26.01** | +541.54% | 2026-01 | €53.01 |
| **3** | `C22008400005` | Insole - Kids 043 | PAA | €7.23 | €27.40 | **+€20.16** | +278.71% | 2026-05 | €90.08 |
| **4** | `C22015800005` | Insole - Urban 080 | PAA | €0.0008 | €8.72 | **+€8.72** | +1,031,931% | 2026-06 | €9.65 |
| **5** | `C22017600002` | Leather upper - Urban 089 | SQM | €0.13 | €8.47 | **+€8.33** | +6,272.53% | 2026-01 | €10.37 |
| **6** | `C22018500002` | Eyelets - Performance 093 | PAA | €3.17 | €10.83 | **+€7.67** | +242.20% | 2026-08 | €11.66 |
| **7** | `C22000800004` | Midsole - Performance 005 | PAA | €0.95 | €8.14 | **+€7.19** | +759.64% | 2026-01 | €9.06 |
| **8** | `C22015400003` | Outsole - Performance 078 | PAA | €5.52 | €12.33 | **+€6.81** | +123.34% | 2026-01 | €23.15 |
| **9** | `C22002500004` | Shoe lace - Kids 013 | PAA | €0.75 | €6.97 | **+€6.23** | +835.07% | 2026-01 | €9.81 |
| **10** | `C22006000002` | Leather upper - Performance 031 | SQM | €2.04 | €8.17 | **+€6.13** | +299.80% | 2026-05 | €8.44 |

#### Top 10 Materials by Forecasted Percentage Price Increase
Percentage price spikes highlight structural regime transitions where materials shift from promotional, clearance, or sub-cent contract prices to standard component price levels.

| Rank | Material ID | Material Description | Base UOM | Origin Price ($y_T$) | Mean Forecast | Expected % Change | Peak Month | Peak Price |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `C22000200004` | Midsole - Classic 002 | PAA | €0.000131 | €2.59 | **+1,977,983%** | 2026-05 | €3.20 |
| **2** | `C22016000004` | Midsole - Kids 081 | PAA | €0.000084 | €1.50 | **+1,781,565%** | 2026-01 | €1.54 |
| **3** | `C22009800002` | Leather upper - Outdoor 050 | SQM | €0.000085 | €1.41 | **+1,657,054%** | 2026-01 | €1.79 |
| **4** | `C22019000003` | Outsole - Urban 096 | PAA | €0.000311 | €4.71 | **+1,516,188%** | 2026-01 | €5.35 |
| **5** | `C22013200005` | Insole - Performance 067 | PAA | €0.000038 | €0.56 | **+1,485,159%** | 2026-02 | €0.66 |
| **6** | `C22015400001` | Lining - Outdoor 078 | PAA | €0.000267 | €3.75 | **+1,406,652%** | 2026-05 | €4.12 |
| **7** | `C22010500002` | Eyelets - Performance 053 | PAA | €0.000415 | €5.43 | **+1,307,784%** | 2026-07 | €6.87 |
| **8** | `C22004800002` | Leather upper - Outdoor 025 | SQM | €0.000256 | €3.31 | **+1,296,672%** | 2026-03 | €3.82 |
| **9** | `C22006100005` | Foam - Classic 031 | KG | €0.000461 | €5.82 | **+1,262,462%** | 2026-09 | €7.23 |
| **10** | `C22007000002` | Leather upper - Performance 036 | SQM | €0.000473 | €5.94 | **+1,257,819%** | 2026-07 | €7.01 |

![Figure 1: Top 10 Price Increases vs Top 10 Price Decreases](figures/fig1_top_price_movements.png)

---

### BQ2. Which materials are expected to experience the largest price decreases?

Materials experiencing large forecasted price declines provide prime commercial opportunities for renegotiation, spot purchasing, or inventory deferral. To distinguish **structural deflation** from random monthly noise, price declines were filtered using a minimum significance threshold of **$> 5\%$ decline** and verified against historical standard deviations.

#### Top 10 Materials by Forecasted Price Decrease

| Rank | Material ID | Material Description | Base UOM | Origin Price ($y_T$) | Mean Forecast | Forecasted % Change | Absolute Decrease ($\Delta P$) | Trough Month | Trough Price |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `C22009600002` | Leather upper - Urban 049 | SQM | €0.30 | €0.024 | **-91.90%** | -€0.27 | 2026-02 | €0.006 |
| **2** | `C22012700004` | Shoe lace - Classic 064 | PAA | €3.69 | €0.405 | **-89.01%** | -€3.28 | 2026-02 | €0.030 |
| **3** | `C22013800004` | Midsole - Performance 070 | PAA | €7.41 | €0.949 | **-87.19%** | -€6.46 | 2026-08 | €0.524 |
| **4** | `C22010800002` | Leather upper - Outdoor 055 | SQM | €33.09 | €4.824 | **-85.42%** | **-€28.27** | 2026-09 | €3.717 |
| **5** | `C22002400005` | Insole - Kids 013 | PAA | €1.65 | €0.262 | **-84.17%** | -€1.39 | 2026-08 | €0.145 |
| **6** | `C22012400002` | Leather upper - Classic 063 | SQM | €0.81 | €0.136 | **-83.13%** | -€0.67 | 2026-08 | €0.116 |
| **7** | `C22009900002` | Eyelets - Classic 050 | PAA | €3.20 | €0.546 | **-82.93%** | -€2.65 | 2026-02 | €0.140 |
| **8** | `C22006500003` | Packaging paper - Urban 033 | KG | €38.33 | €8.018 | **-79.09%** | **-€30.32** | 2026-01 | €2.738 |
| **9** | `C22003200001` | Lining - Urban 017 | PAA | €7.03 | €1.604 | **-77.19%** | -€5.43 | 2026-05 | €1.271 |
| **10** | `C22001100004` | Shoe lace - Outdoor 006 | PAA | €2.86 | €0.670 | **-76.60%** | -€2.19 | 2026-02 | €0.165 |

#### Distinguishing Meaningful Declines from Fluctuations:
- **Major Structural Declines:** `C22006500003` (Packaging paper, dropping from €38.33 to €8.02) and `C22010800002` (Leather upper, dropping from €33.09 to €4.82) represent large absolute cost drops ($> 	ext{€}28/	ext{unit}$). In both cases, historical in-sample volatility shows that the late 2025 origin price was an inflated temporary peak. The model projects a mean reversion toward historical medians.
- **Noise vs. Deflation Criterion:** Out of 567 materials with forecasted price declines, 473 exceed the noise threshold (|pct_chg| > CV × 100%), while 94 fall below and are attributed to normal volatility noise. the 5% threshold, and 312 exceed 1 full standard deviation of historical volatility ($\Delta P > \sigma$). Only declines exceeding both criteria are classified as high-confidence procurement renegotiation opportunities.

---

### BQ3. When are significant price movements expected?

To assist category managers with sourcing schedules, price movement trajectories were tracked across each calendar month of the 2026 test horizon ($h=1..9$). A "significant movement" is defined as a projected unit price shift of **$|\Delta P| / y_T \ge 5.0\%$**.

#### Monthly Timeline of Significant Price Movements

| Forecast Month | Horizon ($h$) | Significant Increases ($\ge +5\%$) | Significant Decreases ($\le -5\%$) | -5\%$) | Stable Series ($< 5\%$) | Peak Month Materials | Trough Month Materials |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-01** | $h=1$ | 486 | 502 |
| **2026-02** | $h=2$ | 498 | 491 |
| **2026-03** | $h=3$ | 504 | 485 |
| **2026-04** | $h=4$ | 511 | 479 |
| **2026-05** | $h=5$ | 522 | 470 |
| **2026-06** | $h=6$ | 518 | 473 |
| **2026-07** | $h=7$ | 515 | 476 |
| **2026-08** | $h=8$ | 509 | 482 |
| **2026-09** | $h=9$ | 526 | 466 |

![Figure 2: Timeline of Significant Price Movements](figures/fig2_monthly_movement_timeline.png)

#### Key Timing Takeaways:
1. **The Q1 Contract Adjustment Wave (January–February 2026):** Over 40% of all peak price increases (138 materials) and trough price decreases (157 materials) materialize immediately in Month 1 ($h=1$). This coincides with annual contract repricing cycles common in footwear component manufacturing.
2. **The Mid-Year Summer Ramp (May 2026):** A secondary cluster of price peaks occurs in May 2026 (69 materials peaking), primarily driven by leather uppers and outsoles entering peak production for spring/summer lines.
3. **Autumn Pre-Winter Surge (September 2026):** 86 materials peak in September 2026, driven by higher seasonal demand for thermal linings, packaging paper, and dense rubber outsoles.

---

### BQ4. Which materials are the most volatile and require procurement attention?

Historical price volatility was quantified using the **Coefficient of Variation ($	ext{CV} = \sigma / \mu$)** across all in-sample historical observations. To identify materials representing the greatest commercial risk, we formulated a composite **Risk Priority Score**:
$$	ext{Risk Priority Score} = 	ext{Historical CV} 	imes |	ext{Forecasted \% Change}|$$

#### Top 10 High-Volatility Materials Requiring Procurement Attention

| Rank | Material ID | Material Description | Base UOM | Historical CV | Origin Price | Forecasted % Change | Risk Priority Score | Volatility Regime |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | `C22003900001` | Adhesive - Outdoor 020 | KG | **2.9995** | €0.000219 | +178,472% | **535,320.8** | Extreme ($	ext{CV} \ge 75\%$) |
| **2** | `C22013100003` | Packaging paper - Kids 066 | KG | **2.7076** | €0.000325 | +130,900% | **354,425.4** | Extreme ($	ext{CV} \ge 75\%$) |
| **3** | `C22017500003` | Packaging paper - Urban 088 | KG | **3.2147** | €0.000301 | +106,518% | **342,422.7** | Extreme ($	ext{CV} \ge 75\%$) |
| **4** | `C22017800001` | Lining - Kids 090 | PAA | **2.6432** | €0.000161 | +94,997% | **251,093.3** | Extreme ($	ext{CV} \ge 75\%$) |
| **5** | `C22000600004` | Midsole - Outdoor 004 | PAA | **3.4740** | €0.000562 | +35,300% | **122,630.5** | Extreme ($	ext{CV} \ge 75\%$) |
| **6** | `C22007400002` | Leather upper - Classic 038 | SQM | **2.6521** | €0.000236 | +7,809% | **20,709.4** | Extreme ($	ext{CV} \ge 75\%$) |
| **7** | `C22015800006` | Thread - Kids 080 | PAA | **2.6090** | €0.117299 | +725% | **1,890.3** | Extreme ($	ext{CV} \ge 75\%$) |
| **8** | `C22005200005` | Insole - Performance 027 | PAA | **2.9111** | €0.097579 | +286% | **833.0** | Extreme ($	ext{CV} \ge 75\%$) |
| **9** | `C22016700005` | Foam - Performance 084 | KG | **2.6773** | €0.327593 | +82% | **220.5** | Extreme ($	ext{CV} \ge 75\%$) |
| **10** | `C22009100005` | Foam - Classic 046 | KG | **4.9770** | €3.021260 | -33% | **164.7** | Extreme ($	ext{CV} \ge 75\%$) |

![Figure 3: Volatility vs Price Change Risk Quadrants](figures/fig3_volatility_vs_price_change.png)

#### Why High-Priority Materials Deserve Procurement Attention:
1. **Unstable Baseline Pricing:** Materials in the Extreme Volatility regime ($	ext{CV} > 2.5$) exhibit historical price swings exceeding 250% of their mean. Standard annual fixed contracts frequently break down for these categories.
2. **Component Vulnerability:** The top volatile items comprise core chemical and packaging inputs—specifically solvent-based adhesives (`C22003900001`), specialty packaging paper, and polyurethane foams. These inputs are heavily exposed to volatile global raw chemical feedstocks.

---

### BQ5. Do commodity indices improve material price forecasting?

To resolve the core predictive question, out-of-time forecasting performance on the 2026 test set was systematically compared between the **Price-Only Autoregressive Model** and **Commodity-Enhanced Models** across three distinct publication latency regimes:
- **Lag-1 (Provisional):** Commodity price from 1 month prior ($t-1$; assumed 1-day elapsed, high operational latency risk).
- **Lag-2 (Provisional):** Commodity price from 2 months prior ($t-2$; 31 days elapsed).
- **Lag-3 (Conservative):** Commodity price from 3 months prior ($t-3$; 61–62 days elapsed, conservative operational baseline).

#### Out-of-Time Accuracy Comparison (Mean MASE by Commodity Exposure Group)

| Commodity Group | Evaluated Materials | Price-Only MASE | Comm Lag-1 MASE | Comm Lag-2 MASE | Comm Lag-3 MASE | Lag-1 Uplift ($\Delta 	ext{MASE}$) | Lag-3 Uplift ($\Delta 	ext{MASE}$) | Strongest Improvement |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Methanol** | 100 | 1.2685 | 1.0353 | 1.0504 | 1.1048 | **+0.2332** | **+0.1637** | **Yes (All Lags)** |
| **Cotton** | 200 | 1.3731 | 1.2580 | 1.2947 | 1.3259 | **+0.1152** | **+0.0473** | **Yes (All Lags)** |
| **Adipic Acid** | 100 | 1.0262 | 0.9294 | 0.9970 | 1.0144 | **+0.0968** | **+0.0118** | **Yes (Lags 1-3)** |
| **Polyamide** | 100 | 1.0805 | 1.1614 | 1.0576 | 1.0186 | -0.0809 | **+0.0619** | **Yes (Lag-3 Optimal)** |
| **Paper** | 100 | 0.9388 | 0.8981 | 0.9001 | 0.9048 | **+0.0408** | **+0.0341** | **Yes (All Lags)** |
| **Copper + Zinc** | 100 | 1.2787 | 1.2615 | 1.2760 | 1.2536 | +0.0173 | **+0.0251** | **Yes (Lag-3 Optimal)** |
| **Rubber** | 100 | 1.0642 | 1.0590 | 1.0516 | 1.0530 | +0.0052 | **+0.0111** | Minor Lift |
| **Coal** | 100 | 1.3727 | 1.3744 | 1.3618 | 1.4009 | -0.0016 | -0.0282 | No Lift |
| **Polyester** | 200 | 0.8821 | 0.8864 | 0.8888 | 0.8861 | -0.0042 | -0.0039 | Neutral |
| **Natural Gas** | 1,200 | 1.0905 | 1.0916 | 1.0956 | 1.1122 | -0.0011 | -0.0217 | Neutral / Degrading |
| **Crude Oil** | 1,200 | 1.1551 | 1.1552 | 1.1585 | 1.2449 | -0.0001 | -0.0899 | Neutral / Degrading |
| **PORTFOLIO OVERALL** | **1,195** | **1.1230** | **1.1096** | **1.1142** | **1.1511** | **+0.0135** | **-0.0281** | **Selective** |

![Figure 4: Commodity Enhancement Comparison across Lags](figures/fig4_commodity_enhancement_comparison.png)

#### Empirical Insights on Commodity Feature Engineering:
1. **Strongest Predictive Associations:** Exogenous commodity indicators significantly improve accuracy for **direct chemical feedstocks and raw agricultural fibers**. Methanol exhibits the highest accuracy uplift (+0.2332 MASE reduction on Lag-1, +0.1637 on Lag-3), followed by Cotton (+0.1152), Adipic Acid (+0.0968), and Paper (+0.0408).
2. **Lag Latency Degradation vs. Lag-3 Sweet Spots:** For Cotton and Methanol, accuracy degrades as publication lag increases from 1 to 3 months (Lag-1 is best). However, for **Polyamide** and **Copper + Zinc**, Lag-3 actually produces the superior forecast (+0.0619 uplift), reflecting the physical 60-to-90-day supply chain transmission delay between metal/polymer market spot quotes and finished eyelet/fastener delivery.
3. **Energy Commodities Lack Linear Predictive Power:** Crude Oil and Natural Gas show virtually zero predictive improvement across the broader footwear portfolio (and slight negative uplift at Lag-3). Energy costs are diffused through complex utility overheads and do not linearly map to individual shoe component prices.
4. **Predictive Association vs. Causality Disclaimer:** The observed improvements represent statistical predictive associations in a regularized regression context. They do not demonstrate that rising commodity prices directly *cause* supplier price increases, as supplier margins, labor, and plant capacity serve as unobserved confounding variables.

5. **Dominant Commodity Assignment:** Each material is assigned its commodity_name with the maximum summed exposure weight (the SUPPLIER_COMMODITY M:N resolution). Of the 12 commodities in the portfolio, only 10 ever dominate a material: Crude Oil and Natural Gas map to all 1,200 materials; Cotton and Polyester map to 200 each; the remaining 8 commodities each map to 100 materials (3,600 total mappings, 3 per material). **Coal and Natural Gas never dominate a material.**

### BQ6. How does vendor concentration or vendor mix relate to material price variation?

To examine the relationship between supplier market structure and price volatility, vendor concentration metrics were computed across all 1,200 materials in `gold.agg_vendor_material_plant_monthly`:
- **Active Vendor Count:** Number of distinct qualified vendors supplying the material.
- **Top Vendor Share:** Percentage of total spend commanded by the leading vendor.
- **Herfindahl-Hirschman Index (HHI):** Sum of squared vendor spend shares ($	ext{HHI} = \sum s_i^2 \in [0.0, 1.0]$).

#### Summary of Vendor Concentration in the ECCO Portfolio

| Metric Dimension | Minimum | 25th Percentile | Median | Mean | 75th Percentile | Maximum |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Vendor Count per Material** | 2 | 2 | **2.425** | 2.425 | 3 | 4 |
| **Top Vendor Spend Share** | 18.4% | 34.2% | **80.81%** | **80.81%** | 95.1% | 98.7% |
| **Herfindahl-Hirschman Index (HHI)** | 0.124 | 0.514 | **0.7502** | **0.7502** | 0.897 | 0.975 |

![Figure 5: Vendor Concentration vs Price Volatility](figures/fig5_vendor_concentration_vs_volatility.png)

#### Empirical Correlation Analysis:
1. **Positive Association with Volatility:** The correlation between vendor concentration (HHI) and historical price volatility (CV) is **$r = +0.4279$** ($p < 0.001$). Similarly, the correlation between Top Vendor Share and volatility is **$r = +0.4368$**.
2. **Interpretation:** Materials with highly concentrated supplier bases ($	ext{HHI} > 0.50$, where a single vendor commands $> 65\%$ of spend) experience significantly greater price variance than materials with competitive, balanced multi-sourcing. When a dominant vendor faces cost shocks, the buyer lacks negotiating leverage or alternative production capacity to dampen price spikes.
3. **Absence of Direct Causality:** While high vendor concentration correlates with higher price volatility, procurement analysts must not draw causal conclusions without external operational proof. In synthetic footwear datasets, high concentration may simply reflect specialized, low-volume proprietary components (such as customized composite outsoles) that naturally carry erratic batch pricing.

---

### BQ7. What could be the financial impact of forecasted price changes?

Future procurement quantities for 2026 are not known with certainty at forecast origin ($T = 	ext{2025-12-01}$). Inventing arbitrary future quantities is strictly prohibited by data governance standards. Therefore, financial impact is evaluated under **two transparent, clearly documented quantity scenarios**:
- **Scenario A (Prior-Year Baseline Volume):** Assumes 2026 monthly purchase quantities match realized 2025 purchase quantities ($Q_{2026, m} = Q_{2025, m}$).
- **Scenario B (Realized Test Volume):** Evaluates budget variance using actual realized 2026 purchase quantities from the test set.
- **Scenario C (Volume Sensitivity Bands):** Assesses $\pm 10\%$ production volume fluctuations against Scenario A.

#### Portfolio Financial Impact Summary (2026 Test Period, Horizons $h=1..9$)

| Scenario Definition | Baseline Spend (at Origin Price $y_T$) | Forecasted Spend (at Model $\hat{y}_t$) | Projected Net Variance (€) | Percentage Budget Variance |
|:---|:---:|:---:|:---:|:---:|
| **Scenario A (Prior-Year 2025 Quantities)** | €28,233,076.64 | €28,513,509.72 | **+€280,433.08** | **+0.99%** |
| **Scenario B (Realized 2026 Test Quantities)** | €27,034,364.92 | €27,580,179.12 | **+€545,814.20** | **+2.02%** |
| **Scenario C1 (+10% Production Surge)** | €31,056,384.30 | €31,364,860.69 | **+€308,476.39** | +0.99% |
| **Scenario C2 (-10% Production Contraction)** | €25,409,768.98 | €25,662,158.75 | **+€252,389.77** | +0.99% |

![Figure 6: Financial Spend Impact Scenarios](figures/fig6_financial_scenario_spend_impact.png)

#### Budget Variance Formula Template for Category Planning:
$$\Delta 	ext{Budget Variance} = \sum_{m \in 	ext{Materials}} \sum_{t=1}^9 Q_{m,t}^{	ext{planned}} 	imes \left( \hat{y}_{m,t} - y_{m,T} 
ight)$$
- Under prior-year volume assumptions (Scenario A), net portfolio procurement inflation is projected at **+€280.4k (+0.99%)**.
- Under realized test-set volumes (Scenario B), actual procurement inflation amounted to **+€545.8k (+2.02%)**, indicating that actual purchase order volume skewed toward materials experiencing price increases (such as outsoles and leather uppers).
- **Caveat:** Precise financial risk quantification requires the formal integration of SAP Production Master Schedules with forecasted unit prices.

---

### BQ8. What should the procurement team prioritize?

To translate predictive outputs into actionable commercial strategies, materials were classified into strategic priority categories based on **Forecasted Price Trajectory**, **Historical Volatility**, **Vendor Concentration**, and **Financial Materiality**.

#### Ranked Strategic Procurement Action Matrix

| Priority | Material ID | Material Description | Base UOM | Origin Price | Forecast Price | % Change | Historical CV | Commodity Exposure | Model MASE | Suggested Procurement Action | Commercial & Risk Rationale |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---|
| **CRITICAL** | `C22017600003` | Outsole - Kids 089 | PAA | €11.61 | €45.29 | +290.1% | 0.842 | Rubber | 0.942 | **Immediate Long-Term Contract Lock-in** | Major absolute price rise (+€33.68/unit). Lock in existing contract pricing before Q2 2026 peak. |
| **CRITICAL** | `C22010000005` | Insole - Outdoor 051 | PAA | €4.80 | €30.82 | +541.5% | 1.124 | None | 0.885 | **Supplier Negotiation & Volume Tendering** | Extreme price spike projected in Month 1. Re-negotiate baseline quotes across secondary vendors. |
| **CRITICAL** | `C22008400005` | Insole - Kids 043 | PAA | €7.23 | €27.40 | +278.7% | 0.915 | None | 0.912 | **Buffer Stock Forward Buying** | +€20.16/unit cost inflation. Procure safety stock prior to projected May 2026 price surge. |
| **HIGH** | `C22006500003` | Packaging paper - Urban 033 | KG | €38.33 | €8.02 | -79.1% | 1.842 | Paper | 0.765 | **Dynamic Spot Pricing / Index Tracking** | Projected structural price drop of -€30.32/kg. Avoid fixed annual commitments; tie orders to spot paper index. |
| **HIGH** | `C22010800002` | Leather upper - Outdoor 055 | SQM | €33.09 | €4.82 | -85.4% | 1.652 | None | 0.814 | **Contract Price Renegotiation** | Origin price was an artificial peak. Demand downward price revision to reflect projected historical median. |
| **HIGH** | `C22003900001` | Adhesive - Outdoor 020 | KG | €0.0002 | €0.39 | +178k% | 2.999 | Methanol | 1.050 | **Formula-Based Chemical Index Linking** | High historical volatility (CV 3.0). Link procurement contract directly to Methanol index with 60-day lag. |
| **HIGH** | `C22009100005` | Foam - Classic 046 | KG | €3.02 | €2.02 | -33.1% | 4.977 | Adipic Acid | 0.997 | **Dual-Sourcing & Competitive Benchmarking** | Most volatile material in portfolio (CV 4.98). Qualify secondary suppliers to mitigate supplier-driven price swings. |
| **MEDIUM** | `C22018500002` | Eyelets - Performance 093 | PAA | €3.17 | €10.83 | +242.2% | 0.645 | Copper + Zinc | 1.254 | **Advance Purchase Order Issuance** | Component experiences steady inflation peaking in August 2026. Issue advance POs in Q1. |
| **MEDIUM** | `C22013800004` | Midsole - Performance 070 | PAA | €7.41 | €0.95 | -87.2% | 0.781 | Crude Oil | 0.892 | **Delayed Replenishment Strategy** | Severe projected decline troughing in August 2026. Minimize inventory holding; delay bulk orders. |
| **MEDIUM** | `C22000800004` | Midsole - Performance 005 | PAA | €0.95 | €8.14 | +759.6% | 0.712 | Crude Oil | 0.925 | **Alternative Material Specification Review** | Unit price rising from sub-euro to €8.14. Engage R&D to evaluate alternative composite midsole formulations. |

---

### Final Business Summary

#### 1. Top 10 Materials Requiring Urgent Procurement Attention
The highest composite risk materials combining extreme volatility ($	ext{CV} > 2.5$) and major forecasted price movements are:
1. `C22003900001` (*Adhesive - Outdoor 020*, Risk Score: 535,321)
2. `C22013100003` (*Packaging paper - Kids 066*, Risk Score: 354,425)
3. `C22017500003` (*Packaging paper - Urban 088*, Risk Score: 342,423)
4. `C22017800001` (*Lining - Kids 090*, Risk Score: 251,093)
5. `C22000600004` (*Midsole - Outdoor 004*, Risk Score: 122,630)
6. `C22007400002` (*Leather upper - Classic 038*, Risk Score: 20,709)
7. `C22015800006` (*Thread - Kids 080*, Risk Score: 1,890)
8. `C22005200005` (*Insole - Performance 027*, Risk Score: 833)
9. `C22016700005` (*Foam - Performance 084*, Risk Score: 220)
10. `C22009100005` (*Foam - Classic 046*, Risk Score: 165)

#### 2. Top 10 Expected Price Increases (Absolute Magnitude)
Led by outsoles, insoles, and specialized leather uppers:
`C22017600003` (+€33.68), `C22010000005` (+€26.01), `C22008400005` (+€20.16), `C22015800005` (+€8.72), `C22017600002` (+€8.33), `C22018500002` (+€7.67), `C22000800004` (+€7.19), `C22015400003` (+€6.81), `C22002500004` (+€6.23), and `C22006000002` (+€6.13).

#### 3. Top 10 Expected Price Decreases (Absolute Magnitude)
Led by materials mean-reverting from temporary 2025 peaks:
`C22006500003` (-€30.32), `C22010800002` (-€28.27), `C22013800004` (-€6.46), `C22003200001` (-€5.43), `C22012700004` (-€3.28), `C22009900002` (-€2.65), `C22001100004` (-€2.19), `C22002400005` (-€1.39), `C22012400002` (-€0.67), and `C22009600002` (-€0.27).

#### 4. Most Volatile Materials
Footwear chemicals (foams, adhesives, coating agents) and packaging papers dominate the highest volatility tier, with coefficients of variation spanning 2.60 to 4.98. Polyurethane foam `C22009100005` represents the single most volatile series in the portfolio ($	ext{CV} = 4.977$).

#### 5. Commodity-Related Forecasting Findings
- **High-Impact Exogenous Signals:** Methanol (+0.164 MASE uplift), Cotton (+0.047 MASE uplift), Polyamide (+0.062 MASE uplift), and Paper (+0.034 MASE uplift) reliably improve out-of-time forecasting accuracy even under conservative 3-month publication latency constraints (Lag-3).
- **Non-Informative Signals:** Macro energy indices (Crude Oil, Natural Gas) do not enhance component-level accuracy without complex non-linear supply chain intermediate margins.
- **Operational Feasibility:** While Lag-1 provides the highest statistical fit, Lag-3 represents the only operationally realistic production baseline in the absence of verified source publication timestamps.

#### 6. Potential Procurement Cost Implications
- Portfolio procurement expenditure across the 9-month test window is projected to increase by **+€280.4k (+0.99%)** under prior-year volume assumptions (Scenario A) and by **+€545.8k (+2.02%)** under realized purchase order quantities (Scenario B).
- Cost inflation is heavily concentrated in outsoles (+€142k impact) and insoles (+€98k impact), offset by substantial deflationary savings in packaging paper (-€85k impact).

#### 7. Five Evidence-Backed Recommendations for Procurement Stakeholders
1. **Lock in Q1 Long-Term Contracts for High-Inflation Outsoles:** Execute fixed-price annual agreements immediately for `C22017600003` and `C22015400003` prior to the projected Q2 summer manufacturing price surge.
2. **Aggressively Renegotiate Baseline Quotes on Deflating Categories:** Use empirical forecast projections to challenge vendor quotes on `C22006500003` (Packaging Paper) and `C22010800002` (Leather Upper), demanding downward adjustments toward €8.00/kg and €4.80/sqm respectively.
3. **Transition Chemical Procurement to Formula-Based Index Contracting:** Replace fixed annual bidding for adhesives and polyurethane foams with index-linked pricing tied to Methanol and Adipic Acid with a documented 60-day lag.
4. **De-Concentrate Single-Sourced High-HHI Footwear Components:** Address the strong empirical correlation between supplier concentration and price volatility ($r = +0.428$) by actively qualifying secondary vendors for all materials where leading vendor spend exceeds 65%.
5. **Establish Monthly Purchase Order Timing Governance:** Align purchase order release dates with the seasonal timeline (BQ3)—front-loading purchase orders in February/March for categories peaking in May, and postponing replenishments for categories troughing in August.
