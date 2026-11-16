# ECCO Procurement Data Quality Report Guide

## Purpose

`notebooks/ecco_procurement_data_quality_assessment.ipynb` is a reproducible
data-quality and descriptive-analysis report for the PostgreSQL database
`ecco_procurement`.

The report documents:

- Database objects, columns, types, keys, and relationships.
- Row counts and table completeness.
- Null values and completely empty columns.
- Duplicate full rows and duplicate primary-key values.
- Foreign-key violations.
- Numeric summaries and date coverage.
- Categorical value frequencies.
- Recorded issues in `data_quality_issue_register`.
- Known limitations and inaccessible objects.

It does not produce business recommendations, forecasts, pricing strategies, or
causal conclusions.

## Environment

Use the existing `.ecco` virtual environment:

```powershell
cd "C:\Users\Rohit Halder\projects\INDIUM_INTERNSHIP"
.\.ecco\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

In VS Code, select the `.ecco` interpreter/kernel before running the notebook.

The notebook uses:

- `pandas` and `numpy` for data analysis.
- `matplotlib` and `seaborn` for charts.
- `SQLAlchemy` with `psycopg2-binary` for PostgreSQL access.
- `python-dotenv` to load the local `.env` file.

## Database configuration

Create a local `.env` file in the project root. It is ignored by Git and must
not be committed:

```text
PGHOST=localhost
PGPORT=5432
PGDATABASE=ecco_procurement
PGUSER=postgres
PGPASSWORD=your_local_password
```

The notebook validates required settings but never displays the password or a
credential-bearing connection URL.

## Running the report

1. Make sure PostgreSQL is running.
2. Make sure `ecco_procurement` has been created and loaded by
   `load_data\Database_loader.sql`.
3. Open `data_report/notebooks/ecco_procurement_data_quality_assessment.ipynb`.
4. Select the `.ecco` kernel.
5. Run all cells from top to bottom.

The notebook discovers non-system schemas and tables/views dynamically. It
records table access failures instead of silently omitting them. Exact row
counts are obtained with `COUNT(*)`.

## Interpreting statuses

- `pass`: the executed check found no violations at that run.
- `fail`: the executed check found one or more violations.
- `not_defined`: the database does not define the requested constraint.
- `not_applicable_empty`: the table has a constraint but no rows to test.
- `failed`: the object could not be analyzed; the error is retained.

A passing check is not a guarantee about future loads or the upstream source.
The source package contains intentional quality issues, including missing
values, duplicate business keys, invalid reported vendor keys, and structural
missing months.

## Reproducibility and data safety

The notebook reads live database contents at execution time. It does not modify
the database or CSV files. It does not write credentials to notebook output.
Because the report is database-backed, rerun it after any reload or schema
change. Rotate database credentials if they have been exposed and keep `.env`
ignored.
