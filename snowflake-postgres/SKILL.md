---
name: snowflake-postgres
description: "Guide to Snowflake Postgres — managed PostgreSQL with pg_lake (Iceberg tables on object storage), pg_incremental (automated archival), and zero-ETL bridge to Snowflake analytics"
---

# Snowflake Postgres

Snowflake Postgres is a fully managed PostgreSQL service that bridges OLTP and OLAP workloads. Run transactional queries on Postgres, analyze the same data in Snowflake — no ETL pipelines needed. Key extensions (`pg_lake`, `pg_incremental`) write PostgreSQL tables as Apache Iceberg tables to object storage, where Snowflake reads them directly.

## Getting Started

### Creating an Instance

```sql
-- From Snowflake (requires ACCOUNTADMIN or appropriate privileges)
CREATE POSTGRES INSTANCE my_postgres
  WAREHOUSE_SIZE = 'SMALL'
  DATABASE = 'my_pg_db';
```

Or via the Snowflake CLI:

```bash
snow postgres create-instance my_postgres --warehouse-size SMALL --database my_pg_db
```

### Connecting

Retrieve connection parameters after instance creation:

```sql
SHOW POSTGRES INSTANCES;
DESCRIBE POSTGRES INSTANCE my_postgres;
```

Connect with any standard PostgreSQL client:

```bash
psql "host=<instance-host> port=5432 dbname=my_pg_db user=admin sslmode=require"
```

### Instance Sizing

| Size    | vCPUs | Memory | Use Case                          |
|---------|-------|--------|-----------------------------------|
| XSMALL  | 2     | 8 GB   | Dev/test, light transactional     |
| SMALL   | 4     | 16 GB  | Small production workloads        |
| MEDIUM  | 8     | 32 GB  | Moderate OLTP                     |
| LARGE   | 16    | 64 GB  | High-throughput transactional     |

### Supported Extensions

Snowflake Postgres supports standard PostgreSQL extensions including `pg_lake`, `pg_incremental`, `pg_partman`, `PostGIS`, `pgcrypto`, `uuid-ossp`, `hstore`, and others. Run `SHOW AVAILABLE EXTENSIONS;` from psql to list all.

## pg_lake — Iceberg Tables on Object Storage

pg_lake writes PostgreSQL tables as Apache Iceberg tables to S3 or other object storage. Changes in Postgres are automatically synced to Iceberg format, making the data queryable from both Postgres (OLTP) and Snowflake (OLAP).

### Setup

```sql
-- In your Postgres instance
CREATE EXTENSION IF NOT EXISTS pg_lake;
```

### Converting Tables to Lake Tables

```sql
-- Create a regular Postgres table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    total NUMERIC(10,2),
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Convert it to a lake table (syncs to Iceberg on object storage)
SELECT pg_lake.create_lake_table('public', 'orders');
```

Once converted, all inserts, updates, and deletes to the `orders` table are automatically propagated to the Iceberg representation on object storage.

### Storage Integration

pg_lake uses the storage integration configured on your Snowflake Postgres instance. The instance provisions and manages the S3 path automatically. To check sync status:

```sql
SELECT * FROM pg_lake.lake_tables;
-- Shows table name, sync status, last sync time, Iceberg metadata location
```

### Controlling Sync Behavior

```sql
-- Set sync interval (default: 60 seconds)
SELECT pg_lake.set_sync_interval('public', 'orders', '30 seconds');

-- Force an immediate sync
SELECT pg_lake.sync_table('public', 'orders');

-- Check replication lag
SELECT table_name, last_synced_at, pending_changes
FROM pg_lake.sync_status;
```

## pg_incremental — Automated Data Archival

pg_incremental manages time-partitioned tables with automatic archival of old partitions. Combined with pg_lake, archived partitions remain queryable through Snowflake.

### Setup

```sql
CREATE EXTENSION IF NOT EXISTS pg_incremental;
```

### Creating Partitioned Tables with Retention

```sql
-- Create a time-partitioned table with 90-day retention
SELECT pg_incremental.create_partitioned_table(
    table_name   := 'events',
    partition_col := 'event_time',
    interval     := '1 day',
    retention    := '90 days'
);

-- The table is created with automatic partition management:
-- - New partitions are created ahead of time
-- - Partitions older than 90 days are detached and archived
```

### Integration with pg_lake

When both extensions are active, archived partitions are written to Iceberg before being dropped from Postgres. This means old data is still queryable via Snowflake:

```sql
-- Enable lake archival for a partitioned table
SELECT pg_lake.create_lake_table('public', 'events');

-- Now: recent data lives in Postgres, old data lives in Iceberg
-- Both are queryable from Snowflake
```

### Managing Retention

```sql
-- View current partition status
SELECT * FROM pg_incremental.partition_info('events');

-- Adjust retention
SELECT pg_incremental.set_retention('events', '60 days');

-- Manually archive a partition (sends to pg_lake if enabled)
SELECT pg_incremental.archive_partition('events', '2025-01-15');
```

## Zero-ETL Bridge to Snowflake

Snowflake reads the Iceberg tables created by pg_lake directly — no separate ETL pipeline, no data copying, no orchestration.

### How It Works

1. pg_lake writes Postgres data as Iceberg tables to object storage
2. Snowflake uses a catalog integration to discover and read those Iceberg tables
3. You query the data in Snowflake using standard SQL

