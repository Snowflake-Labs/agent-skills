---
name: dynamic-tables
description: "Best practices for Snowflake Dynamic Tables — declarative data pipelines with automatic incremental refresh, replacing complex Streams + Tasks patterns"
---

# Snowflake Dynamic Tables

## Overview

Dynamic Tables are declarative, SQL-defined tables that Snowflake automatically keeps fresh. You write a query that defines **what** the table should contain, and Snowflake handles the **when** (scheduling) and **how** (incremental vs full refresh). They replace the manual orchestration of Streams + Tasks with a single DDL statement.

Key properties:
- **Declarative** — define the transformation as a SELECT, not imperative INSERT/MERGE logic
- **Automatic refresh** — Snowflake detects upstream changes and refreshes on a schedule you control via `TARGET_LAG`
- **Incremental when possible** — Snowflake automatically chooses incremental refresh for supported operations, processing only changed data
- **DAG-aware** — chain Dynamic Tables together; Snowflake resolves dependencies and refreshes in the correct order

> **Official docs:** [Snowflake Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about)

---

## When to Use Dynamic Tables

**Good fit:**
- Replace Streams + Tasks for incremental ETL/ELT pipelines
- Replace scheduled `CREATE TABLE AS SELECT` or `INSERT OVERWRITE` patterns
- Multi-hop transformation chains (bronze → silver → gold)
- Materialized views that need JOIN support or complex logic (materialized views cannot do JOINs)
- Any pipeline where you want Snowflake to manage scheduling and dependency ordering

**Not a good fit:**
- Sub-second latency requirements — use Snowpipe Streaming instead
- Simple one-off transforms that run once — use `CREATE TABLE AS SELECT`
- Tables that need DML writes (INSERT/UPDATE/DELETE) — Dynamic Tables are read-only; Snowflake owns the data
- Append-only event logging — use standard tables with Snowpipe or Streams

---

## Creating Dynamic Tables

### Basic Syntax

```sql
CREATE OR REPLACE DYNAMIC TABLE my_db.my_schema.orders_cleaned
  TARGET_LAG = '1 hour'
  WAREHOUSE = transform_wh
AS
  SELECT
      order_id,
      customer_id,
      TRIM(status) AS status,
      amount::NUMBER(12,2) AS amount,
      created_at
  FROM my_db.raw.orders
  WHERE status IS NOT NULL;
```

### TARGET_LAG Options

| Value | Behavior | Use When |
|-------|----------|----------|
| `'1 minute'` | Refresh within 1 minute of upstream change | Near-real-time dashboards |
| `'1 hour'` | Refresh within 1 hour | Standard reporting pipelines |
| `'1 day'` | Refresh within 1 day | Daily batch analytics |
| `DOWNSTREAM` | Refresh only when a downstream DT needs data | Intermediate pipeline stages |

```sql
-- Time-based: consumer-facing table refreshes every 10 minutes
CREATE DYNAMIC TABLE gold.daily_revenue
  TARGET_LAG = '10 minutes'
  WAREHOUSE = transform_wh
AS SELECT ...;

-- DOWNSTREAM: intermediate table refreshes only when needed
CREATE DYNAMIC TABLE silver.orders_deduped
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
AS SELECT ...;
```

### Warehouse Assignment

Dedicate a small warehouse for DT refreshes. Do not share it with interactive queries.

```sql
CREATE WAREHOUSE transform_wh
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

---

## Designing DT Pipelines (DAGs)

Chain Dynamic Tables by referencing upstream DTs in the query. Snowflake builds a dependency DAG and refreshes in order.

```
raw.events  ──►  bronze.events_raw  ──►  silver.events_cleaned  ──►  gold.event_metrics
 (source)         (TARGET_LAG =           (TARGET_LAG =               (TARGET_LAG =
                   DOWNSTREAM)             DOWNSTREAM)                 '10 minutes')
```

### Bronze: Raw Ingestion

```sql
CREATE DYNAMIC TABLE bronze.events_raw
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
AS
  SELECT
      $1:event_id::VARCHAR AS event_id,
      $1:user_id::VARCHAR AS user_id,
      $1:event_type::VARCHAR AS event_type,
      $1:payload::VARIANT AS payload,
      $1:ts::TIMESTAMP_NTZ AS event_ts,
      METADATA$FILENAME AS source_file
  FROM @raw.events_stage (FILE_FORMAT => 'json_format');
