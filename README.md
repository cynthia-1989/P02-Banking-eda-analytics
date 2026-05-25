# P02 ⭐⭐ — Banking EDA 💳

## Overview

This project builds a banking exploratory data analysis (EDA) pipeline for analysing transaction behaviour, fraud patterns, customer segment activity, statistical relationships, and anomalous banking transactions.

The pipeline loads processed banking transaction data, performs fraud profiling, customer segment analysis, chi-square statistical testing, anomaly detection, and generates reports and visualisations.

---

## Table of Contents

1. [Project Brief](#project-brief)
2. [EDA Workflow](#eda-workflow)
3. [Input and Output](#input-and-output)
4. [Project Structure](#project-structure)
5. [Fraud Pattern Analysis](#fraud-pattern-analysis)
6. [Segment Behaviour Analysis](#segment-behaviour-analysis)
7. [Chi-Square Independence Test](#chi-square-independence-test)
8. [Anomaly Detection](#anomaly-detection)
9. [Visualisations](#visualisations)
10. [How to Run](#how-to-run)
11. [Tests](#tests)
12. [Git Workflow](#git-workflow)

---

## Project Brief

**Company:** NexBank  
**Role:** Data Analyst — Risk Analytics

The banking dataset includes transactional records such as:

- Transaction amounts
- Merchant categories
- Customer segments
- Payment channels
- Fraud indicators
- Transaction timestamps

The analysis focuses on identifying fraud concentration, customer transaction behaviour, statistical fraud relationships, and suspicious banking transactions.

---

## EDA Workflow

### 1. Load

Load the processed banking dataset from:

```text
data/processed/processed-data.csv
```

The dataset is generated from the ETL pipeline.

---

### 2. Profile

Generate a statistical overview of the banking dataset.

Checks include:

- Row and column counts
- Missing values
- Duplicate records
- Numeric summaries
- Categorical summaries

---

### 3. Fraud Pattern Analysis

Analyse fraud concentration using groupby operations.

Analysis includes:

- Fraud count by merchant category
- Fraud count by payment channel
- Fraud concentration by time period
- Fraud ranking analysis

---

### 4. Segment Behaviour Analysis

Analyse customer transaction behaviour across segments.

Analysis includes:

- Average transaction amount by segment
- Transaction frequency by segment
- Fraud rate by segment
- Segment comparison statistics

Customer segments analysed include:

- Retail
- Premium
- Business
- Student

---

### 5. Chi-Square Independence Test

Test whether fraud occurrence is statistically independent of merchant category.

The project uses:

```python
scipy.stats.chi2_contingency()
```

The chi-square test determines whether fraud and merchant category have a statistically significant relationship.

---

### 6. Anomaly Detection

Detect statistically unusual banking transactions using:

- IQR method
- Z-score method
- Fraud anomaly detection

The project also identifies difficult fraud cases where:

- `is_fraud=True`
- Transaction amount appears statistically normal

Transactions flagged by multiple methods are treated as confirmed anomalies.

---

## Input and Output

### Input

```text
data/processed/processed-data.csv
```

### Outputs

```text
reports/analysis_report.txt
reports/anomalies.csv
reports/segment_profile.csv
reports/figures/
```

---

## Project Structure

```text
P02-banking-eda/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│
├── reports/
│   └── figures/
│
├── sql/
│
├── src/
│   ├── data_extractor.py
│   ├── validator.py
│   ├── transformer.py
│   ├── eda_engine.py
│   ├── segment_profiler.py
│   ├── anomaly_detector.py
│   └── query_runner.py
│
├── tests/
│
├── run.py
├── config.py
├── requirements.txt
└── README.md
```

---

## Fraud Pattern Analysis

The project analyses fraud concentration by:

- Merchant category
- Payment channel
- Customer segment
- Transaction period

Metrics generated include:

- Fraud counts
- Fraud percentages
- Fraud ranking
- High-risk merchant categories

---

## Segment Behaviour Analysis

The project evaluates transaction behaviour across customer segments.

Metrics generated include:

- Average transaction amount
- Median transaction amount
- Transaction frequency
- Fraud rate
- Total transaction volume

The analysis helps identify behavioural differences between banking customer types.

---

## Chi-Square Independence Test

The project evaluates whether fraud occurrence depends on merchant category.

Variables analysed include:

- `merchant_category`
- `is_fraud`

Chi-square testing is used to determine whether the relationship is statistically significant.

Decision rule:

- If `p < 0.05` → relationship is statistically significant
- If `p >= 0.05` → variables are statistically independent

---

## Anomaly Detection

The anomaly detection module identifies transactions that are statistically unusual.

Examples include:

- Extremely high transaction amounts
- Abnormal customer behaviour
- Unusual fraud activity
- Fraudulent transactions with normal transaction amounts

Detected anomalies are exported to:

```text
reports/anomalies.csv
```

---

## Visualisations

The notebook generates and saves banking visualisations including:

- Fraud count by merchant category
- Fraud count by payment channel
- Transaction amount distributions
- Customer segment comparisons
- Correlation heatmaps
- Banking anomaly visualisations

Saved charts are stored in:

```text
reports/figures/
```

---

## How to Run

Run the complete banking EDA pipeline:

```bash
python run.py
```

The pipeline performs:

1. SQL extraction
2. Validation
3. Transformation
4. EDA analysis
5. Fraud analysis
6. Anomaly detection
7. Report generation

---

## Tests

Run unit tests using:

```bash
pytest tests/
```

Tests cover:

- EDAEngine methods
- Fraud pattern analysis
- Segment profiling
- Chi-square testing
- Anomaly detection
- Data quality validation

---

## Git Workflow

```bash
git status
git add .
git commit -m "feat: complete banking EDA pipeline"
git push
```

---

## Success Criteria Achieved

- EDAEngine implemented
- SegmentProfiler implemented
- Chi-square analysis completed
- Fraud pattern analysis completed
- AnomalyDetector implemented
- Anomalies exported to CSV
- Visualisations generated
- Unit tests completed
- Project pushed to GitHub

---