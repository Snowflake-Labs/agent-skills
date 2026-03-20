---
title: Right-Size Your Warehouse
impact: CRITICAL
impactDescription: "2-10x cost reduction; prevents both under-provisioning and overspending"
tags: [warehouse, sizing, cost, performance]
---

## Right-Size Your Warehouse

**Impact: CRITICAL**

Snowflake warehouses double in compute with each size increment (XS→S→M→L). Picking a warehouse two sizes too large costs 4x more. Picking one too small makes queries slower, not cheaper — Snowflake bills per-second with a 60-second minimum.

**Incorrect (oversized warehouse for simple queries):**

```sql
-- Bad: XL warehouse for dashboard queries hitting small tables
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'X-LARGE'
  AUTO_SUSPEND = 600;
```

**Correct (start small, scale based on evidence):**

```sql
-- Good: Start with X-Small, monitor query profile
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- Check if queries are spilling to disk (sign warehouse is too small)
SELECT query_id, warehouse_size,
  bytes_spilled_to_local_storage,
  bytes_spilled_to_remote_storage
FROM snowflake.account_usage.query_history
WHERE warehouse_name = 'DASHBOARD_WH'
  AND bytes_spilled_to_remote_storage > 0
ORDER BY start_time DESC
LIMIT 20;
```

**Sizing Guidelines:**

| Warehouse Size | Best For |
|----------------|----------|
| X-Small | Simple queries, dashboards, small transforms |
| Small | Standard ETL, moderate joins |
| Medium | Complex joins, large aggregations |
| Large | Heavy transforms, large table scans |
| X-Large+ | Rarely needed; test before committing |

**Key signal:** If queries spill to remote storage, scale up. If most queries finish in < 1 second with no spills, scale down.

**Gen2 Standard Warehouses (GA May 2025):** Gen2 warehouses run on faster hardware (Graviton3) with ~2x analytics performance, but cost ~25-35% more per credit. They shine for CPU-bound batch workloads that suspend promptly. For bursty BI queries with staggered arrivals, the premium may not pay off. Always A/B test before switching:

```sql
-- Create a Gen2 warehouse for testing
CREATE WAREHOUSE etl_wh_gen2
  WAREHOUSE_SIZE = 'MEDIUM'
  RESOURCE_CONSTRAINT = STANDARD_GEN_2
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- Migrate an existing warehouse
ALTER WAREHOUSE my_wh SUSPEND;
ALTER WAREHOUSE my_wh SET RESOURCE_CONSTRAINT = STANDARD_GEN_2;
ALTER WAREHOUSE my_wh RESUME;
```

Reference: [Warehouse Considerations](https://docs.snowflake.com/en/user-guide/warehouses-considerations)
