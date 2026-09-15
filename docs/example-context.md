# Data Context

## Requested task
Prepare a data-quality review for customer churn prediction.

## Observations
```json
{
  "file": "customers.csv",
  "format": ".csv",
  "file_bytes": 116,
  "sampling": "First rows only; statistics describe the analyzed subset, not a random sample.",
  "tables_truncated": false,
  "tables": [
    {
      "table": "customers.csv",
      "rows_analyzed": 5,
      "rows_truncated": false,
      "columns_in_source": 4,
      "columns_truncated": false,
      "duplicate_rows_in_analyzed_columns": 0,
      "columns": [
        {
          "name": "customer_id",
          "dtype": "object",
          "missing": 0,
          "distinct_non_null": 5
        },
        {
          "name": "tenure_months",
          "dtype": "int64",
          "missing": 0,
          "distinct_non_null": 5,
          "min": 2.0,
          "max": 24.0,
          "mean": 12.4
        },
        {
          "name": "monthly_charge",
          "dtype": "float64",
          "missing": 1,
          "distinct_non_null": 3,
          "min": 49.0,
          "max": 79.0,
          "mean": 59.0
        },
        {
          "name": "churn",
          "dtype": "int64",
          "missing": 0,
          "distinct_non_null": 2,
          "min": 0.0,
          "max": 1.0,
          "mean": 0.4
        }
      ]
    }
  ]
}
```

## Interpretation limits
Statistics cover only the first configured rows and columns. Duplicate counts use only analyzed columns. Column types are reader-inferred, not semantic definitions. No raw example rows are included. Aggregate values and column names can still be sensitive.

## Next checks
Confirm the unit of observation, target definition, time ordering, join keys, and possible target leakage against the requested task. Confirm sample representativeness before generalizing. These are checks to perform, not established findings.

Mode: deterministic profile; no model inference was performed.
