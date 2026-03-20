---
title: Use LATERAL FLATTEN Correctly for Arrays
impact: HIGH
impactDescription: "Correct FLATTEN usage prevents missing rows, duplicates, and wrong results"
tags: [semi-structured, flatten, lateral, arrays, json]
---

## Use LATERAL FLATTEN Correctly for Arrays

**Impact: HIGH**

LATERAL FLATTEN is how you expand arrays into rows in Snowflake. Getting it wrong causes missing data (inner join behavior) or duplicated rows (multiple flattens without correlation).

**Correct (basic FLATTEN pattern):**

```sql
-- Expand an array of tags into one row per tag
SELECT
  e.event_id,
  f.value::VARCHAR AS tag
FROM events e,
  LATERAL FLATTEN(input => e.tags) f;
-- Note: Rows with NULL or empty tags array are EXCLUDED (inner join behavior)
```

**Preserve rows with empty/null arrays (outer flatten):**

```sql
-- Good: OUTER => TRUE keeps rows even when array is empty or NULL
SELECT
  e.event_id,
  f.value::VARCHAR AS tag
FROM events e,
  LATERAL FLATTEN(input => e.tags, OUTER => TRUE) f;
-- Rows with no tags now appear with tag = NULL
```

**Incorrect (multiple flattens causing cross-product):**

```sql
-- Bad: Two independent flattens cause a cross-product
SELECT
  e.event_id,
  t.value::VARCHAR AS tag,
  i.value::NUMBER AS item_id
FROM events e,
  LATERAL FLATTEN(input => e.tags) t,
  LATERAL FLATTEN(input => e.items) i;
-- If tags has 3 elements and items has 5, you get 15 rows (cross join!)
```

**Correct (flatten separately to avoid cross-product):**

```sql
-- Good: Flatten separately and join, or restructure your query
SELECT event_id, tag, NULL AS item_id
FROM events, LATERAL FLATTEN(input => tags) f_tags
  WHERE f_tags.value IS NOT NULL
UNION ALL
SELECT event_id, NULL AS tag, value::NUMBER AS item_id
FROM events, LATERAL FLATTEN(input => items) f_items;
```

**FLATTEN output columns:**
| Column | Description |
|--------|-------------|
| `f.seq` | Sequence number (unique per input row) |
| `f.key` | Key name (for objects) or index (for arrays) |
| `f.path` | Path to the element |
| `f.index` | Array index (0-based) |
| `f.value` | The actual value |
| `f.this` | The entire array/object being flattened |

**Nested array flattening:**

```sql
-- Flatten array of objects, then access object keys
SELECT
  o.order_id,
  item.value:product_id::NUMBER AS product_id,
  item.value:quantity::NUMBER AS quantity,
  item.value:price::DECIMAL(10,2) AS price
FROM orders o,
  LATERAL FLATTEN(input => o.line_items) item;
```

Reference: [FLATTEN](https://docs.snowflake.com/en/sql-reference/functions/flatten)
