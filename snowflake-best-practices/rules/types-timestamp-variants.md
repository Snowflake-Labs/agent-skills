---
title: Choose the Right TIMESTAMP Variant
impact: CRITICAL
impactDescription: "Prevents timezone bugs in analytics, ETL, and cross-region queries"
tags: [types, timestamp, timezone, schema]
---

## Choose the Right TIMESTAMP Variant

**Impact: CRITICAL**

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

**Default behavior:** `TIMESTAMP` without a suffix defaults to `TIMESTAMP_NTZ` in Snowflake. Always be explicit.

```sql
-- Bad: Which type is this? Depends on TIMESTAMP_TYPE_MAPPING parameter
CREATE TABLE t (ts TIMESTAMP);

-- Good: Always explicit
CREATE TABLE t (ts TIMESTAMP_LTZ);
```

Reference: [TIMESTAMP Data Types](https://docs.snowflake.com/en/sql-reference/data-types-datetime#timestamp)
