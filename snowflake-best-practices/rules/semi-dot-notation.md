---
title: Use Dot Notation and Bracket Notation Correctly
impact: HIGH
impactDescription: "Prevents NULL results from incorrect path expressions on VARIANT data"
tags: [semi-structured, dot-notation, variant, json, casting]
---

## Use Dot Notation and Bracket Notation Correctly

**Impact: HIGH**

Accessing VARIANT data with wrong syntax silently returns NULL instead of erroring. Understanding Snowflake's path expression rules prevents subtle bugs.

**Dot notation basics:**

```sql
-- Snowflake auto-uppercases unquoted identifiers
-- JSON key "name" must be accessed with lowercase
SELECT src:name FROM my_table;        -- Correct: finds key "name"
SELECT src:NAME FROM my_table;        -- Also finds "name" (case-insensitive by default)
SELECT src:"Name" FROM my_table;      -- Case-sensitive: finds exactly "Name"
```

**Incorrect (uncast VARIANT access):**

```sql
-- Bad: Returns VARIANT type — can cause unexpected behavior in comparisons
SELECT src:amount FROM orders;
```

**Correct (explicit type casting):**

```sql
-- Good: Explicit cast to the correct type
SELECT src:amount::DECIMAL(10,2) FROM orders;

-- Good: Use TRY_ cast for defensive coding
SELECT TRY_CAST(src:amount AS DECIMAL(10,2)) FROM orders;
```

**Bracket notation for special characters and variables:**

```sql
-- Keys with spaces, dots, or special characters need bracket notation
SELECT src['user-id'] FROM events;       -- hyphenated key
SELECT src['first.name'] FROM events;    -- dotted key (not nested!)
SELECT src['123-field'] FROM events;     -- starts with number

-- Nested access combines dot and bracket notation
SELECT src:address['zip-code']::VARCHAR FROM customers;
```

**Traversing nested objects:**

```sql
-- Dot notation chains for nested access
SELECT
  src:user.address.city::VARCHAR AS city,
  src:user.address.state::VARCHAR AS state
FROM events;

-- Equivalent bracket notation
SELECT
  src['user']['address']['city']::VARCHAR AS city
FROM events;
```

**Array access:**

```sql
-- Access array elements by index (0-based)
SELECT src:items[0]:product_id::NUMBER AS first_product
FROM orders;

-- Get array size
SELECT ARRAY_SIZE(src:items) AS item_count
FROM orders;
```

**Common pitfalls:**
| Expression | Result | Why |
|-----------|--------|-----|
| `src:Amount` | NULL | Key is "amount" (lowercase in JSON) |
| `src:user.name` | Value | Traverses nested object |
| `src['user.name']` | NULL (likely) | Looks for literal key "user.name" |
| `src:items.0` | NULL | Use `src:items[0]` for arrays |

**2025 update: Structured types.** Snowflake now supports typed semi-structured columns (`ARRAY(INT)`, `OBJECT(name VARCHAR, age INT)`, `MAP(VARCHAR, INT)`) on standard tables. These provide schema enforcement and can be faster for predictable data shapes. Consider structured types when your JSON schema is stable:

```sql
-- Structured column: Snowflake validates types at insert time
CREATE TABLE events (
  event_id NUMBER,
  tags ARRAY(VARCHAR),
  metadata OBJECT(source VARCHAR, priority INT)
);
```

Reference: [Traversing Semi-Structured Data](https://docs.snowflake.com/en/user-guide/querying-semistructured#traversing-semi-structured-data)
