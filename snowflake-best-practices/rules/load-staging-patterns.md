---
title: Use Proper Staging Patterns
impact: HIGH
impactDescription: "Clean separation of raw, validated, and production data prevents data quality issues"
tags: [loading, staging, architecture, data-quality]
---

## Use Proper Staging Patterns

**Impact: HIGH**

Load data into a raw staging layer first, then validate and transform. Loading directly into production tables risks corrupt or partial data reaching consumers.

**Incorrect (loading directly into production):**

```sql
-- Bad: Raw CSV data goes straight into the table users query
COPY INTO production.customers
FROM @external_stage/customers/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1);
-- If the file has bad rows, production is corrupted
```

**Correct (raw → staging → production pattern):**

```sql
-- Step 1: Load raw data with ON_ERROR = CONTINUE to capture everything
COPY INTO raw.customers_load
FROM @external_stage/customers/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)
ON_ERROR = CONTINUE;

-- Step 2: Validate and transform into staging
CREATE OR REPLACE TABLE staging.customers AS
SELECT
  $1::NUMBER AS customer_id,
  TRIM($2)::VARCHAR AS name,
  TRY_TO_DATE($3, 'YYYY-MM-DD') AS signup_date,
  $4::VARCHAR AS email
FROM raw.customers_load
WHERE TRY_TO_NUMBER($1) IS NOT NULL  -- skip bad rows
  AND TRY_TO_DATE($3, 'YYYY-MM-DD') IS NOT NULL;

-- Step 3: Merge into production
MERGE INTO production.customers t
USING staging.customers s ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET
  name = s.name, signup_date = s.signup_date, email = s.email
WHEN NOT MATCHED THEN INSERT
  (customer_id, name, signup_date, email)
  VALUES (s.customer_id, s.name, s.signup_date, s.email);
```

**Stage types and when to use them:**

```sql
-- Internal named stage: Data stays in Snowflake storage
CREATE STAGE my_internal_stage ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- External stage: Points to S3/GCS/Azure — data stays in your cloud
CREATE STAGE my_s3_stage
  URL = 's3://my-bucket/data/'
  STORAGE_INTEGRATION = my_s3_integration;

-- Table stage: Quick ad-hoc loads (every table has one: @%table_name)
PUT file:///tmp/data.csv @%my_table;
```

**Use TRY_ functions for safe type casting:**

```sql
-- TRY_TO_NUMBER returns NULL instead of erroring on bad data
SELECT TRY_TO_NUMBER('abc');  -- NULL (not an error)
SELECT TRY_TO_DATE('not-a-date');  -- NULL (not an error)
```

Reference: [Staging Data](https://docs.snowflake.com/en/user-guide/data-load-local-file-system-create-stage)
