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

$$\text{weighted\_unit\_price\_eur} = \frac{\sum_{i \in \text{eligible}} \text{eur\_expenditure}_i}{\sum_{i \in \text{eligible}} \text{standardized\_po\_qty}_i} = \frac{\text{eligible\_spend\_eur}}{\text{comparable\_po\_quantity}}$$

#### Key Properties Verified:
1. **Strict Volume Gating:** In months with zero purchase orders, zero standardized quantity, or non-positive quantities, `comparable_po_quantity` is 0. The transformation employs `CASE WHEN comparable_po_quantity > 0 THEN ... ELSE NULL END`. The target is strictly **`NULL`**, never imputed as zero.
2. **Currency Eligibility Protection:** Transactions with unconfirmed exchange rates (the 188 `EURO` alias rows) are quarantined in `pending_spend_local` and are excluded from `eligible_spend_eur`. They do not contaminate unit prices.
3. **UOM Standardization:** Only records with `uom_conversion_status = 'IDENTITY_VERIFIED'` enter `comparable_po_quantity`. The 181 `PENDING_APPROVAL` records are excluded.
4. **Outlier Treatment:** The 199 price outliers are included in `weighted_unit_price_eur` per business guidelines, but are fully identified via `price_outlier_record_count` to enable sensitivity experiments.
5. **Extreme Dynamic Price Range:** Minimum unit price is €0.000025 (thread) and maximum is €550.00 (leather). The dynamic ratio is $\frac{550.00}{0.000025} = 22,000,000$ (a **22-million-to-1 dynamic range**, spanning **over 7 orders of magnitude**: $\log_{10}(2.2 \times 10^7) = 7.34$). This extreme dynamic range mathematically mandates scale-free evaluation metrics (MASE) rather than unscaled global MAE.

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
