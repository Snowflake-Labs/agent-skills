---
title: Choose COPY INTO vs Snowpipe Based on Latency Needs
impact: CRITICAL
impactDescription: "Right loading method avoids wasted credits (batch) or missed SLAs (streaming)"
tags: [loading, snowpipe, copy-into, architecture]
---

## Choose COPY INTO vs Snowpipe Based on Latency Needs

**Impact: CRITICAL**

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

**Decision framework:**

```
Files arrive on a schedule (hourly, daily)?
  → COPY INTO with a Task or orchestrator

Files arrive continuously (event-driven)?
  → Snowpipe (AUTO_INGEST)

Need sub-second latency from source to table?
  → Snowpipe Streaming (SDK-based, no files)

Loading from another Snowflake table?
  → INSERT INTO ... SELECT (no staging needed)
```

**Anti-patterns:**
- Running COPY INTO every minute on a cron (use Snowpipe instead — it's cheaper)
- Using Snowpipe for once-daily bulk loads (use COPY INTO — more control, cheaper)
- Using a warehouse for Snowpipe loads (Snowpipe uses serverless compute automatically)

**COPY INTO idempotency:** COPY INTO tracks loaded files for 64 days. Re-running the same COPY INTO skips already-loaded files automatically. Use `FORCE = TRUE` only to intentionally reload.

Reference: [Data Loading Overview](https://docs.snowflake.com/en/user-guide/data-load-overview)
