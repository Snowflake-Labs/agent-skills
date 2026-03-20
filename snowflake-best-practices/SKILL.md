---
name: snowflake-best-practices
description: "MUST USE when reviewing Snowflake schemas, queries, warehouses, or data pipelines. Contains 25 rules that MUST be checked before providing recommendations. Always read relevant rule files and cite specific rules in responses. Triggers: snowflake, create table, warehouse, clustering key, query optimization, data loading, copy into, variant, semi-structured, cost optimization, snowflake security."
---

# Snowflake Best Practices

Comprehensive guidance for Snowflake covering warehouse management, schema design, query optimization, data loading, semi-structured data, cost control, and security. Contains 25 rules across 8 categories, prioritized by impact.

> **Official docs:** [Snowflake Documentation](https://docs.snowflake.com)

## IMPORTANT: How to Apply This Skill

**Before answering Snowflake questions, follow this priority order:**

1. **Check for applicable rules** in the `rules/` directory
2. **If rules exist:** Apply them and cite them in your response using "Per `rule-name`..."
3. **If no rule exists:** Use general Snowflake knowledge or search documentation
4. **If uncertain:** Use web search for current best practices
5. **Always cite your source:** rule name, "general Snowflake guidance", or URL

**Why rules take priority:** Snowflake has specific behaviors (micro-partitions, columnar storage, compute/storage separation, credit-based billing) where general database intuition can be misleading. The rules encode validated, Snowflake-specific guidance.

---

## Review Procedures

### For Schema Reviews (CREATE TABLE, ALTER TABLE)

**Read these rule files in order:**

1. `rules/cluster-key-filter-alignment.md` — Align clustering with query filters
2. `rules/cluster-key-cardinality.md` — Column cardinality in cluster keys
3. `rules/cluster-key-when-to-cluster.md` — When clustering is worth it
4. `rules/types-use-appropriate-types.md` — Proper type selection
5. `rules/types-timestamp-variants.md` — TIMESTAMP_LTZ vs NTZ vs TZ
6. `rules/types-varchar-sizing.md` — VARCHAR sizing behavior
7. `rules/semi-variant-vs-flatten.md` — VARIANT vs flattened columns

**Check for:**
- [ ] Clustering key matches most common WHERE/JOIN predicates
- [ ] Data types match actual data (NUMBER not VARCHAR for IDs)
- [ ] TIMESTAMP variant appropriate for use case (LTZ for events, NTZ for business dates)
- [ ] VARIANT used only for truly dynamic schemas
- [ ] No unnecessary clustering on small tables

### For Query Reviews (SELECT, JOIN, aggregations)

**Read these rule files:**

1. `rules/query-avoid-select-star.md` — Column pruning benefits
2. `rules/query-filter-on-cluster-keys.md` — Partition pruning
3. `rules/query-use-qualify.md` — QUALIFY vs subquery
4. `rules/query-result-cache.md` — Result cache behavior
5. `rules/query-pruning-aware-joins.md` — JOIN optimization

**Check for:**
- [ ] SELECT lists only needed columns (no SELECT *)
- [ ] WHERE clauses use clustering key columns
- [ ] QUALIFY used instead of ROW_NUMBER subqueries
- [ ] JOINs filter early, not after joining
- [ ] Result cache not defeated by non-deterministic functions

### For Warehouse Reviews (sizing, configuration)

**Read these rule files:**

1. `rules/warehouse-right-sizing.md` — Choose the right size
2. `rules/warehouse-auto-suspend.md` — Auto-suspend configuration
3. `rules/warehouse-scale-up-vs-out.md` — Scaling strategy
4. `rules/warehouse-query-acceleration.md` — Query acceleration service

**Check for:**
- [ ] Warehouse size matches workload (not oversized)
- [ ] Auto-suspend set appropriately (60s for interactive, 300s for ETL)
- [ ] Multi-cluster for concurrency, larger size for complex queries
- [ ] Separate warehouses for different workload types

### For Data Loading Reviews (COPY INTO, Snowpipe)

**Read these rule files:**

1. `rules/load-file-sizing.md` — Optimal file sizes
2. `rules/load-copy-vs-snowpipe.md` — Batch vs streaming
3. `rules/load-staging-patterns.md` — Stage organization
4. `rules/load-format-options.md` — File format best practices

**Check for:**
- [ ] Files are 100-250 MB compressed
- [ ] COPY INTO for batch, Snowpipe for continuous
- [ ] Stage paths organized by date/source
- [ ] File format options set correctly (SKIP_HEADER, NULL_IF, etc.)

### For Cost Reviews

**Read these rule files:**

1. `rules/cost-resource-monitors.md` — Credit monitoring
2. `rules/cost-warehouse-timeouts.md` — Prevent runaway queries
3. `rules/cost-credit-aware-design.md` — Architecture for cost efficiency

**Check for:**
- [ ] Resource monitors set on all warehouses
- [ ] Statement timeout configured
- [ ] Workloads separated by warehouse (don't mix ETL and ad-hoc)
- [ ] Transient tables used for staging/temp data

---

## Output Format

Structure your response as follows:

```
## Rules Checked
- `rule-name-1` — Compliant / Violation found
- `rule-name-2` — Compliant / Violation found
...

## Findings

### Violations
- **`rule-name`**: Description of the issue
  - Current: [what the code does]
  - Required: [what it should do]
  - Fix: [specific correction]

### Compliant
- `rule-name`: Brief note on why it's correct

## Recommendations
[Prioritized list of changes, citing rules]
```

---

## Rule Categories by Priority

| Priority | Category | Impact | Prefix | Rule Count |
|----------|----------|--------|--------|------------|
| 1 | Warehouse Management | CRITICAL | `warehouse-` | 4 |
| 2 | Clustering Keys | CRITICAL | `cluster-key-` | 3 |
| 3 | Data Types | CRITICAL | `types-` | 3 |
| 4 | Query Optimization | CRITICAL | `query-` | 5 |
| 5 | Data Loading | HIGH | `load-` | 4 |
| 6 | Semi-Structured Data | HIGH | `semi-` | 3 |
| 7 | Cost Control | HIGH | `cost-` | 3 |

---

## Quick Reference

### Warehouse Management (CRITICAL)

- `warehouse-right-sizing` — Start small (XS/S), scale up based on query profile
- `warehouse-auto-suspend` — 60s for interactive, 300s for ETL, 0 for batch pipelines
- `warehouse-scale-up-vs-out` — Scale UP for complex queries, scale OUT (multi-cluster) for concurrency
- `warehouse-query-acceleration` — Enable QAS for ad-hoc workloads with outlier queries

### Clustering Keys (CRITICAL)

- `cluster-key-filter-alignment` — Cluster on columns used in WHERE and JOIN predicates
- `cluster-key-cardinality` — Use medium-cardinality columns (dates, categories) not high (UUIDs)
- `cluster-key-when-to-cluster` — Only cluster tables > 1 TB or with poor pruning ratios

### Data Types (CRITICAL)

- `types-use-appropriate-types` — Use NUMBER for numeric data, not VARCHAR; use DATE not TIMESTAMP for dates
- `types-timestamp-variants` — TIMESTAMP_LTZ for events, TIMESTAMP_NTZ for business dates, TIMESTAMP_TZ for multi-timezone
- `types-varchar-sizing` — VARCHAR(16777216) is the default and costs nothing extra; don't micro-optimize

### Query Optimization (CRITICAL)

- `query-avoid-select-star` — List specific columns; Snowflake is columnar, fewer columns = less I/O
- `query-filter-on-cluster-keys` — WHERE on clustering key columns enables micro-partition pruning
- `query-use-qualify` — Use QUALIFY instead of subquery with ROW_NUMBER
- `query-result-cache` — Identical queries return cached results for 24h if data hasn't changed
- `query-pruning-aware-joins` — Filter tables before joining, put smaller table on right side

### Data Loading (HIGH)

- `load-file-sizing` — 100-250 MB compressed per file for optimal parallel loading
- `load-copy-vs-snowpipe` — COPY INTO for batch/scheduled, Snowpipe for continuous/event-driven
- `load-staging-patterns` — Organize stages by source/date, use PURGE for cleanup
- `load-format-options` — Set ERROR_ON_COLUMN_COUNT_MISMATCH, NULL_IF, DATE_FORMAT explicitly

### Semi-Structured Data (HIGH)

- `semi-variant-vs-flatten` — Use VARIANT for truly dynamic schemas; flatten to columns for known structures
- `semi-lateral-flatten` — Use LATERAL FLATTEN for arrays/nested objects
- `semi-dot-notation` — Use dot notation (col:field) for simple access, FLATTEN for arrays

### Cost Control (HIGH)

- `cost-resource-monitors` — Set resource monitors on every warehouse with notify + suspend thresholds
- `cost-warehouse-timeouts` — Set STATEMENT_TIMEOUT_IN_SECONDS to prevent runaway queries
- `cost-credit-aware-design` — Use transient tables for staging, separate warehouses by workload, auto-suspend aggressively

---

## When to Apply

This skill activates when you encounter:

- `CREATE TABLE` or `ALTER TABLE` statements
- Warehouse sizing or configuration questions
- `CREATE WAREHOUSE` or `ALTER WAREHOUSE`
- Clustering key selection or `CLUSTER BY`
- Data type selection questions
- Slow query troubleshooting
- `COPY INTO` or data loading pipeline design
- VARIANT / semi-structured data handling
- Cost optimization or credit usage questions
- Query performance tuning
- Security configuration (RBAC, masking, network policies)

---

## Rule File Structure

Each rule file in `rules/` contains:

- **YAML frontmatter**: title, impact level, tags
- **Brief explanation**: Why this rule matters in Snowflake specifically
- **Incorrect example**: Anti-pattern with explanation
- **Correct example**: Best practice with explanation
- **Additional context**: Trade-offs, when to apply, references
