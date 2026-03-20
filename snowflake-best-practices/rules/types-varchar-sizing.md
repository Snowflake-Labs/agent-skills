---
title: Don't Micro-Optimize VARCHAR Size
impact: CRITICAL
impactDescription: "Prevents unnecessary schema debates; Snowflake stores actual length regardless of declared max"
tags: [types, varchar, schema, storage]
---

## Don't Micro-Optimize VARCHAR Size

**Impact: CRITICAL** (frequently misunderstood)

Unlike traditional databases (Oracle, SQL Server, MySQL), Snowflake does NOT allocate storage based on declared VARCHAR length. `VARCHAR(10)` and `VARCHAR(16777216)` (the 16 MB default) use **identical storage** for the same actual string. Snowflake compresses and stores only the actual bytes.

> **2025 update:** VARCHAR max size increased from 16 MB to 128 MB (`VARCHAR(134217728)`). VARIANT/ARRAY/OBJECT max also increased from 16 MB to 128 MB. The default VARCHAR (no length specified) remains 16 MB — you must explicitly declare the larger size if needed.

**Incorrect (micro-optimizing VARCHAR lengths like a traditional RDBMS):**

```sql
-- Bad: Wasting time debating string lengths — has zero storage impact in Snowflake
CREATE TABLE customers (
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  email VARCHAR(254),
  city VARCHAR(100),
  state VARCHAR(2),
  country VARCHAR(3)
);
```

**Correct (use VARCHAR with reasonable or default limits):**

```sql
-- Good: Default VARCHAR (16 MB max) is fine for most columns
CREATE TABLE customers (
  first_name VARCHAR,
  last_name VARCHAR,
  email VARCHAR,
  city VARCHAR,
  state VARCHAR,
  country VARCHAR
);
```

**When specified lengths ARE useful:**
- As documentation / data contracts (VARCHAR(2) for state codes communicates intent)
- For data validation (INSERT will fail if value exceeds declared length)
- For external tool compatibility (some BI tools read declared length)

**Reasonable approach:**

```sql
-- Acceptable: Use lengths as documentation, not optimization
CREATE TABLE customers (
  first_name VARCHAR(100),   -- Documents: "names up to 100 chars"
  email VARCHAR(320),        -- Documents: "RFC 5321 max email length"
  description VARCHAR        -- No meaningful limit to document
);
```

**Key point:** Do NOT spend time optimizing VARCHAR lengths for storage or performance in Snowflake. It has zero effect on either. Spend that time on clustering keys and warehouse sizing instead.

Reference: [VARCHAR Data Type](https://docs.snowflake.com/en/sql-reference/data-types-text#varchar)
