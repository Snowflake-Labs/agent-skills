---
title: Set Statement Timeouts to Kill Runaway Queries
impact: HIGH
impactDescription: "Prevents single queries from consuming hours of warehouse credits"
tags: [cost, timeout, governance, query-management]
---

## Set Statement Timeouts to Kill Runaway Queries

**Impact: HIGH**

A single poorly written query (accidental cross join, missing filter) can run for hours on a large warehouse, burning hundreds of credits. Statement timeouts are your safety net.

**Incorrect (no timeout):**

```sql
-- Bad: No timeout — this accidental cross join runs for 4 hours
SELECT * FROM table_a CROSS JOIN table_b;
-- Cost: ~48 credits on a LARGE warehouse
```

**Correct (set statement timeouts at multiple levels):**

```sql
-- Set timeout at warehouse level (affects all queries on this warehouse)
ALTER WAREHOUSE analytics_wh
  SET STATEMENT_TIMEOUT_IN_SECONDS = 3600;  -- 1 hour max

-- Set timeout at user level (for specific power users)
ALTER USER analyst_user
  SET STATEMENT_TIMEOUT_IN_SECONDS = 1800;  -- 30 minutes

-- Set timeout at session level (for a specific session)
ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 900;  -- 15 minutes
```

**Recommended timeouts by environment:**

| Environment | Timeout | Rationale |
|------------|---------|-----------|
| Development | 300s (5 min) | Catches mistakes fast |
| Ad-hoc/BI | 900s (15 min) | Reasonable for complex dashboards |
| ETL/Production | 3600s (1 hour) | Allow long-running transforms |
| Data Science | 7200s (2 hours) | ML training queries need time |

**Also set STATEMENT_QUEUED_TIMEOUT:**

```sql
-- Kill queries that wait too long in the queue (warehouse busy)
ALTER WAREHOUSE analytics_wh
  SET STATEMENT_QUEUED_TIMEOUT_IN_SECONDS = 600;  -- 10 min queue max
-- Prevents queries from silently queuing for hours
```

**Monitor long-running queries:**

```sql
-- Find currently running queries over 5 minutes
SELECT query_id, query_text, warehouse_name,
  DATEDIFF('minute', start_time, CURRENT_TIMESTAMP()) AS running_minutes
FROM TABLE(information_schema.query_history(
  DATEADD('hour', -1, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP()))
WHERE execution_status = 'RUNNING'
  AND running_minutes > 5
ORDER BY running_minutes DESC;
```

Reference: [Statement Timeout Parameters](https://docs.snowflake.com/en/sql-reference/parameters#statement-timeout-in-seconds)
