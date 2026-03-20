---
title: Align Clustering Keys with Query Filter Predicates
impact: CRITICAL
impactDescription: "10-100x query speedup through micro-partition pruning"
tags: [clustering, schema, partition-pruning, performance]
---

## Align Clustering Keys with Query Filter Predicates

**Impact: CRITICAL**

Snowflake stores data in micro-partitions (~16 MB compressed). Each micro-partition records min/max metadata for every column. When your WHERE clause filters on clustering key columns, Snowflake skips entire micro-partitions — this is **pruning**. A well-chosen clustering key can reduce scanned data from terabytes to megabytes.

**Incorrect (clustering on a column rarely used in filters):**

```sql
-- Bad: Clustering on primary key, but queries always filter by date and region
CREATE TABLE orders (
  order_id NUMBER,
  order_date DATE,
  region VARCHAR,
  amount NUMBER
) CLUSTER BY (order_id);

-- This query scans ALL micro-partitions — no pruning benefit
SELECT * FROM orders WHERE order_date = '2025-01-15' AND region = 'US';
```

**Correct (clustering on the columns actually used in WHERE clauses):**

```sql
-- Good: Cluster on the columns that appear in WHERE / JOIN predicates
CREATE TABLE orders (
  order_id NUMBER,
  order_date DATE,
  region VARCHAR,
  amount NUMBER
) CLUSTER BY (order_date, region);

-- Now this query prunes efficiently — only scans partitions matching date + region
SELECT * FROM orders WHERE order_date = '2025-01-15' AND region = 'US';
```

**How to identify the right columns:**

```sql
-- Check which columns appear most in WHERE clauses for this table
SELECT *
FROM snowflake.account_usage.access_history
WHERE base_objects_accessed LIKE '%ORDERS%'
ORDER BY query_start_time DESC
LIMIT 100;

-- Check current clustering depth (lower = better)
SELECT SYSTEM$CLUSTERING_INFORMATION('orders', '(order_date, region)');
```

**Cluster key column ordering matters:** Put the column with fewer distinct values first (similar to ClickHouse primary key ordering). `(region, order_date)` groups by region first, then date within each region.

Reference: [Clustering Keys & Clustered Tables](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)
