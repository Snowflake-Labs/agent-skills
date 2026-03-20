---
title: Filter on Clustering Key Columns for Pruning
impact: CRITICAL
impactDescription: "10-1000x reduction in data scanned through micro-partition pruning"
tags: [query, pruning, clustering, performance]
---

## Filter on Clustering Key Columns for Pruning

**Impact: CRITICAL**

Every micro-partition stores min/max metadata for each column. When your WHERE clause matches the clustering key columns, Snowflake eliminates entire micro-partitions without reading them. This is the single most impactful query optimization in Snowflake.

**Incorrect (filtering on non-clustered columns):**

```sql
-- Table is clustered on (order_date, region)
-- Bad: Filtering on a non-clustered column forces full scan
SELECT * FROM orders WHERE customer_name = 'Acme Corp';
-- Scans: 100% of micro-partitions (no pruning possible)
```

**Correct (filtering on clustering key columns):**

```sql
-- Good: Filter on the clustering key columns
SELECT * FROM orders
WHERE order_date = '2025-01-15' AND region = 'US';
-- Scans: <1% of micro-partitions (excellent pruning)
```

**Check pruning effectiveness in query profile:**

```sql
-- After running a query, check the profile for the TableScan node:
-- "Partitions scanned" vs "Partitions total"
-- Good: 50 scanned / 10,000 total (0.5%)
-- Bad: 9,500 scanned / 10,000 total (95%)
```

**Pruning-aware patterns:**

```sql
-- Date range filters prune well
WHERE event_date BETWEEN '2025-01-01' AND '2025-01-31'

-- Equality on low-cardinality leading column prunes well
WHERE region = 'EU' AND event_date >= '2025-01-01'

-- Functions on clustered columns BREAK pruning
-- Bad: TO_CHAR(event_date, 'YYYY-MM') = '2025-01'
-- Good: event_date BETWEEN '2025-01-01' AND '2025-01-31'
```

**Key rule:** Do NOT apply functions to clustering key columns in WHERE clauses. `WHERE YEAR(order_date) = 2025` prevents pruning. Use range predicates instead: `WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'`.

Reference: [Pruning](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions#query-pruning)