```

### Silver: Cleaned and Validated

```sql
CREATE DYNAMIC TABLE silver.events_cleaned
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
AS
  SELECT
      event_id,
      user_id,
      event_type,
      payload,
      event_ts
  FROM bronze.events_raw
  WHERE event_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_ts DESC) = 1;
```

### Gold: Business Aggregates

```sql
CREATE DYNAMIC TABLE gold.event_metrics
  TARGET_LAG = '10 minutes'
  WAREHOUSE = transform_wh
AS
  SELECT
      DATE_TRUNC('hour', event_ts) AS event_hour,
      event_type,
      COUNT(*) AS event_count,
      COUNT(DISTINCT user_id) AS unique_users
  FROM silver.events_cleaned
  GROUP BY 1, 2;
```

**Pattern:** Use `TARGET_LAG = DOWNSTREAM` for bronze and silver. Set a time-based lag only on the gold (consumer-facing) DT. This avoids unnecessary intermediate refreshes.

---

## Incremental vs Full Refresh

Snowflake automatically selects incremental refresh when the query supports it. Incremental processes only changed micro-partitions — significantly cheaper and faster.

### Operations That Support Incremental Refresh

- Filters (`WHERE`)
- Projections (column selection, expressions)
- `INNER JOIN`, `LEFT/RIGHT OUTER JOIN` (with equality predicates)
- `UNION ALL`
- Simple aggregations (`GROUP BY` with `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`)
- `QUALIFY` with `ROW_NUMBER()`

### Operations That Force Full Refresh

- `LIMIT` / `TOP`
- Non-deterministic functions: `RANDOM()`, `UUID_STRING()`, `CURRENT_TIMESTAMP()`
- `UNION` (dedup requires full scan)
- Some window functions beyond `ROW_NUMBER()` (e.g., `LAG`, `LEAD`, `NTILE`)
- Subqueries in `SELECT` list
- `ORDER BY` at the top level (without `QUALIFY`)

```sql
-- WRONG: Forces full refresh due to CURRENT_TIMESTAMP()
CREATE DYNAMIC TABLE silver.orders_with_load_ts
  TARGET_LAG = '1 hour'
  WAREHOUSE = transform_wh
AS
  SELECT *, CURRENT_TIMESTAMP() AS loaded_at
  FROM bronze.raw_orders;

-- CORRECT: Use METADATA$ACTION or upstream timestamp instead
CREATE DYNAMIC TABLE silver.orders_with_load_ts
  TARGET_LAG = '1 hour'
  WAREHOUSE = transform_wh
AS
  SELECT *, ingested_at AS loaded_at
  FROM bronze.raw_orders;
```

### Check Refresh Mode

```sql
SHOW DYNAMIC TABLES LIKE 'orders_cleaned' IN SCHEMA my_db.my_schema;
-- Check "refresh_mode" column: INCREMENTAL or FULL
```

---

## Monitoring and Troubleshooting

### View DT Status

```sql
-- List all Dynamic Tables with status
SHOW DYNAMIC TABLES IN SCHEMA my_db.my_schema;

-- Refresh history for a specific DT
SELECT *
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME => 'my_db.my_schema.orders_cleaned',
  DATA_TIMESTAMP_START => DATEADD('day', -1, CURRENT_TIMESTAMP())
))
ORDER BY data_timestamp DESC;
```

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `UPSTREAM_FAILED` scheduling state | An upstream DT failed to refresh | Fix the upstream DT first; downstream DTs resume automatically |
| DT stuck in `SUSPENDED` | Manual suspend or account-level issue | `ALTER DYNAMIC TABLE ... RESUME` |
| Full refresh when incremental expected | Query uses unsupported operation | Check for `LIMIT`, non-deterministic functions, or complex window functions; rewrite the query |
| Refresh takes too long | Warehouse too small or query not pruning | Scale up the warehouse or add filters that align with clustering keys |
| Stale data despite short TARGET_LAG | Upstream source not changing, or refresh errors | Check `DYNAMIC_TABLE_REFRESH_HISTORY` for error messages |

### Manual Operations

```sql
-- Force an immediate refresh
ALTER DYNAMIC TABLE my_db.my_schema.orders_cleaned REFRESH;

-- Suspend refreshes (e.g., during maintenance)
ALTER DYNAMIC TABLE my_db.my_schema.orders_cleaned SUSPEND;

