---
title: Understand and Leverage the Result Cache
impact: CRITICAL
impactDescription: "Instant query results (0 credits) for repeated queries within 24 hours"
tags: [query, caching, performance, cost]
---

## Understand and Leverage the Result Cache

**Impact: CRITICAL**

When you run an identical query and the underlying data hasn't changed, Snowflake returns the cached result instantly — no warehouse compute needed, zero credits consumed. This is automatic but easy to accidentally defeat.

**How the result cache works:**
- Caches results for 24 hours
- The new query must match the previous query **exactly** — any syntactic difference defeats the cache
- Cache is invalidated if underlying data changes (DML, COPY INTO, etc.)
- No warehouse is needed to serve a cached result
- Does not work with queries on hybrid tables or queries containing external functions

**Incorrect (defeating the result cache):**

```sql
-- Bad: CURRENT_TIMESTAMP changes every second — never hits cache
SELECT *, CURRENT_TIMESTAMP AS query_time
FROM dashboard_summary;

-- Bad: RANDOM() makes the query non-deterministic
SELECT *, RANDOM() AS rand_id
FROM dashboard_summary;

-- Bad: Case differences defeat the cache — even keyword case matters!
-- Given this first query populates the cache:
SELECT DISTINCT(severity) FROM weather_events;
-- These WILL NOT reuse the cache:
select distinct(severity) from weather_events;        -- lowercase keywords
SELECT DISTINCT(severity) FROM weather_events we;     -- added table alias
```

**Correct (cache-friendly patterns):**

```sql
-- Good: Deterministic query — hits cache on repeat
SELECT name, amount FROM orders WHERE order_date = '2025-01-15';

-- Good: For dashboards, use a date parameter instead of CURRENT_DATE
-- so the query is identical for all users during the same day
SELECT region, SUM(amount)
FROM orders
WHERE order_date = '2025-01-15'  -- explicit date, not CURRENT_DATE
GROUP BY region;
```

**Check cache usage:**

```sql
-- Queries served from cache show QUERY_TYPE = 'SELECT' and
-- WAREHOUSE_NAME IS NULL (no warehouse was used)
SELECT query_id, query_text, warehouse_name, execution_time
FROM snowflake.account_usage.query_history
WHERE warehouse_name IS NULL
  AND query_type = 'SELECT'
ORDER BY start_time DESC
LIMIT 20;
```

**Tips for cache hits:**
- Standardize SQL formatting and keyword casing across your team — even `SELECT` vs `select` defeats the cache
- Configure BI tools to use parameterized queries with consistent formatting
- Avoid adding table aliases unless needed — `FROM orders` and `FROM orders o` are different cache keys
- Non-reusable functions: `CURRENT_TIMESTAMP`, `UUID_STRING`, `RANDOM`, `RANDSTR`

Reference: [Using Persisted Query Results](https://docs.snowflake.com/en/user-guide/querying-persisted-results)
