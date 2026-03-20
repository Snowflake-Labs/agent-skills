---
title: Choose Medium-Cardinality Columns for Clustering
impact: CRITICAL
impactDescription: "Effective pruning requires the right cardinality range"
tags: [clustering, schema, cardinality, partition-pruning]
---

## Choose Medium-Cardinality Columns for Clustering

**Impact: CRITICAL**

Clustering works by colocating rows with similar values in the same micro-partitions. Very high-cardinality columns (UUIDs, timestamps to the microsecond) produce almost no overlap between partitions — pruning can't skip anything. Very low-cardinality columns (boolean, status with 3 values) group too coarsely to be useful alone.

**Incorrect (clustering on a UUID):**

```sql
-- Bad: Every event_id is unique — micro-partitions have non-overlapping ranges
-- but each partition contains random dates and regions, so no useful pruning
CREATE TABLE events (...) CLUSTER BY (event_id);
```

**Incorrect (clustering on a boolean):**

```sql
-- Bad: Only 2 values — data splits into ~2 groups, minimal pruning benefit
CREATE TABLE events (...) CLUSTER BY (is_active);
```

**Correct (medium-cardinality columns):**

```sql
-- Good: Dates (~365/year) and regions (~10-50) provide excellent pruning
CREATE TABLE events (...) CLUSTER BY (event_date, region);
```

**Cardinality Guide:**

| Cardinality | Examples | Clustering Value |
|-------------|----------|-----------------|
| Very low (< 10) | Boolean, status | Poor alone — combine with another column |
| Low (10-100) | Region, category, department | Good as leading column |
| Medium (100-100K) | Date, city, product_id | Excellent for clustering |
| High (100K-10M) | User_id, customer_id | Acceptable if frequently filtered |
| Very high (10M+) | UUID, timestamp_ntz(9) | Poor — almost no pruning benefit |

**Compound keys help:** Combine a low-cardinality column with a medium one:

```sql
-- region (10 values) + date (365/year) = ~3,650 combinations — ideal for pruning
CLUSTER BY (region, order_date)
```

**Tip:** Use `DATE` truncation for timestamps in clustering keys:

```sql
-- Instead of clustering on a high-cardinality timestamp:
CLUSTER BY (TO_DATE(event_timestamp), region)
```

**Important: Snowflake only uses the first 5 characters of a clustering key for partition pruning.** This means `CLUSTER BY (date_string)` where values look like `'20250115'` (YYYYMMDD format) will only prune on `'20250'` — effectively by year, not by date. Always use native DATE/TIMESTAMP types with truncation instead of string representations.

Reference: [Clustering Keys & Clustered Tables](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)
