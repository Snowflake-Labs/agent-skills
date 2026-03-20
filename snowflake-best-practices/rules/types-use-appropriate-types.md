---
title: Use Appropriate Data Types
impact: CRITICAL
impactDescription: "Correct types enable pruning, prevent conversion overhead, ensure data integrity"
tags: [types, schema, data-types]
---

## Use Appropriate Data Types

**Impact: CRITICAL**

Snowflake's columnar storage and micro-partition pruning work best with native types. Storing numbers as VARCHAR prevents numeric comparisons, breaks pruning, and wastes storage. Storing dates as strings prevents date arithmetic and partition pruning.

**Incorrect (everything as VARCHAR):**

```sql
-- Bad: Numeric IDs and dates stored as strings
CREATE TABLE orders (
  order_id VARCHAR,       -- Actually a number
  amount VARCHAR,         -- Actually a decimal
  order_date VARCHAR,     -- Actually a date ('2025-01-15')
  quantity VARCHAR        -- Actually an integer
);

-- Comparisons fail silently: '9' > '10' is TRUE for strings
-- No micro-partition pruning on date ranges
-- No SUM/AVG without CAST overhead
```

**Correct (native types matching actual data):**

```sql
-- Good: Proper types enable pruning, aggregation, and integrity
CREATE TABLE orders (
  order_id NUMBER(38,0),
  amount NUMBER(12,2),
  order_date DATE,
  quantity NUMBER(10,0)
);
```

**Type Selection Guide:**

| Data | Use | NOT |
|------|-----|-----|
| Integer IDs | `NUMBER(38,0)` | `VARCHAR` |
| Money / decimal | `NUMBER(12,2)` or `NUMBER(18,4)` | `FLOAT` (precision loss) |
| Dates (no time) | `DATE` | `VARCHAR`, `TIMESTAMP` |
| Timestamps | `TIMESTAMP_LTZ` / `TIMESTAMP_NTZ` | `VARCHAR`, `NUMBER` |
| True/false | `BOOLEAN` | `VARCHAR('Y'/'N')`, `NUMBER(1,0)` |
| Short codes | `VARCHAR` | `NUMBER` (if codes have leading zeros) |
| JSON/dynamic | `VARIANT` | `VARCHAR` (loses query capabilities) |

**Special cases:**
- Phone numbers, zip codes, SSNs → `VARCHAR` (leading zeros matter)
- UUIDs → `VARCHAR(36)` (not a number)
- IP addresses → `VARCHAR` (or `NUMBER` with conversion functions if filtering heavily)

Reference: [Data Types](https://docs.snowflake.com/en/sql-reference/data-types)