### Setting Up the Snowflake Side

```sql
-- 1. Create a catalog integration pointing to the pg_lake Iceberg catalog
CREATE OR REPLACE CATALOG INTEGRATION pg_lake_catalog
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = 'public'
  REST_CONFIG = (
    CATALOG_URI = '<pg_lake_catalog_uri>'
    CATALOG_API_TYPE = 'AWS_GLUE'  -- or appropriate type
  )
  ENABLED = TRUE;

-- 2. Create an Iceberg table in Snowflake that references the pg_lake output
CREATE OR REPLACE ICEBERG TABLE analytics_db.public.orders
  EXTERNAL_VOLUME = 'pg_lake_volume'
  CATALOG = 'pg_lake_catalog'
  CATALOG_TABLE_NAME = 'public.orders';

-- 3. Query transactional data with Snowflake's full analytics engine
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS order_count,
    SUM(total) AS revenue
FROM analytics_db.public.orders
GROUP BY 1
ORDER BY 1;
```

### Catalog-Linked Database (Simplified)

For a simpler setup, use a catalog-linked database to auto-discover all pg_lake tables:

```sql
CREATE DATABASE pg_analytics
  LINKED_CATALOG = 'pg_lake_catalog';

-- All pg_lake tables appear automatically
SELECT * FROM pg_analytics.public.orders LIMIT 10;
```

## Common Patterns

### OLTP + OLAP Hybrid Architecture

Keep transactional workloads on Postgres, run analytics in Snowflake:

```sql
-- Postgres side: fast transactional inserts
INSERT INTO orders (customer_id, total, status)
VALUES (42, 99.99, 'confirmed');

-- Snowflake side: heavy aggregation across millions of rows
SELECT customer_id, SUM(total) AS lifetime_value
FROM pg_analytics.public.orders
GROUP BY customer_id
ORDER BY lifetime_value DESC
LIMIT 100;
```

### Event Sourcing with Lake Archival

Use pg_incremental to keep the event table lean in Postgres while preserving full history in Snowflake:

```sql
-- Postgres: recent events for real-time processing
SELECT * FROM events WHERE event_time > now() - INTERVAL '7 days';

-- Snowflake: full event history for trend analysis
SELECT event_type, COUNT(*), DATE_TRUNC('week', event_time) AS week
FROM pg_analytics.public.events
GROUP BY 1, 3;
```

### Microservice Database with Analytics Bridge

Each microservice owns its Postgres database. pg_lake bridges selected tables to a shared Snowflake analytics layer without coupling services:

```sql
-- Service A Postgres: only expose what analytics needs
SELECT pg_lake.create_lake_table('public', 'user_signups');

-- Service B Postgres: same pattern
SELECT pg_lake.create_lake_table('public', 'purchases');

-- Snowflake: join across microservice boundaries
SELECT u.signup_source, COUNT(p.id) AS purchases
FROM service_a.public.user_signups u
JOIN service_b.public.purchases p ON u.user_id = p.user_id
GROUP BY 1;
```

## Extensions and Compatibility

### Key Differences from Vanilla PostgreSQL

- **Managed infrastructure**: no OS-level access, automated backups and patching
- **pg_lake and pg_incremental**: exclusive to Snowflake Postgres
- **Storage**: uses Snowflake-managed storage with automatic Iceberg integration
- **Networking**: accessed through Snowflake's network layer with private connectivity options

### Supported Extensions

| Extension        | Purpose                                    |
|------------------|--------------------------------------------|
| pg_lake          | Iceberg table sync to object storage       |
| pg_incremental   | Time-partitioned tables with auto-archival |
| pg_partman       | Advanced partition management              |
| PostGIS          | Geospatial data types and functions        |
| pgcrypto         | Cryptographic functions                    |
| uuid-ossp        | UUID generation                            |
| pg_trgm          | Trigram-based text similarity              |
| btree_gin/gist   | Additional index types                     |

## Best Practices

1. **Right-size for OLTP**: choose an instance size based on your transactional workload, not your analytics needs. Snowflake handles the heavy analytical queries.

2. **Be selective with pg_lake**: convert tables that need analytics access, not every table. System tables, temporary tables, and small lookup tables usually don't need Iceberg sync.

3. **Set appropriate sync intervals**: default 60 seconds works for most cases. Reduce for near-real-time dashboards, increase for batch-oriented analytics to reduce I/O overhead.

4. **Monitor sync lag**: check `pg_lake.sync_status` regularly. If `pending_changes` grows consistently, consider increasing instance size or adjusting sync intervals.

5. **Use pg_incremental for large time-series tables**: keep Postgres fast by only holding recent data. Let pg_lake archive older partitions to Iceberg where Snowflake handles historical queries efficiently.

6. **Keep transactional queries on Postgres**: don't route analytical queries to Postgres. Use Snowflake for aggregations, joins across large datasets, and reporting.

7. **Use catalog-linked databases**: prefer `CREATE DATABASE ... LINKED_CATALOG` over manually creating individual Iceberg tables in Snowflake — it auto-discovers new pg_lake tables.

8. **Test with realistic data volumes**: pg_lake sync performance depends on change volume and row size. Test with production-like data before going live.
