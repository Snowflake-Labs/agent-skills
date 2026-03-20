---
title: Use QUALIFY Instead of Subqueries for Window Function Filtering
impact: CRITICAL
impactDescription: "Simpler SQL, better readability, same performance; Snowflake-native syntax"
tags: [query, qualify, window-function, sql-style]
---

## Use QUALIFY Instead of Subqueries for Window Function Filtering

**Impact: CRITICAL** (code quality and maintainability)

QUALIFY is Snowflake's native clause for filtering on window function results. It eliminates the common pattern of wrapping a query in a subquery just to filter on ROW_NUMBER(). This is both cleaner and avoids unnecessary query nesting.

**Incorrect (subquery pattern):**

```sql
-- Bad: Subquery wrapper just to filter on row_number
SELECT * FROM (
  SELECT
    customer_id,
    order_date,
    amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders
)
WHERE rn = 1;
```

**Correct (QUALIFY):**

```sql
-- Good: QUALIFY filters directly on window functions — no subquery needed
SELECT customer_id, order_date, amount
FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) = 1;
```

**More examples:**

```sql
-- Get top 3 products per category by revenue
SELECT category, product_name, revenue
FROM products
QUALIFY RANK() OVER (PARTITION BY category ORDER BY revenue DESC) <= 3;

-- Deduplicate: keep the latest record per key
SELECT *
FROM raw_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY loaded_at DESC) = 1;

-- Keep rows where running total exceeds threshold
SELECT customer_id, order_date, amount
FROM orders
QUALIFY SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date) > 1000;
```

**QUALIFY execution order:** QUALIFY runs after WHERE, GROUP BY, HAVING, and window functions — same position as the subquery filter, but without the nesting.

```
FROM → WHERE → GROUP BY → HAVING → Window Functions → QUALIFY → ORDER BY → LIMIT
```

**Note:** QUALIFY is Snowflake and Databricks syntax. If cross-database portability is required, use the subquery pattern. For Snowflake-native code, always prefer QUALIFY.

Reference: [QUALIFY](https://docs.snowflake.com/en/sql-reference/constructs/qualify)
