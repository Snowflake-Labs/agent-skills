---
title: VARIANT Column vs FLATTEN — Choose the Right Access Pattern
impact: CRITICAL
impactDescription: "Wrong pattern causes 10x slower queries on semi-structured data"
tags: [semi-structured, variant, flatten, json, performance]
---

## VARIANT Column vs FLATTEN — Choose the Right Access Pattern

**Impact: CRITICAL**

Snowflake stores semi-structured data (JSON, Avro, Parquet) in VARIANT columns. How you query it matters enormously. Direct dot notation on VARIANT is fast for simple access. FLATTEN is needed for arrays but is expensive if misused.

**When to use dot notation (simple key access):**

```sql
-- Good: Direct access to known keys — fast, uses columnar optimization
SELECT
  src:user_id::NUMBER AS user_id,
  src:event_type::VARCHAR AS event_type,
  src:timestamp::TIMESTAMP_LTZ AS event_time
FROM raw_events;
```

**When to use FLATTEN (arrays and nested structures):**

```sql
-- Good: FLATTEN to expand an array into rows
SELECT
  e.src:user_id::NUMBER AS user_id,
  f.value:product_id::NUMBER AS product_id,
  f.value:quantity::NUMBER AS quantity
FROM raw_events e,
  LATERAL FLATTEN(input => e.src:items) f
WHERE e.src:event_type = 'purchase';
```

**Incorrect (unnecessary FLATTEN):**

```sql
-- Bad: FLATTEN on a non-array field — just use dot notation
SELECT f.value:user_id::NUMBER
FROM raw_events,
  LATERAL FLATTEN(input => src) f
WHERE f.key = 'user_id';

-- Good: Direct access
SELECT src:user_id::NUMBER FROM raw_events;
```

**For frequently queried JSON data, materialize into typed columns:**

```sql
-- Best performance: Extract to typed columns in a view or table
CREATE VIEW events_parsed AS
SELECT
  src:user_id::NUMBER AS user_id,
  src:event_type::VARCHAR(50) AS event_type,
  src:timestamp::TIMESTAMP_LTZ AS event_time,
  src:items AS items_array  -- keep complex nested data as VARIANT
FROM raw_events;
```

**Decision guide:**
| Data Shape | Approach |
|-----------|----------|
| Flat JSON with known keys | Dot notation with ::TYPE casting |
| JSON with arrays | LATERAL FLATTEN on the array |
| Deeply nested JSON | FLATTEN with RECURSIVE = TRUE |
| Frequently queried JSON | Materialize into typed columns |

Reference: [Querying Semi-Structured Data](https://docs.snowflake.com/en/user-guide/querying-semistructured)
