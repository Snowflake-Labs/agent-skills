---
title: Configure Auto-Suspend Appropriately
impact: CRITICAL
impactDescription: "Prevents idle warehouse charges; typical 30-70% cost savings"
tags: [warehouse, auto-suspend, cost]
---

## Configure Auto-Suspend Appropriately

**Impact: CRITICAL**

Warehouses bill per-second while running. An idle warehouse with auto-suspend disabled or set too high burns credits doing nothing. Conversely, setting auto-suspend too aggressively on ETL warehouses causes constant cold-start overhead.

**Incorrect (default 10-minute suspend for interactive queries):**

```sql
-- Bad: 10-minute idle timeout for a dashboard warehouse
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 600;
```

**Correct (tuned per workload type):**

```sql
-- Interactive / dashboard: suspend fast (1 minute)
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- ETL / scheduled loads: moderate suspend (5 minutes)
-- Avoids constant resume between pipeline steps
CREATE WAREHOUSE etl_wh
  WAREHOUSE_SIZE = 'MEDIUM'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;

-- Batch pipeline with known schedule: immediate suspend
-- Pipeline explicitly starts and the warehouse suspends right after
CREATE WAREHOUSE batch_wh
  WAREHOUSE_SIZE = 'LARGE'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

**Guidelines:**

| Workload Type | Auto-Suspend | Rationale |
|---------------|-------------|-----------|
| Interactive / BI | 60s | Users have gaps between queries |
| ETL pipelines | 300s | Steps run close together, avoid resume overhead |
| Batch jobs | 60s | Known start/end, suspend between runs |
| Data science / ad-hoc | 300s | Long think-time between queries |

**Always set AUTO_RESUME = TRUE.** There is no reason to disable it in production. Warehouse resume takes 1-2 seconds typically.

**Understand auto-suspend timing gaps:** Snowflake checks for idle warehouses approximately every 30 seconds (not continuously). Combined with the 60-second minimum billing, a 5-second query on a suspended warehouse may actually bill for 90-120 seconds. This matters most for short-burst BI patterns with hundreds of daily queries — the idle waste adds up. For long-running ETL jobs (30+ minutes), this is negligible.

**Cache trade-off:** When a warehouse suspends, its local disk cache (SSD) is dropped. If you have repeating queries scanning the same tables, setting auto-suspend too low degrades performance from constant cache-cold restarts. For BI warehouses with high cache hit rates, consider 300s to keep the cache warm.

Reference: [Warehouse Auto-Suspend](https://docs.snowflake.com/en/user-guide/warehouses-overview#auto-suspension-and-auto-resumption)
