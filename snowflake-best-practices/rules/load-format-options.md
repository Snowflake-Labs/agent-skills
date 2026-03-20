---
title: Configure File Format Options Correctly
impact: HIGH
impactDescription: "Prevents silent data corruption from mismatched format options"
tags: [loading, file-format, csv, parquet, json]
---

## Configure File Format Options Correctly

**Impact: HIGH**

Incorrect file format options cause silent data corruption — wrong columns, truncated values, or null where data should exist. Always create named file formats rather than inlining options.

**Incorrect (inline options, easy to get wrong):**

```sql
-- Bad: Inline options are error-prone and not reusable
COPY INTO my_table FROM @my_stage
FILE_FORMAT = (TYPE = CSV FIELD_DELIMITER = ',' SKIP_HEADER = 1
  RECORD_DELIMITER = '\n' FIELD_OPTIONALLY_ENCLOSED_BY = '"');
```

**Correct (named file format):**

```sql
-- Good: Create a reusable, documented file format
CREATE FILE FORMAT IF NOT EXISTS my_db.public.csv_standard
  TYPE = CSV
  FIELD_DELIMITER = ','
  RECORD_DELIMITER = '\n'
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('NULL', 'null', '\\N', '')
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE
  TRIM_SPACE = TRUE
  COMMENT = 'Standard CSV with headers, comma-delimited, double-quote enclosed';

COPY INTO my_table FROM @my_stage FILE_FORMAT = my_db.public.csv_standard;
```

**Format-specific recommendations:**

```sql
-- Parquet: Best format for analytics — typed, compressed, columnar
CREATE FILE FORMAT parquet_standard
  TYPE = PARQUET
  COMPRESSION = SNAPPY;  -- default, fastest decompression

-- Use MATCH_BY_COLUMN_NAME for Parquet (handles column order changes)
COPY INTO my_table FROM @my_stage
  FILE_FORMAT = parquet_standard
  MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- JSON: Use STRIP_OUTER_ARRAY for JSON arrays
CREATE FILE FORMAT json_standard
  TYPE = JSON
  STRIP_OUTER_ARRAY = TRUE
  ALLOW_DUPLICATE = FALSE
  STRIP_NULL_VALUES = FALSE;

-- Important: For JSON, load into a VARIANT column first, then flatten
COPY INTO raw.json_events (src)
FROM @my_stage
FILE_FORMAT = json_standard;
```

**Critical options to always set:**
| Option | Why |
|--------|-----|
| `ERROR_ON_COLUMN_COUNT_MISMATCH` | Catches schema drift immediately |
| `NULL_IF` | Ensures consistent NULL representation |
| `MATCH_BY_COLUMN_NAME` (Parquet) | Handles column reordering safely |
| `ON_ERROR = ABORT_STATEMENT` | Default; don't silently skip bad data |

**Prefer Parquet over CSV** for any non-trivial data pipeline. Parquet is typed, compressed, and supports schema evolution. CSV requires manual type casting and is prone to delimiter/encoding issues.

Reference: [File Format Options](https://docs.snowflake.com/en/sql-reference/sql/create-file-format)
