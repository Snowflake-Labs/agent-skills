---
name: snowpark-python
description: "Best practices for building Snowpark Python applications — DataFrame API, UDFs, UDTFs, stored procedures, and deployment patterns"
---

# Snowpark Python

Snowpark Python lets you build data pipelines, transformations, and analytics entirely in Python — executed inside Snowflake's compute engine. It provides a DataFrame API (lazy evaluation, server-side execution), plus the ability to deploy UDFs, UDTFs, and stored procedures that run natively in Snowflake without moving data to the client.

> **Official docs:** [Snowpark Python Developer Guide](https://docs.snowflake.com/en/developer-guide/snowpark/python/index)

---

## Session Management

The `Session` object is the entry point for all Snowpark operations.

### Creating a Session

```python
from snowflake.snowpark import Session

# From a dictionary (use env vars or secrets manager — never hardcode credentials)
import os
connection_params = {
    "account": os.environ["SNOWFLAKE_ACCOUNT"],
    "user": os.environ["SNOWFLAKE_USER"],
    "password": os.environ["SNOWFLAKE_PASSWORD"],
    "role": "DATA_ENGINEER",
    "warehouse": "TRANSFORM_WH",
    "database": "ANALYTICS",
    "schema": "PUBLIC",
}
session = Session.builder.configs(connection_params).create()
```

```python
# From a named connection in ~/.snowflake/connections.toml
session = Session.builder.configs({"connection_name": "my_conn"}).create()
```

### Best Practices

- **Never hardcode credentials.** Use environment variables, `~/.snowflake/connections.toml`, or a secrets manager.
- **Close sessions** when done: `session.close()`. Use `with` blocks or try/finally.
- **One session per script** is typical. Sessions are not thread-safe.
- Inside a stored procedure, the session is passed as the first argument — do not create a new one.

---

## DataFrame API Patterns

Snowpark DataFrames use **lazy evaluation**: operations build an execution plan, and nothing runs on Snowflake until an action (`collect()`, `show()`, `count()`, `save_as_table()`) triggers it.

### Reading Data

```python
# From a table
df = session.table("ANALYTICS.PUBLIC.ORDERS")

# From a SQL query
df = session.sql("SELECT * FROM ORDERS WHERE status = 'SHIPPED'")

# From a file on a stage
df = session.read.parquet("@my_stage/data/file.parquet")
df = session.read.csv("@my_stage/data/file.csv")
```

### Transformations

```python
from snowflake.snowpark.functions import col, sum as sum_, avg, lit, when
from snowflake.snowpark import Window

# Filter and select
active_orders = df.filter(col("STATUS") == "ACTIVE").select("ORDER_ID", "CUSTOMER_ID", "TOTAL")

# Join
customers = session.table("CUSTOMERS")
enriched = orders.join(customers, orders["CUSTOMER_ID"] == customers["ID"], "left")

# Aggregation
summary = df.group_by("REGION").agg(
    sum_("TOTAL").alias("TOTAL_REVENUE"),
    avg("TOTAL").alias("AVG_ORDER_VALUE"),
)

# Window functions
window_spec = Window.partition_by("CUSTOMER_ID").order_by(col("ORDER_DATE").desc())
df_ranked = df.with_column("RANK", row_number().over(window_spec))

# Conditional columns
df = df.with_column("TIER", when(col("TOTAL") > 1000, lit("HIGH")).otherwise(lit("STANDARD")))
```

### Actions (Trigger Execution)

```python
df.show()                          # Print to console (debugging)
df.show(50)                        # Show up to 50 rows
results = df.collect()             # Returns list of Row objects (pulls to client)
pandas_df = df.to_pandas()         # Convert to pandas DataFrame (pulls to client)
row_count = df.count()             # Returns integer count
df.write.save_as_table("OUTPUT")   # Write results to a Snowflake table
```

### Common Mistakes

```python
# WRONG: Pulling large datasets to client
all_rows = session.table("BILLION_ROW_TABLE").collect()  # OOM risk

# CORRECT: Process inside Snowflake, only pull summaries
summary = session.table("BILLION_ROW_TABLE").group_by("REGION").count()
summary.show()  # Small result set — safe to pull
```

```python
# WRONG: Python loop over rows
rows = df.collect()
for row in rows:
    # process each row in Python...

# CORRECT: Express logic as DataFrame operations
df_result = df.with_column("PROCESSED", upper(col("NAME")))
df_result.write.save_as_table("PROCESSED_TABLE")
```

---

## UDFs (User-Defined Functions)

UDFs extend SQL with Python logic. They map one input row to one output value.

### Decorator Pattern

```python
from snowflake.snowpark.functions import udf
from snowflake.snowpark.types import StringType, IntegerType

@udf(name="categorize_amount", return_type=StringType(), input_types=[IntegerType()],
     is_permanent=False, replace=True)
def categorize_amount(amount: int) -> str:
    if amount > 1000:
        return "HIGH"
    elif amount > 100:
        return "MEDIUM"
    return "LOW"

# Use in DataFrame
df.with_column("CATEGORY", categorize_amount(col("TOTAL")))
```

### Vectorized UDFs (Pandas)

Vectorized UDFs process batches of rows using pandas Series — significantly faster than scalar UDFs for large datasets.

```python
from snowflake.snowpark.types import PandasSeriesType, PandasDataFrameType, StringType, FloatType
import pandas as pd

@udf(name="normalize_name", is_permanent=False, replace=True)
def normalize_name(name: pd.Series) -> pd.Series:
    return name.str.strip().str.lower().str.title()
```

### With Package Dependencies

```python
@udf(name="extract_domain", return_type=StringType(), input_types=[StringType()],
     packages=["tldextract"], is_permanent=True, stage_location="@udf_stage", replace=True)
def extract_domain(url: str) -> str:
    import tldextract
    result = tldextract.extract(url)
    return f"{result.domain}.{result.suffix}"
```

### Programmatic Registration

```python
# Register from a lambda or existing function
add_one = session.udf.register(
    lambda x: x + 1,
    return_type=IntegerType(),
    input_types=[IntegerType()],
    name="add_one",
)
```

### Permanent vs Temporary

| Type | Lifetime | Use Case |
|------|----------|----------|
| Temporary (`is_permanent=False`) | Session only | Development, ad-hoc analysis |
| Permanent (`is_permanent=True`) | Persists across sessions | Production, shared across users |

Permanent UDFs require `stage_location` for uploading Python code to Snowflake.

---

## UDTFs (User-Defined Table Functions)

UDTFs produce **multiple output rows** per input row (one-to-many). Use when you need to explode, generate, or partition data.

### Class-Based Pattern

```python
from snowflake.snowpark.functions import udtf
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType

schema = StructType([
    StructField("WORD", StringType()),
    StructField("COUNT", IntegerType()),
])

@udtf(output_schema=schema, input_types=[StringType()], name="tokenize", replace=True)
class Tokenizer:
    def process(self, text: str):
        """Called once per input row. Yield tuples for each output row."""
        from collections import Counter
        words = text.lower().split()
        for word, count in Counter(words).items():
            yield (word, count)

    def end_partition(self):
        """Called after all rows in a partition. Optional — use for aggregation."""
        pass

# Usage
df.join_table_function("tokenize", col("DESCRIPTION"))
```

### When to Use UDTF vs UDF

| | UDF | UDTF |
|---|---|---|
| **Rows** | 1 input -> 1 output | 1 input -> N outputs |
| **Use case** | Transform a value | Explode, tokenize, generate rows |
| **Partitioning** | N/A | Supports `partition_by` for parallelism |

---

## Stored Procedures

Stored procedures run **inside Snowflake** (not on the client). Use them for ETL/ELT pipelines, data transformations, and administrative tasks.

### Decorator Pattern

```python
from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc
from snowflake.snowpark.types import StringType

@sproc(name="daily_transform", return_type=StringType(), is_permanent=True,
       stage_location="@sproc_stage", packages=["snowflake-snowpark-python"], replace=True)
def daily_transform(session: Session) -> str:
    source = session.table("RAW.EVENTS")
    transformed = source.filter(col("EVENT_DATE") == current_date()).select(
        col("USER_ID"), col("EVENT_TYPE"), col("PAYLOAD")
    )
    transformed.write.mode("append").save_as_table("ANALYTICS.DAILY_EVENTS")
    return f"Loaded {transformed.count()} rows"
```

### Key Rules

- The **first parameter** is always `session: Session` — Snowflake injects it at runtime.
- **Do not create a new Session** inside a stored procedure. Use the one provided.
- Stored procedures can call other Snowpark operations, run SQL, and use UDFs.
- Use `session.sql("CALL my_procedure()").collect()` to invoke from client code.

```python
# WRONG: Creating a session inside a stored procedure
@sproc(...)
def my_proc(session: Session) -> str:
    new_session = Session.builder.configs({...}).create()  # DO NOT DO THIS

# CORRECT: Use the provided session
@sproc(...)
def my_proc(session: Session) -> str:
    df = session.table("MY_TABLE")  # Use the injected session
```

---

## Performance Best Practices

### Push Computation to Snowflake

All DataFrame operations execute server-side. Avoid pulling data to the client for processing.

```python
# WRONG: Filter in Python after collecting
all_data = df.collect()
filtered = [r for r in all_data if r["STATUS"] == "ACTIVE"]

# CORRECT: Filter in Snowflake
filtered = df.filter(col("STATUS") == "ACTIVE")
```

### Use Vectorized UDFs

Pandas-based UDFs process data in batches, avoiding per-row overhead.

```python
# Scalar UDF — slow for large datasets (row-by-row)
@udf(return_type=FloatType(), input_types=[FloatType()])
def slow_normalize(val: float) -> float:
    return (val - 50.0) / 10.0

# Vectorized UDF — fast (batch processing via pandas)
@udf()
def fast_normalize(val: pd.Series) -> pd.Series:
    return (val - 50.0) / 10.0
```

### Cache Reused DataFrames

If a DataFrame is referenced multiple times, cache it to avoid re-execution.

```python
base_df = session.table("LARGE_TABLE").filter(col("YEAR") == 2025)
cached = base_df.cache_result()  # Materializes into a temp table

summary_a = cached.group_by("REGION").count()
summary_b = cached.group_by("CATEGORY").agg(sum_("REVENUE"))
```

### Write Results Back to Snowflake

```python
# Prefer save_as_table over collect() for large outputs
result.write.mode("overwrite").save_as_table("ANALYTICS.RESULTS")

# Append mode for incremental loads
result.write.mode("append").save_as_table("ANALYTICS.RESULTS")
```

---

## Deployment Patterns

### Using Snowflake CLI (`snow`)

```bash
# Initialize a Snowpark project
snow init my_project --template snowpark_python

# Deploy functions and procedures
snow snowpark deploy --replace

# Execute a stored procedure
snow snowpark execute function "my_func(1, 'hello')"
snow snowpark execute procedure "daily_transform()"
```

### Staging Dependencies

For permanent UDFs/procedures with third-party packages, upload code to a stage:

```python
session.sql("CREATE STAGE IF NOT EXISTS @my_stage").collect()

@udf(name="my_udf", is_permanent=True, stage_location="@my_stage",
     packages=["requests", "beautifulsoup4"], replace=True)
def my_udf(url: str) -> str:
    ...
```

### Task Scheduling

Schedule stored procedures to run on a cadence:

```sql
CREATE OR REPLACE TASK daily_transform_task
    WAREHOUSE = 'TRANSFORM_WH'
    SCHEDULE = 'USING CRON 0 6 * * * America/Los_Angeles'
AS
    CALL daily_transform();

ALTER TASK daily_transform_task RESUME;
```

---

## Quick Reference

| Operation | Method |
|---|---|
| Read table | `session.table("DB.SCHEMA.TABLE")` |
| Run SQL | `session.sql("SELECT ...")` |
| Filter | `df.filter(col("X") == value)` |
| Select columns | `df.select("A", "B", "C")` |
| Add column | `df.with_column("NEW", expr)` |
| Join | `df1.join(df2, df1["ID"] == df2["ID"])` |
| Aggregate | `df.group_by("X").agg(sum_("Y"))` |
| Write table | `df.write.save_as_table("OUTPUT")` |
| Debug | `df.show()` or `df.explain()` |
| Row count | `df.count()` |
| To pandas | `df.to_pandas()` |
| Cache | `df.cache_result()` |