-- Resume refreshes
ALTER DYNAMIC TABLE my_db.my_schema.orders_cleaned RESUME;
```

---

## Performance Best Practices

1. **Dedicated warehouse** — Use a separate XS or S warehouse for DT refreshes. Do not share with ad-hoc queries; contention delays refreshes.

2. **Right-size TARGET_LAG** — Every refresh costs credits. A 1-minute lag on a table consumed once daily wastes money. Match lag to actual consumption frequency.

   ```sql
   -- WRONG: Over-refreshing for a daily report
   CREATE DYNAMIC TABLE gold.daily_summary
     TARGET_LAG = '1 minute'  -- Refreshes ~1440 times/day for a daily report
     WAREHOUSE = transform_wh
   AS SELECT ...;

   -- CORRECT: Match lag to consumption
   CREATE DYNAMIC TABLE gold.daily_summary
     TARGET_LAG = '1 hour'  -- 24 refreshes/day is sufficient
     WAREHOUSE = transform_wh
   AS SELECT ...;
   ```

3. **Narrow transformation chains** — Each DT should do one logical step. Don't combine ingestion, cleaning, dedup, and aggregation into a single DT. Smaller steps enable incremental refresh and are easier to debug.

4. **Use DOWNSTREAM for intermediates** — Only the final consumer-facing DT needs a time-based lag. Intermediate DTs should use `DOWNSTREAM` to avoid unnecessary refreshes.

5. **Add clustering keys on large DTs** — If a gold DT is large (>1 TB) and queried with specific filters, add a clustering key for downstream query performance.

   ```sql
   ALTER DYNAMIC TABLE gold.event_metrics CLUSTER BY (event_hour);
   ```

6. **Avoid non-deterministic functions** — They force full refresh every cycle. Use upstream-provided timestamps instead of `CURRENT_TIMESTAMP()`.

---

## Migration from Streams + Tasks

### Before: Streams + Tasks

```sql
-- Step 1: Create a stream on the source
CREATE STREAM raw.orders_stream ON TABLE raw.orders;

-- Step 2: Create a target table
CREATE TABLE silver.orders_cleaned (
    order_id VARCHAR,
    customer_id VARCHAR,
    amount NUMBER(12,2),
    created_at TIMESTAMP_NTZ
);

-- Step 3: Create a task with manual scheduling and error handling
CREATE TASK silver.orders_clean_task
  WAREHOUSE = transform_wh
  SCHEDULE = '1 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('raw.orders_stream')
AS
  MERGE INTO silver.orders_cleaned t
  USING (
      SELECT order_id, customer_id, amount::NUMBER(12,2) AS amount, created_at
      FROM raw.orders_stream
      WHERE order_id IS NOT NULL
  ) s
  ON t.order_id = s.order_id
  WHEN MATCHED THEN UPDATE SET t.amount = s.amount, t.created_at = s.created_at
  WHEN NOT MATCHED THEN INSERT (order_id, customer_id, amount, created_at)
    VALUES (s.order_id, s.customer_id, s.amount, s.created_at);

-- Step 4: Resume the task (tasks are created suspended)
ALTER TASK silver.orders_clean_task RESUME;
```

**Problems:** 4 separate objects to manage. Manual MERGE logic. Must handle task failures, stream staleness, and dependency ordering yourself. Multi-hop pipelines require chaining tasks with `AFTER` clauses.

### After: Dynamic Table

```sql
CREATE DYNAMIC TABLE silver.orders_cleaned
  TARGET_LAG = '1 minute'
  WAREHOUSE = transform_wh
AS
  SELECT
      order_id,
      customer_id,
      amount::NUMBER(12,2) AS amount,
      created_at
  FROM raw.orders
  WHERE order_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY created_at DESC) = 1;
```

**Result:** Single object. No stream, no task, no MERGE logic. Snowflake handles change detection, scheduling, incremental processing, deduplication, and dependency ordering automatically.

### Migration Checklist

- [ ] Identify all Streams + Tasks in the pipeline
- [ ] Map each MERGE/INSERT to a `CREATE DYNAMIC TABLE` with the equivalent SELECT
- [ ] Replace `SCHEDULE` intervals with appropriate `TARGET_LAG`
- [ ] Replace task chaining (`AFTER`) with DT references (query one DT from another)
- [ ] Test that the DT query supports incremental refresh (avoid `LIMIT`, non-deterministic functions)
- [ ] Suspend old tasks before enabling DTs to avoid duplicate processing
- [ ] Drop streams and tasks after validating DT output matches expected results
