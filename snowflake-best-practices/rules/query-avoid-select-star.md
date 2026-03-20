---
title: Avoid SELECT * in Production Queries
impact: CRITICAL
impactDescription: "2-10x I/O reduction; Snowflake is columnar — fewer columns = less data scanned"
tags: [query, performance, columnar, select-star]
---

## Avoid SELECT * in Production Queries

**Impact: CRITICAL**

Snowflake stores data in a columnar format. Each column is stored and compressed independently. `SELECT *` forces Snowflake to read every column from storage, even if you only need 3 of 50. On wide tables, this can mean 10-20x more I/O.

**Incorrect:**

```sql
-- Bad: Reads all 50 columns from a wide fact table
SELECT * FROM fact_web_events WHERE event_date = '2025-01-15';
```

**Correct:**

```sql
-- Good: Only reads the 4 columns needed — columnar storage skips the rest
SELECT event_id, user_id, event_type, event_date
FROM fact_web_events
WHERE event_date = '2025-01-15';
```

**Why this matters more in Snowflake than row-stores:**
- Row stores read entire rows regardless — SELECT * has minimal penalty
- Columnar stores read only requested columns — SELECT * negates the #1 advantage
- Wide tables (50+ columns) with SELECT * can be 10-20x slower than selecting 5 columns

**Exceptions where SELECT * is acceptable:**
- Ad-hoc exploration on small tables (`LIMIT 10`)
- `CREATE TABLE AS SELECT * FROM ...` when you genuinely need all columns
- `INSERT INTO target SELECT * FROM source` when schemas match

**CTAS best practice:**

```sql
-- If you need all columns, at least be explicit about it
CREATE TABLE my_subset AS
SELECT event_id, user_id, event_type, event_date, payload
FROM fact_web_events
WHERE event_date >= '2025-01-01';
```

Reference: [Query Performance](https://docs.snowflake.com/en/user-guide/performance-query)
