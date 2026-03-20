# Snowflake Agent Skills

This repository contains skills for AI coding agents that work with Snowflake. Each skill is a self-contained directory with a `SKILL.md` file following the [agentskills.io](https://agentskills.io) open standard.

## Quick Install

```bash
npx skills add Snowflake-Labs/agent-skills
```

## Available Skills

### Snowflake Core

- **[snowflake-best-practices](snowflake-best-practices/)** — 25 production rules for warehouse sizing, clustering, query optimization, data loading, semi-structured data, and cost control
- **[dynamic-tables](dynamic-tables/)** — Declarative data pipelines with automatic incremental refresh, replacing Streams + Tasks
- **[cortex-ai-functions](cortex-ai-functions/)** — SQL-native AI/LLM functions: classify, extract, summarize, translate, embed, and process documents
- **[snowpark-python](snowpark-python/)** — DataFrame API, UDFs, UDTFs, stored procedures running inside Snowflake
- **[snowflake-postgres](snowflake-postgres/)** — Managed PostgreSQL with pg_lake (Iceberg), pg_incremental, and zero-ETL bridge to Snowflake

### Data Ingestion

- **[snowpipe-streaming-java](snowpipe-streaming-java/)** — Stream data into Snowflake using the Java Snowpipe Streaming SDK
- **[snowpipe-streaming-python](snowpipe-streaming-python/)** — Stream data into Snowflake using the Python Snowpipe Streaming SDK

### Migration & Setup

- **[ssis-to-dbt-replatform-migration](ssis-to-dbt-replatform-migration/)** — SSIS to dbt + Snowflake migration using SnowConvert AI
- **[docker-dev-setup](docker-dev-setup/)** — Production-grade Dockerfile and Docker Compose
- **[drizzle-orm-setup](drizzle-orm-setup/)** — Drizzle ORM with TypeScript schema and migrations
- **[supabase-auth-rls](supabase-auth-rls/)** — Supabase auth with Row Level Security
