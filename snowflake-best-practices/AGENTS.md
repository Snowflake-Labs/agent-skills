# Snowflake Best Practices

**25 rules** | Generated March 2026

> **Note:**
> This document is compiled from individual rule files in `rules/`.
> It is designed for AI agents and LLMs to reference when designing,
> optimizing, or maintaining Snowflake databases.

---

## Table of Contents

1. [Warehouse Configuration](#1-warehouse-configuration)
   - 1.1 Configure Auto-Suspend Appropriately — **CRITICAL**
   - 1.2 Use Query Acceleration for Outlier Queries — **HIGH**
   - 1.3 Right-Size Your Warehouse — **CRITICAL**
   - 1.4 Scale Up for Complexity, Scale Out for Concurrency — **CRITICAL**
2. [Clustering Keys](#2-clustering-keys)
   - 2.1 Choose Medium-Cardinality Columns for Clustering — **CRITICAL**
   - 2.2 Align Clustering Keys with Query Filter Predicates — **CRITICAL**
   - 2.3 Only Cluster Tables That Need It — **CRITICAL**
3. [Data Types](#3-data-types)
   - 3.1 Choose the Right TIMESTAMP Variant — **CRITICAL**
   - 3.2 Use Appropriate Data Types — **CRITICAL**
   - 3.3 Don't Micro-Optimize VARCHAR Size — **CRITICAL**
4. [Query Optimization](#4-query-optimization)
   - 4.1 Avoid SELECT * in Production Queries — **CRITICAL**
   - 4.2 Filter on Clustering Key Columns for Pruning — **CRITICAL**
   - 4.3 Filter Tables Before Joining — **CRITICAL**
   - 4.4 Understand and Leverage the Result Cache — **CRITICAL**
   - 4.5 Use QUALIFY Instead of Subqueries for Window Function Filtering — **CRITICAL**
5. [Data Loading](#5-data-loading)
   - 5.1 Choose COPY INTO vs Snowpipe Based on Latency Needs — **CRITICAL**
   - 5.2 Size Files for Optimal Parallel Loading — **CRITICAL**
   - 5.3 Configure File Format Options Correctly — **HIGH**
   - 5.4 Use Proper Staging Patterns — **HIGH**
6. [Semi-Structured Data](#6-semi-structured-data)
   - 6.1 Use Dot Notation and Bracket Notation Correctly — **HIGH**
   - 6.2 Use LATERAL FLATTEN Correctly for Arrays — **HIGH**
   - 6.3 VARIANT Column vs FLATTEN — Choose the Right Access Pattern — **CRITICAL**
7. [Cost Control](#7-cost-control)
   - 7.1 Design for Credit-Aware Architecture — **CRITICAL**
   - 7.2 Set Resource Monitors to Prevent Runaway Costs — **CRITICAL**
   - 7.3 Set Statement Timeouts to Kill Runaway Queries — **HIGH**

---

## 1. Warehouse Configuration

### 1.1 Configure Auto-Suspend Appropriately

**Impact: CRITICAL** (Prevents idle warehouse charges; typical 30-70% cost savings)

Warehouses bill per-second while running. An idle warehouse with auto-suspend disabled or set too high burns credits doing nothing. Conversely, setting auto-suspend too aggressively on ETL warehouses causes constant cold-start overhead.

**Incorrect (default 10-minute suspend for interactive queries):**

```sql
-- Bad: 10-minute idle timeout for a dashboard warehouse
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 600;
```

**Correct (tuned per workload type):**

```sql
-- Interactive / dashboard: suspend fast (1 minute)
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- ETL / scheduled loads: moderate suspend (5 minutes)
-- Avoids constant resume between pipeline steps
CREATE WAREHOUSE etl_wh
  WAREHOUSE_SIZE = 'MEDIUM'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;

-- Batch pipeline with known schedule: immediate suspend
-- Pipeline explicitly starts and the warehouse suspends right after
CREATE WAREHOUSE batch_wh
  WAREHOUSE_SIZE = 'LARGE'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

Reference: [https://docs.snowflake.com/en/user-guide/warehouses-overview#auto-suspension-and-auto-resumption](https://docs.snowflake.com/en/user-guide/warehouses-overview#auto-suspension-and-auto-resumption)

### 1.2 Use Query Acceleration for Outlier Queries

**Impact: HIGH** (Up to 8x faster for outlier queries in ad-hoc workloads)

The Query Acceleration Service (QAS) offloads portions of a query to shared compute resources. It helps most when a workload has a mix of fast and slow queries — the outlier slow queries get accelerated without sizing up the warehouse for the common case.

**Incorrect (oversizing the warehouse because of occasional slow queries):**

```sql
-- Bad: Warehouse is X-Large because 5% of queries are slow
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'X-LARGE'
  AUTO_SUSPEND = 60;
-- 95% of queries finish in 2 seconds on X-Small, but a few table scans take 3 minutes
```

**Correct (right-sized warehouse + QAS for outliers):**

```sql
-- Good: Keep warehouse small, enable QAS for the long-tail
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  ENABLE_QUERY_ACCELERATION = TRUE
  QUERY_ACCELERATION_MAX_SCALE_FACTOR = 4;
```

Reference: [https://docs.snowflake.com/en/user-guide/query-acceleration-service](https://docs.snowflake.com/en/user-guide/query-acceleration-service)

### 1.3 Right-Size Your Warehouse

**Impact: CRITICAL** (2-10x cost reduction; prevents both under-provisioning and overspending)

Snowflake warehouses double in compute with each size increment (XS→S→M→L). Picking a warehouse two sizes too large costs 4x more. Picking one too small makes queries slower, not cheaper — Snowflake bills per-second with a 60-second minimum.

**Incorrect (oversized warehouse for simple queries):**

```sql
-- Bad: XL warehouse for dashboard queries hitting small tables
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'X-LARGE'
  AUTO_SUSPEND = 600;
```

**Correct (start small, scale based on evidence):**

```sql
-- Good: Start with X-Small, monitor query profile
CREATE WAREHOUSE dashboard_wh
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- Check if queries are spilling to disk (sign warehouse is too small)
SELECT query_id, warehouse_size,
  bytes_spilled_to_local_storage,
  bytes_spilled_to_remote_storage
FROM snowflake.account_usage.query_history
WHERE warehouse_name = 'DASHBOARD_WH'
  AND bytes_spilled_to_remote_storage > 0
ORDER BY start_time DESC
LIMIT 20;
```

Reference: [https://docs.snowflake.com/en/user-guide/warehouses-considerations](https://docs.snowflake.com/en/user-guide/warehouses-considerations)

### 1.4 Scale Up for Complexity, Scale Out for Concurrency

**Impact: CRITICAL** (Correct scaling strategy prevents both poor performance and wasted spend)

Snowflake offers two scaling dimensions: **size** (scale up) and **multi-cluster** (scale out). Using the wrong one wastes credits without solving the problem.
- **Scale UP** (larger warehouse): When individual queries are slow because they process too much data. A bigger warehouse adds more compute nodes to a single query.
- **Scale OUT** (multi-cluster): When queries queue because too many run concurrently. Multi-cluster adds parallel copies of the warehouse.

**Incorrect (using multi-cluster to fix slow queries):**

```sql
-- Bad: Query takes 5 minutes, adding clusters won't help a single slow query
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'SMALL'
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 5;
```

**Correct (scale up for slow queries):**

```sql
-- Good: Single slow query → increase warehouse size
ALTER WAREHOUSE analytics_wh SET WAREHOUSE_SIZE = 'MEDIUM';
```

**Incorrect (using larger warehouse to fix queueing):**

```sql
-- Bad: 50 concurrent users queueing → bigger warehouse doesn't add concurrency
ALTER WAREHOUSE dashboard_wh SET WAREHOUSE_SIZE = 'X-LARGE';
```

**Correct (scale out for concurrency):**

```sql
-- Good: Many concurrent users → multi-cluster
ALTER WAREHOUSE dashboard_wh SET
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 3
  SCALING_POLICY = 'STANDARD';
```

Reference: [https://docs.snowflake.com/en/user-guide/warehouses-multicluster](https://docs.snowflake.com/en/user-guide/warehouses-multicluster)

---

## 2. Clustering Keys

### 2.1 Choose Medium-Cardinality Columns for Clustering

**Impact: CRITICAL** (Effective pruning requires the right cardinality range)

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

Reference: [https://docs.snowflake.com/en/user-guide/tables-clustering-keys](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)

### 2.2 Align Clustering Keys with Query Filter Predicates

**Impact: CRITICAL** (10-100x query speedup through micro-partition pruning)

Snowflake stores data in micro-partitions (~16 MB compressed). Each micro-partition records min/max metadata for every column. When your WHERE clause filters on clustering key columns, Snowflake skips entire micro-partitions — this is **pruning**. A well-chosen clustering key can reduce scanned data from terabytes to megabytes.

**Incorrect (clustering on a column rarely used in filters):**

```sql
-- Bad: Clustering on primary key, but queries always filter by date and region
CREATE TABLE orders (
  order_id NUMBER,
  order_date DATE,
  region VARCHAR,
  amount NUMBER
) CLUSTER BY (order_id);

-- This query scans ALL micro-partitions — no pruning benefit
SELECT * FROM orders WHERE order_date = '2025-01-15' AND region = 'US';
```

**Correct (clustering on the columns actually used in WHERE clauses):**

```sql
-- Good: Cluster on the columns that appear in WHERE / JOIN predicates
CREATE TABLE orders (
  order_id NUMBER,
  order_date DATE,
  region VARCHAR,
  amount NUMBER
) CLUSTER BY (order_date, region);

-- Now this query prunes efficiently — only scans partitions matching date + region
SELECT * FROM orders WHERE order_date = '2025-01-15' AND region = 'US';
```

Reference: [https://docs.snowflake.com/en/user-guide/tables-clustering-keys](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)

### 2.3 Only Cluster Tables That Need It

**Impact: CRITICAL** (Avoids unnecessary Automatic Clustering costs on small or well-pruned tables)

Automatic Clustering is a background service that costs credits. It continuously reorganizes micro-partitions to maintain clustering. On small tables or tables that already prune well naturally (because data arrives in order), this is wasted money.

**Incorrect (clustering a small table):**

```sql
-- Bad: 50,000 rows fits in a few micro-partitions — clustering adds cost, zero benefit
CREATE TABLE dim_regions (
  region_id NUMBER,
  region_name VARCHAR,
  country VARCHAR
) CLUSTER BY (region_name);
```

**Incorrect (clustering when natural ordering is sufficient):**

```sql
-- Bad: Append-only time-series data naturally clusters by timestamp
-- because new rows land in new micro-partitions in order
CREATE TABLE events (
  event_time TIMESTAMP_LTZ,
  event_type VARCHAR,
  payload VARIANT
) CLUSTER BY (event_time);
-- Automatic Clustering will spend credits rearranging data that was already ordered
```

**Correct (cluster large tables with poor natural pruning):**

```sql
-- Good: 5 billion rows, queries filter by region but data arrives in random region order
-- Clustering actually helps here
CREATE TABLE web_events (
  event_time TIMESTAMP_LTZ,
  region VARCHAR,
  user_id NUMBER,
  page_url VARCHAR
) CLUSTER BY (region, TO_DATE(event_time));
```

Reference: [https://docs.snowflake.com/en/user-guide/tables-auto-reclustering](https://docs.snowflake.com/en/user-guide/tables-auto-reclustering)

---

## 3. Data Types

### 3.1 Choose the Right TIMESTAMP Variant

**Impact: CRITICAL** (Prevents timezone bugs in analytics, ETL, and cross-region queries)

Snowflake has three TIMESTAMP types. Using the wrong one causes silent timezone bugs — queries return wrong results without errors. The most common mistake is using TIMESTAMP_NTZ for event data, which discards timezone information.
**The three types:**
| Type | Stores Timezone? | Conversion on Read? | Use For |
|------|------------------|---------------------|---------|
| `TIMESTAMP_LTZ` | Yes (implicitly, as UTC) | Converts to session timezone | Event timestamps, audit logs, "when did this happen?" |
| `TIMESTAMP_NTZ` | No | No conversion | Business dates, schedules, "meeting at 3pm" (no TZ needed) |
| `TIMESTAMP_TZ` | Yes (explicitly, preserves original TZ) | No conversion (shows stored TZ) | Multi-timezone display, "show the user's local time" |

**Incorrect (NTZ for event data):**

```sql
-- Bad: Event time stored without timezone — ambiguous
CREATE TABLE events (
  event_time TIMESTAMP_NTZ  -- Is this UTC? PST? Unknown.
);

-- Two users in different timezones see the same raw value
-- but interpret it differently. Reports are wrong for one of them.
```

**Correct (LTZ for event data):**

```sql
-- Good: LTZ stores as UTC, displays in session timezone
CREATE TABLE events (
  event_time TIMESTAMP_LTZ  -- Unambiguous: stored as UTC internally
);

-- User in PST sees PST, user in UTC sees UTC — same underlying moment
```

**Correct (NTZ for business dates):**

```sql
-- Good: A schedule time is inherently local — no timezone conversion wanted
CREATE TABLE meetings (
  meeting_time TIMESTAMP_NTZ  -- "3:00 PM" means 3:00 PM, period
);
```

**Correct (TZ for multi-timezone display):**

```sql
-- Good: Preserves the original timezone for display
CREATE TABLE global_events (
  local_event_time TIMESTAMP_TZ  -- '2025-01-15 10:00:00 +09:00' stays as Tokyo time
);
```

Reference: [https://docs.snowflake.com/en/sql-reference/data-types-datetime#timestamp](https://docs.snowflake.com/en/sql-reference/data-types-datetime#timestamp)

### 3.2 Use Appropriate Data Types

**Impact: CRITICAL** (Correct types enable pruning, prevent conversion overhead, ensure data integrity)

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

Reference: [https://docs.snowflake.com/en/sql-reference/data-types](https://docs.snowflake.com/en/sql-reference/data-types)

### 3.3 Don't Micro-Optimize VARCHAR Size

**Impact: CRITICAL** (Prevents unnecessary schema debates; Snowflake stores actual length regardless of declared max)

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

Reference: [https://docs.snowflake.com/en/sql-reference/data-types-text#varchar](https://docs.snowflake.com/en/sql-reference/data-types-text#varchar)

---

## 4. Query Optimization

### 4.1 Avoid SELECT * in Production Queries

**Impact: CRITICAL** (2-10x I/O reduction; Snowflake is columnar — fewer columns = less data scanned)

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

Reference: [https://docs.snowflake.com/en/user-guide/performance-query](https://docs.snowflake.com/en/user-guide/performance-query)

### 4.2 Filter on Clustering Key Columns for Pruning

**Impact: CRITICAL** (10-1000x reduction in data scanned through micro-partition pruning)

Every micro-partition stores min/max metadata for each column. When your WHERE clause matches the clustering key columns, Snowflake eliminates entire micro-partitions without reading them. This is the single most impactful query optimization in Snowflake.

**Incorrect (filtering on non-clustered columns):**

```sql
-- Table is clustered on (order_date, region)
-- Bad: Filtering on a non-clustered column forces full scan
SELECT * FROM orders WHERE customer_name = 'Acme Corp';
-- Scans: 100% of micro-partitions (no pruning possible)
```

**Correct (filtering on clustering key columns):**

```sql
-- Good: Filter on the clustering key columns
SELECT * FROM orders
WHERE order_date = '2025-01-15' AND region = 'US';
-- Scans: <1% of micro-partitions (excellent pruning)
```

Reference: [https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions#query-pruning](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions#query-pruning)

### 4.3 Filter Tables Before Joining

**Impact: CRITICAL** (2-10x faster joins by reducing data before the join operation)

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

Reference: [https://docs.snowflake.com/en/user-guide/performance-query#join-optimization](https://docs.snowflake.com/en/user-guide/performance-query#join-optimization)

### 4.4 Understand and Leverage the Result Cache

**Impact: CRITICAL** (Instant query results (0 credits) for repeated queries within 24 hours)

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

Reference: [https://docs.snowflake.com/en/user-guide/querying-persisted-results](https://docs.snowflake.com/en/user-guide/querying-persisted-results)

### 4.5 Use QUALIFY Instead of Subqueries for Window Function Filtering

**Impact: CRITICAL** (Simpler SQL, better readability, same performance; Snowflake-native syntax)

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

Reference: [https://docs.snowflake.com/en/sql-reference/constructs/qualify](https://docs.snowflake.com/en/sql-reference/constructs/qualify)

---

## 5. Data Loading

### 5.1 Choose COPY INTO vs Snowpipe Based on Latency Needs

**Impact: CRITICAL** (Right loading method avoids wasted credits (batch) or missed SLAs (streaming))

Snowflake offers three data loading methods. Choosing the wrong one wastes credits or misses latency targets.
| Method | Latency | Cost Model | Best For |
|--------|---------|-----------|----------|
| COPY INTO | Minutes | Warehouse credits | Batch ETL, scheduled loads |
| Snowpipe | ~1 minute | Serverless credits | Continuous file arrival |
| Snowpipe Streaming | Seconds | Serverless credits | Real-time event streams |

**Incorrect (wrong loading method for the use case):**

```sql
-- Bad: Running COPY INTO every minute via cron — wasteful, use Snowpipe instead
-- This keeps a warehouse running continuously for what should be event-driven loads
COPY INTO raw.events FROM @my_stage/events/ FILE_FORMAT = (TYPE = PARQUET);
-- Scheduled every 1 minute via external cron — burns warehouse credits non-stop
```

**Correct (COPY INTO for batch — you control the warehouse):**

```sql
-- Good: Scheduled batch load (e.g., hourly via task or orchestrator)
COPY INTO raw.events
FROM @my_stage/events/
PATTERN = '.*2025-01-15.*[.]parquet'
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
```

**Correct (Snowpipe for continuous auto-ingest on file arrival):**

```sql
-- Good: Auto-ingest when files land in S3/GCS/Azure
CREATE PIPE raw.events_pipe
  AUTO_INGEST = TRUE
AS
COPY INTO raw.events
FROM @my_stage/events/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
```

Reference: [https://docs.snowflake.com/en/user-guide/data-load-overview](https://docs.snowflake.com/en/user-guide/data-load-overview)

### 5.2 Size Files for Optimal Parallel Loading

**Impact: CRITICAL** (10-50x faster loads; Snowflake parallelizes by file, not within files)

Snowflake loads files in parallel — one thread per file. If you have one 10GB file, only one thread works. If you have 100 files of 100MB each, Snowflake uses 100 threads. File sizing is the #1 data loading optimization.

**Incorrect:**

```sql
-- Bad: Single massive file — only one thread loads it
COPY INTO my_table FROM @my_stage/giant_file_10gb.csv;
-- Result: Slow, serialized load
```

**Correct:**

```sql
-- Good: Pre-split into 100-250MB compressed files
-- Use naming convention that enables pattern matching
COPY INTO my_table
FROM @my_stage/data/
PATTERN = '.*[.]csv[.]gz'
FILE_FORMAT = (TYPE = CSV COMPRESSION = GZIP);
-- Result: Parallel load across all files
```

Reference: [https://docs.snowflake.com/en/user-guide/data-load-considerations-prepare](https://docs.snowflake.com/en/user-guide/data-load-considerations-prepare)

### 5.3 Configure File Format Options Correctly

**Impact: HIGH** (Prevents silent data corruption from mismatched format options)

Incorrect file format options cause silent data corruption — wrong columns, truncated values, or null where data should exist. Always create named file formats rather than inlining options.

**Incorrect (inline options, easy to get wrong):**

```sql
-- Bad: Inline options are error-prone and not reusable
COPY INTO my_table FROM @my_stage
FILE_FORMAT = (TYPE = CSV FIELD_DELIMITER = ',' SKIP_HEADER = 1
  RECORD_DELIMITER = '\n' FIELD_OPTIONALLY_ENCLOSED_BY = '"');
```

**Correct (named file format):**

```sql
-- Good: Create a reusable, documented file format
CREATE FILE FORMAT IF NOT EXISTS my_db.public.csv_standard
  TYPE = CSV
  FIELD_DELIMITER = ','
  RECORD_DELIMITER = '\n'
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('NULL', 'null', '\\N', '')
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE
  TRIM_SPACE = TRUE
  COMMENT = 'Standard CSV with headers, comma-delimited, double-quote enclosed';

COPY INTO my_table FROM @my_stage FILE_FORMAT = my_db.public.csv_standard;
```

Reference: [https://docs.snowflake.com/en/sql-reference/sql/create-file-format](https://docs.snowflake.com/en/sql-reference/sql/create-file-format)

### 5.4 Use Proper Staging Patterns

**Impact: HIGH** (Clean separation of raw, validated, and production data prevents data quality issues)

Load data into a raw staging layer first, then validate and transform. Loading directly into production tables risks corrupt or partial data reaching consumers.

**Incorrect (loading directly into production):**

```sql
-- Bad: Raw CSV data goes straight into the table users query
COPY INTO production.customers
FROM @external_stage/customers/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1);
-- If the file has bad rows, production is corrupted
```

**Correct (raw → staging → production pattern):**

```sql
-- Step 1: Load raw data with ON_ERROR = CONTINUE to capture everything
COPY INTO raw.customers_load
FROM @external_stage/customers/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)
ON_ERROR = CONTINUE;

-- Step 2: Validate and transform into staging
CREATE OR REPLACE TABLE staging.customers AS
SELECT
  $1::NUMBER AS customer_id,
  TRIM($2)::VARCHAR AS name,
  TRY_TO_DATE($3, 'YYYY-MM-DD') AS signup_date,
  $4::VARCHAR AS email
FROM raw.customers_load
WHERE TRY_TO_NUMBER($1) IS NOT NULL  -- skip bad rows
  AND TRY_TO_DATE($3, 'YYYY-MM-DD') IS NOT NULL;

-- Step 3: Merge into production
MERGE INTO production.customers t
USING staging.customers s ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET
  name = s.name, signup_date = s.signup_date, email = s.email
WHEN NOT MATCHED THEN INSERT
  (customer_id, name, signup_date, email)
  VALUES (s.customer_id, s.name, s.signup_date, s.email);
```

Reference: [https://docs.snowflake.com/en/user-guide/data-load-local-file-system-create-stage](https://docs.snowflake.com/en/user-guide/data-load-local-file-system-create-stage)

---

## 6. Semi-Structured Data

### 6.1 Use Dot Notation and Bracket Notation Correctly

**Impact: HIGH** (Prevents NULL results from incorrect path expressions on VARIANT data)

Accessing VARIANT data with wrong syntax silently returns NULL instead of erroring. Understanding Snowflake's path expression rules prevents subtle bugs.
**Dot notation basics:**

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

Reference: [https://docs.snowflake.com/en/user-guide/querying-semistructured#traversing-semi-structured-data](https://docs.snowflake.com/en/user-guide/querying-semistructured#traversing-semi-structured-data)

### 6.2 Use LATERAL FLATTEN Correctly for Arrays

**Impact: HIGH** (Correct FLATTEN usage prevents missing rows, duplicates, and wrong results)

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

Reference: [https://docs.snowflake.com/en/sql-reference/functions/flatten](https://docs.snowflake.com/en/sql-reference/functions/flatten)

### 6.3 VARIANT Column vs FLATTEN — Choose the Right Access Pattern

**Impact: CRITICAL** (Wrong pattern causes 10x slower queries on semi-structured data)

Snowflake stores semi-structured data (JSON, Avro, Parquet) in VARIANT columns. How you query it matters enormously. Direct dot notation on VARIANT is fast for simple access. FLATTEN is needed for arrays but is expensive if misused.
**When to use dot notation (simple key access):**

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

Reference: [https://docs.snowflake.com/en/user-guide/querying-semistructured](https://docs.snowflake.com/en/user-guide/querying-semistructured)

---

## 7. Cost Control

### 7.1 Design for Credit-Aware Architecture

**Impact: CRITICAL** (Architectural decisions that reduce Snowflake spend by 30-70%)

Every Snowflake operation consumes credits. Understanding the cost model lets you make architectural choices that dramatically reduce spend without sacrificing performance.
**Credit consumption model:**
| Resource | Cost Driver | Optimization |
|----------|------------|-------------|
| Warehouses | Size × active time (per-second, 60s min) | Right-size, auto-suspend |
| Snowpipe | 0.06 credits/file | Batch files, avoid tiny files |
| Auto-clustering | Data reorganization | Only cluster tables >1TB |
| Materialized views | Maintenance compute | Use sparingly, prefer Dynamic Tables |
| Serverless tasks | Compute for task runs | Schedule efficiently |

**Incorrect (oversized warehouse for small queries):**

```sql
-- Bad: 4XL warehouse for a query scanning 100MB
ALTER WAREHOUSE SET WAREHOUSE_SIZE = 'X4LARGE';
SELECT COUNT(*) FROM small_table WHERE status = 'active';
-- Cost: Minimum 60 seconds × 128 credits/hour = 2.13 credits
```

**Correct (right-sized warehouse):**

```sql
-- Good: XS warehouse for small queries
ALTER WAREHOUSE SET WAREHOUSE_SIZE = 'XSMALL';
SELECT COUNT(*) FROM small_table WHERE status = 'active';
-- Cost: Minimum 60 seconds × 1 credit/hour = 0.017 credits
```

Reference: [https://docs.snowflake.com/en/user-guide/cost-understanding-compute](https://docs.snowflake.com/en/user-guide/cost-understanding-compute)

### 7.2 Set Resource Monitors to Prevent Runaway Costs

**Impact: CRITICAL** (Prevents surprise bills from runaway queries or misconfigured warehouses)

Without resource monitors, a single runaway query or misconfigured warehouse can consume unlimited credits. Resource monitors are Snowflake's built-in cost guardrails.

**Incorrect (no resource monitor):**

```sql
-- Bad: Warehouse with no spending controls
CREATE WAREHOUSE analytics_wh
  WAREHOUSE_SIZE = 'LARGE'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
-- A bad query could burn hundreds of credits before anyone notices
```

**Correct (resource monitor with alerts and hard limit):**

```sql
-- Good: Create a resource monitor with escalating actions
CREATE RESOURCE MONITOR analytics_monitor
  WITH CREDIT_QUOTA = 1000
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 75 PERCENT DO NOTIFY
    ON 90 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND
    ON 110 PERCENT DO SUSPEND_IMMEDIATE;

-- Assign to a specific warehouse
ALTER WAREHOUSE analytics_wh SET RESOURCE_MONITOR = analytics_monitor;

-- Or set an account-level monitor (catches everything)
ALTER ACCOUNT SET RESOURCE_MONITOR = account_monitor;
```

Reference: [https://docs.snowflake.com/en/user-guide/resource-monitors](https://docs.snowflake.com/en/user-guide/resource-monitors), [https://docs.snowflake.com/en/user-guide/budgets](https://docs.snowflake.com/en/user-guide/budgets)

### 7.3 Set Statement Timeouts to Kill Runaway Queries

**Impact: HIGH** (Prevents single queries from consuming hours of warehouse credits)

A single poorly written query (accidental cross join, missing filter) can run for hours on a large warehouse, burning hundreds of credits. Statement timeouts are your safety net.

**Incorrect (no timeout):**

```sql
-- Bad: No timeout — this accidental cross join runs for 4 hours
SELECT * FROM table_a CROSS JOIN table_b;
-- Cost: ~48 credits on a LARGE warehouse
```

**Correct (set statement timeouts at multiple levels):**

```sql
-- Set timeout at warehouse level (affects all queries on this warehouse)
ALTER WAREHOUSE analytics_wh
  SET STATEMENT_TIMEOUT_IN_SECONDS = 3600;  -- 1 hour max

-- Set timeout at user level (for specific power users)
ALTER USER analyst_user
  SET STATEMENT_TIMEOUT_IN_SECONDS = 1800;  -- 30 minutes

-- Set timeout at session level (for a specific session)
ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 900;  -- 15 minutes
```

Reference: [https://docs.snowflake.com/en/sql-reference/parameters#statement-timeout-in-seconds](https://docs.snowflake.com/en/sql-reference/parameters#statement-timeout-in-seconds)

---
