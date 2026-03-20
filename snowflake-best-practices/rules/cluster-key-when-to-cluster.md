---
title: Only Cluster Tables That Need It
impact: CRITICAL
impactDescription: "Avoids unnecessary Automatic Clustering costs on small or well-pruned tables"
tags: [clustering, cost, schema]
---

## Only Cluster Tables That Need It

**Impact: CRITICAL**

Automatic Clustering is a background service that costs credits. It continuously reorganizes micro-partitions to maintain clustering. On small tables or tables that already prune well naturally (because data arrives in order), this is wasted money.

**Incorrect (clustering a small table):**

```sql
-- Bad: 50,000 rows fits in a few micro-partitions — clustering adds cost, zero benefit
CREATE TABLE dim_regions (
  region_id NUMBER,
  region_name VARCHAR,
  country VARCHAR
) CLUSTER BY (region_name);
```

**Incorrect (clustering when natural ordering is sufficient):**

```sql
-- Bad: Append-only time-series data naturally clusters by timestamp
-- because new rows land in new micro-partitions in order
CREATE TABLE events (
  event_time TIMESTAMP_LTZ,
  event_type VARCHAR,
  payload VARIANT
) CLUSTER BY (event_time);
-- Automatic Clustering will spend credits rearranging data that was already ordered
```

**Correct (cluster large tables with poor natural pruning):**

```sql
-- Good: 5 billion rows, queries filter by region but data arrives in random region order
-- Clustering actually helps here
CREATE TABLE web_events (
  event_time TIMESTAMP_LTZ,
  region VARCHAR,
  user_id NUMBER,
  page_url VARCHAR
) CLUSTER BY (region, TO_DATE(event_time));
```

**When to cluster:**
- Table is large (> 1 TB or > 1 billion rows)
- Queries show poor pruning (scan ratio > 50% of partitions)
- Data arrives in a different order than the common query filter
- Query profile shows significant "TableScan" time

**When NOT to cluster:**
- Table is small (< 500 MB or < 10 million rows)
- Data is append-only and queries filter on the arrival-time column (naturally clustered)
- Table is rarely queried
- Table is transient / temporary

**Important: Manual reclustering is deprecated.** `ALTER TABLE ... RECLUSTER` was deprecated in May 2020 and removed from most accounts. Defining a clustering key now implicitly enables Automatic Clustering. Use `ALTER TABLE ... SUSPEND RECLUSTER` / `RESUME RECLUSTER` to control costs.

**Tip: Initial clustering via INSERT OVERWRITE is much cheaper.** For a first-time sort of a large existing table, a one-time INSERT OVERWRITE with ORDER BY can be 5x cheaper and faster than waiting for Automatic Clustering to converge:

```sql
-- Initial sort: far cheaper than waiting for background auto-clustering
ALTER WAREHOUSE load_wh SET WAREHOUSE_SIZE = 'XLARGE';

INSERT OVERWRITE INTO web_events
SELECT * FROM web_events
ORDER BY region, TO_DATE(event_time);

-- Then let Automatic Clustering handle incremental maintenance
ALTER TABLE web_events CLUSTER BY (region, TO_DATE(event_time));
```

**Check if clustering would help:**

```sql
-- Check pruning efficiency for your most common query pattern
SELECT SYSTEM$CLUSTERING_INFORMATION('web_events', '(region, TO_DATE(event_time))');

-- Look for: average_overlaps > 2.0 and average_depth > 2.0 means clustering would help
```

Reference: [Automatic Clustering](https://docs.snowflake.com/en/user-guide/tables-auto-reclustering)
