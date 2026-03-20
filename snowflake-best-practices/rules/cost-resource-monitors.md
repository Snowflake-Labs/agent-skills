---
title: Set Resource Monitors to Prevent Runaway Costs
impact: CRITICAL
impactDescription: "Prevents surprise bills from runaway queries or misconfigured warehouses"
tags: [cost, resource-monitor, governance, budget]
---

## Set Resource Monitors to Prevent Runaway Costs

**Impact: CRITICAL**

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

**Monitor tiers for different environments:**

```sql
-- Development: Low quota, hard suspend
CREATE RESOURCE MONITOR dev_monitor
  WITH CREDIT_QUOTA = 100
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 80 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND_IMMEDIATE;

-- Production: Higher quota, notify early, suspend as last resort
CREATE RESOURCE MONITOR prod_monitor
  WITH CREDIT_QUOTA = 5000
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 50 PERCENT DO NOTIFY
    ON 75 PERCENT DO NOTIFY
    ON 90 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND;
```

**Trigger actions explained:**
| Action | Behavior |
|--------|----------|
| `NOTIFY` | Sends email alert; warehouse keeps running |
| `SUSPEND` | Lets running queries finish, then suspends warehouse |
| `SUSPEND_IMMEDIATE` | Kills running queries and suspends warehouse |

**Check current monitors:**

```sql
SHOW RESOURCE MONITORS;
```

**Modern alternative: Snowflake Budgets.** Budgets are a newer, more flexible cost management feature that monitors spending across warehouses, pipes, materialized views, tasks, and more. Budgets support tag-based resource grouping, forecasting, and custom actions (e.g., calling stored procedures at thresholds). Use resource monitors for simple per-warehouse guardrails; use Budgets for organization-wide cost governance:

```sql
-- Create a custom budget with a spending limit
CREATE BUDGET my_budget IN budgets_db.budgets_schema;
CALL my_budget!SET_SPENDING_LIMIT(500);  -- 500 credits/month

-- Add resources by tag for flexible grouping
CALL my_budget!ADD_RESOURCE_TAG(
  SELECT SYSTEM$REFERENCE('TAG', 'cost_center', 'SESSION', 'applybudget'),
  'analytics');
```

Reference: [Resource Monitors](https://docs.snowflake.com/en/user-guide/resource-monitors) | [Budgets](https://docs.snowflake.com/en/user-guide/budgets)
