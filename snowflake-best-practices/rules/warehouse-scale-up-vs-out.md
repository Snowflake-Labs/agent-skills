---
title: Scale Up for Complexity, Scale Out for Concurrency
impact: CRITICAL
impactDescription: "Correct scaling strategy prevents both poor performance and wasted spend"
tags: [warehouse, scaling, multi-cluster, concurrency]
---

## Scale Up for Complexity, Scale Out for Concurrency

**Impact: CRITICAL**

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

**Decision Guide:**

| Symptom | Solution | Action |
|---------|----------|--------|
| Single query is slow | Scale UP | Increase WAREHOUSE_SIZE |
| Queries are queueing | Scale OUT | Increase MAX_CLUSTER_COUNT |
| Spilling to remote storage | Scale UP | Increase WAREHOUSE_SIZE |
| High QUEUED_PROVISIONING time | Scale OUT | Increase MAX_CLUSTER_COUNT |

**Multi-cluster scaling policies:**
- `STANDARD`: Adds clusters as queries queue. Best for variable concurrency.
- `ECONOMY`: Only adds clusters when the full queue would fill 6 minutes. Saves credits but slower response.

Reference: [Multi-Cluster Warehouses](https://docs.snowflake.com/en/user-guide/warehouses-multicluster)
