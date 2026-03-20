---
title: Use Query Acceleration for Outlier Queries
impact: HIGH
impactDescription: "Up to 8x faster for outlier queries in ad-hoc workloads"
tags: [warehouse, query-acceleration, performance]
---

## Use Query Acceleration for Outlier Queries

**Impact: HIGH**

The Query Acceleration Service (QAS) offloads portions of a query to shared compute resources. It helps most when a workload has a mix of fast and slow queries — the outlier slow queries get accelerated without sizing up the warehouse for the common case.

**Incorrect (oversizing the warehouse because of occasional slow queries):**

```sql
-- Bad: Warehouse is X-Large because 5% of queries are slow
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'X-LARGE'
  AUTO_SUSPEND = 60;
-- 95% of queries finish in 2 seconds on X-Small, but a few table scans take 3 minutes
```

**Correct (right-sized warehouse + QAS for outliers):**

```sql
-- Good: Keep warehouse small, enable QAS for the long-tail
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  ENABLE_QUERY_ACCELERATION = TRUE
  QUERY_ACCELERATION_MAX_SCALE_FACTOR = 4;
```

**When QAS helps:**
- Ad-hoc / exploratory analytics with variable query patterns
- Queries that scan large portions of big tables
- Workloads where most queries are fast but a few are outliers

**When QAS does NOT help:**
- Queries already optimized with good pruning
- All queries are uniformly fast or uniformly slow
- Queries bottlenecked by something other than scan (e.g., complex UDFs)

**Check eligible queries:**

```sql
-- See which queries would benefit from QAS
SELECT query_id, eligible_query_acceleration_time
FROM snowflake.account_usage.query_acceleration_eligible
WHERE warehouse_name = 'ANALYTICS_WH'
  AND eligible_query_acceleration_time > 0
ORDER BY eligible_query_acceleration_time DESC
LIMIT 20;
```

Reference: [Query Acceleration Service](https://docs.snowflake.com/en/user-guide/query-acceleration-service)
