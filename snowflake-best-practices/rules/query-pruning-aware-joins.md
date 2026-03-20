---
title: Filter Tables Before Joining
impact: CRITICAL
impactDescription: "2-10x faster joins by reducing data before the join operation"
tags: [query, join, performance, pruning]
---

## Filter Tables Before Joining

**Impact: CRITICAL**

Apply WHERE filters to each table before joining, not after. Snowflake can prune micro-partitions independently for each side of the join when filters are applied early. Filtering after the join forces Snowflake to materialize the full join result first.

**Incorrect (filtering after the join):**

```sql
-- Bad: Joins ALL orders with ALL customers, then filters
SELECT c.name, o.amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date = '2025-01-15'
  AND c.region = 'US';
-- Snowflake may still push predicates down, but explicit is better
```

**Correct (filtering before or during the join):**

```sql
-- Good: Filter each table to minimize join input
SELECT c.name, o.amount
FROM (SELECT customer_id, amount FROM orders WHERE order_date = '2025-01-15') o
JOIN (SELECT customer_id, name FROM customers WHERE region = 'US') c
  ON o.customer_id = c.customer_id;
```

**Also correct (Snowflake's optimizer usually handles this):**

```sql
-- Acceptable: The optimizer will push predicates down in most cases
-- but CTEs make intent explicit and aid readability
WITH filtered_orders AS (
  SELECT customer_id, amount
  FROM orders
  WHERE order_date = '2025-01-15'
),
filtered_customers AS (
  SELECT customer_id, name
  FROM customers
  WHERE region = 'US'
)
SELECT c.name, o.amount
FROM filtered_orders o
JOIN filtered_customers c ON o.customer_id = c.customer_id;
```

**Join sizing tips:**
- Put the smaller table on the RIGHT side of the JOIN (Snowflake builds a hash table from the right/inner side)
- Use explicit `INNER JOIN` instead of just `JOIN` for clarity
- Avoid `SELECT *` in joins — only select needed columns from each table

**Anti-pattern: Cross joins hidden by WHERE:**

```sql
-- Bad: Accidental cross join filtered down — generates massive intermediate result
SELECT a.name, b.amount
FROM table_a a, table_b b
WHERE a.id = b.id AND a.date = '2025-01-15';

-- Good: Explicit JOIN
SELECT a.name, b.amount
FROM table_a a
INNER JOIN table_b b ON a.id = b.id
WHERE a.date = '2025-01-15';
```

Reference: [Join Strategies](https://docs.snowflake.com/en/user-guide/performance-query#join-optimization)
