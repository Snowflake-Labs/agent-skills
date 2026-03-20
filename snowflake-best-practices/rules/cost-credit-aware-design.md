---
title: Design for Credit-Aware Architecture
impact: CRITICAL
impactDescription: "Architectural decisions that reduce Snowflake spend by 30-70%"
tags: [cost, architecture, credits, optimization]
---

## Design for Credit-Aware Architecture

**Impact: CRITICAL**

Every Snowflake operation consumes credits. Understanding the cost model lets you make architectural choices that dramatically reduce spend without sacrificing performance.

**Credit consumption model:**

| Resource | Cost Driver | Optimization |
|----------|------------|-------------|
| Warehouses | Size × active time (per-second, 60s min) | Right-size, auto-suspend |
| Snowpipe | 0.06 credits/file | Batch files, avoid tiny files |
| Auto-clustering | Data reorganization | Only cluster tables >1TB |
| Materialized views | Maintenance compute | Use sparingly, prefer Dynamic Tables |
| Serverless tasks | Compute for task runs | Schedule efficiently |

**Incorrect (oversized warehouse for small queries):**

```sql
-- Bad: 4XL warehouse for a query scanning 100MB
ALTER WAREHOUSE SET WAREHOUSE_SIZE = 'X4LARGE';
SELECT COUNT(*) FROM small_table WHERE status = 'active';
-- Cost: Minimum 60 seconds × 128 credits/hour = 2.13 credits
```

**Correct (right-sized warehouse):**

```sql
-- Good: XS warehouse for small queries
ALTER WAREHOUSE SET WAREHOUSE_SIZE = 'XSMALL';
SELECT COUNT(*) FROM small_table WHERE status = 'active';
-- Cost: Minimum 60 seconds × 1 credit/hour = 0.017 credits
```

**Use transient tables for staging and intermediate data:**

```sql
-- Good: Transient tables have no Fail-safe storage cost (saves 7 days of storage)
CREATE TRANSIENT TABLE staging.daily_load (
  id NUMBER,
  data VARIANT,
  loaded_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Set low retention for staging (0 or 1 day)
ALTER TABLE staging.daily_load SET DATA_RETENTION_TIME_IN_DAYS = 0;
```

**Cost-effective patterns:**

```sql
-- 1. Use LIMIT during development
SELECT * FROM large_table LIMIT 100;  -- Don't scan full table while developing

-- 2. Use SAMPLE for analysis on large tables
SELECT AVG(amount), STDDEV(amount)
FROM large_orders SAMPLE (1);  -- 1% sample, not full scan

-- 3. Use EXPLAIN to check cost before running
EXPLAIN
SELECT ... FROM large_table ...;
-- Check "partitionsTotal" and "partitionsAssigned" in the output

-- 4. Schedule Tasks during off-peak hours
CREATE TASK nightly_etl
  WAREHOUSE = etl_wh
  SCHEDULE = 'USING CRON 0 2 * * * America/Los_Angeles'  -- 2 AM PT
AS
  CALL run_etl_pipeline();
```

**Monitor spending:**

```sql
-- Credit usage by warehouse (last 30 days)
SELECT warehouse_name,
  SUM(credits_used) AS total_credits,
  SUM(credits_used) * 3.00 AS estimated_cost_usd  -- adjust rate
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY warehouse_name
ORDER BY total_credits DESC;
```

Reference: [Understanding Compute Cost](https://docs.snowflake.com/en/user-guide/cost-understanding-compute)
