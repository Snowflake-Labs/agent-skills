---
title: Size Files for Optimal Parallel Loading
impact: CRITICAL
impactDescription: "10-50x faster loads; Snowflake parallelizes by file, not within files"
tags: [loading, file-size, parallelism, performance]
---

## Size Files for Optimal Parallel Loading

**Impact: CRITICAL**

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

**Optimal file sizes:**
| Format | Compressed Size | Why |
|--------|----------------|-----|
| CSV/TSV | 100-250 MB | Balances parallelism vs overhead |
| Parquet | 100-250 MB | Row groups add internal parallelism |
| JSON | 100-250 MB | Larger files = fewer overhead ops |

**Pre-splitting files (before upload):**

```bash
# Split a large CSV into 250MB chunks
split -b 250m large_file.csv chunk_
gzip chunk_*

# For Parquet, use your ETL tool's partition settings
# e.g., Spark: df.repartition(40).write.parquet("s3://bucket/path/")
```

**Anti-patterns:**
- One giant file (no parallelism)
- Millions of tiny files <1MB (too much overhead per file)
- Uncompressed files (wastes network and storage)

**Always compress:** GZIP for CSV/JSON, Snappy for Parquet (default). Compression reduces transfer time and storage costs.

Reference: [Data Loading Best Practices](https://docs.snowflake.com/en/user-guide/data-load-considerations-prepare)
