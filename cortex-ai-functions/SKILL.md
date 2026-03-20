---
name: cortex-ai-functions
description: "Guide to Snowflake Cortex AI functions — SQL-native LLM inference, text classification, extraction, sentiment analysis, embeddings, and document processing without infrastructure management"
---

# Snowflake Cortex AI Functions

SQL-native AI functions that bring LLM capabilities directly into your queries. No API keys, no infrastructure, no data movement — call AI on your data where it lives in Snowflake.

> **Official docs:** [Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)

---

## Quick Reference

| Function | Purpose | Returns |
|---|---|---|
| `AI_COMPLETE` | Text generation / prompting | Generated text (VARCHAR) |
| `AI_CLASSIFY` | Zero-shot text classification | Label + confidence (OBJECT) |
| `AI_EXTRACT` | Entity extraction from text | Structured JSON (OBJECT) |
| `AI_SENTIMENT` | Sentiment scoring | FLOAT from -1 to 1 |
| `AI_SUMMARIZE` | Text summarization | Summary text (VARCHAR) |
| `AI_TRANSLATE` | Language translation | Translated text (VARCHAR) |
| `AI_EMBED` | Vector embeddings | VECTOR(FLOAT, dim) |
| `AI_FILTER` | Boolean content filtering | TRUE / FALSE |
| `AI_REDACT` | PII redaction | Redacted text (VARCHAR) |
| `AI_AGG` | Aggregated AI analysis | Summary across rows (VARCHAR) |
| `AI_PARSE_DOCUMENT` | Document/PDF extraction | Structured content (OBJECT) |

All functions live in the `SNOWFLAKE.CORTEX` schema.

---

## Text Generation — AI_COMPLETE

Generate text using hosted LLMs. The most versatile function.

### Basic usage

```sql
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE('claude-3-5-sonnet', 'Explain micro-partitions in one sentence.');
```

### With system message and structured prompt

```sql
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    'claude-3-5-sonnet',
    [
        {'role': 'system', 'content': 'You are a concise SQL tutor. Reply in under 50 words.'},
        {'role': 'user', 'content': 'When should I use a clustering key?'}
    ]::ARRAY(OBJECT(role VARCHAR, content VARCHAR)),
    {'temperature': 0.3, 'max_tokens': 200}
);
```

### Batch processing — run AI on every row

```sql
SELECT
    ticket_id,
    subject,
    SNOWFLAKE.CORTEX.AI_COMPLETE(
        'mistral-large2',
        'Classify this support ticket as billing, technical, or account. Reply with one word only.\n\n' || body
    ) AS category
FROM support_tickets
WHERE created_at >= CURRENT_DATE - 7;
```

### Available models

| Model | Best for |
|---|---|
| `claude-3-5-sonnet` | Complex reasoning, analysis, code |
| `mistral-large2` | General tasks, good cost/quality balance |
| `llama3.1-70b` | Open-source, fast, cost-effective |
| `llama3.1-8b` | Lightweight tasks, lowest cost |

---

## Text Classification — AI_CLASSIFY

Zero-shot classification — no training data needed.

### Single row

```sql
SELECT SNOWFLAKE.CORTEX.AI_CLASSIFY(
    'My invoice is wrong and I was charged twice',
    ['billing', 'technical_issue', 'account_access', 'feature_request']
);
-- Returns: {"label": "billing", "score": 0.92}
```

### Batch — classify customer feedback

```sql
SELECT
    feedback_id,
    comment,
    SNOWFLAKE.CORTEX.AI_CLASSIFY(
        comment,
        ['positive', 'negative', 'neutral']
    ):label::VARCHAR AS sentiment_label,
    SNOWFLAKE.CORTEX.AI_CLASSIFY(
        comment,
        ['positive', 'negative', 'neutral']
    ):score::FLOAT AS confidence
FROM customer_feedback;
```

### Content moderation

```sql
SELECT
    post_id,
    content,
    SNOWFLAKE.CORTEX.AI_CLASSIFY(
        content,
        ['safe', 'spam', 'offensive', 'off_topic']
    ):label::VARCHAR AS moderation_result
FROM user_posts
WHERE moderation_result != 'safe';
```

---

## Entity Extraction — AI_EXTRACT

Pull structured data out of unstructured text.

### Basic extraction

```sql
SELECT SNOWFLAKE.CORTEX.AI_EXTRACT(
    'Please contact John Smith at john@example.com regarding order #12345 placed on March 15, 2025.',
    ['person_name', 'email', 'order_number', 'date']
);
-- Returns: {"person_name": "John Smith", "email": "john@example.com", "order_number": "12345", "date": "March 15, 2025"}
```

### Batch — extract from support tickets

```sql
SELECT
    ticket_id,
    body,
    SNOWFLAKE.CORTEX.AI_EXTRACT(body, ['product_name', 'error_code', 'urgency']):product_name::VARCHAR AS product,
    SNOWFLAKE.CORTEX.AI_EXTRACT(body, ['product_name', 'error_code', 'urgency']):error_code::VARCHAR AS error_code
FROM support_tickets;
```

---

## Sentiment Analysis — AI_SENTIMENT

Score text from -1 (negative) to 1 (positive).

### Single value

```sql
SELECT SNOWFLAKE.CORTEX.AI_SENTIMENT('The product works great, very happy with my purchase!');
-- Returns: 0.89
```

### Batch — analyze reviews with aggregation

```sql
SELECT
    product_id,
    COUNT(*) AS review_count,
    AVG(SNOWFLAKE.CORTEX.AI_SENTIMENT(review_text)) AS avg_sentiment,
    COUNT_IF(SNOWFLAKE.CORTEX.AI_SENTIMENT(review_text) < -0.3) AS negative_count
FROM product_reviews
GROUP BY product_id
ORDER BY avg_sentiment ASC;
```

---

## Summarization — AI_SUMMARIZE

Condense long text into concise summaries.

```sql
SELECT SNOWFLAKE.CORTEX.AI_SUMMARIZE(article_body) AS summary
FROM news_articles
WHERE published_date = CURRENT_DATE;
```

### Summarize support conversations

```sql
SELECT
    conversation_id,
    SNOWFLAKE.CORTEX.AI_SUMMARIZE(full_transcript) AS summary
FROM support_conversations
WHERE resolved_at >= CURRENT_DATE - 1;
```

---

## Translation — AI_TRANSLATE

Translate text between languages.

```sql
SELECT SNOWFLAKE.CORTEX.AI_TRANSLATE(
    'Snowflake es una plataforma de datos en la nube.',
    'es',   -- source language
    'en'    -- target language
);
-- Returns: "Snowflake is a cloud data platform."
```

### Batch — translate product descriptions

```sql
SELECT
    product_id,
    description_es,
    SNOWFLAKE.CORTEX.AI_TRANSLATE(description_es, 'es', 'en') AS description_en,
    SNOWFLAKE.CORTEX.AI_TRANSLATE(description_es, 'es', 'fr') AS description_fr
FROM product_catalog
WHERE market = 'LATAM';
```

Supported languages include: `en`, `es`, `fr`, `de`, `it`, `pt`, `ja`, `ko`, `zh`, `ru`, `pl`, `sv`, and others. Check docs for the full list.

---

## Embeddings — AI_EMBED

Generate vector embeddings for semantic search and RAG pipelines.

### Generate an embedding

```sql
SELECT SNOWFLAKE.CORTEX.AI_EMBED('e5-base-v2', 'Snowflake clustering keys improve query performance');
```

### Semantic similarity search

```sql
-- Find documents similar to a query
SET search_query = 'How do I optimize warehouse costs?';

SELECT
    doc_id,
    title,
    VECTOR_COSINE_SIMILARITY(
        embedding,
        SNOWFLAKE.CORTEX.AI_EMBED('e5-base-v2', $search_query)
    ) AS similarity
FROM knowledge_base
ORDER BY similarity DESC
LIMIT 10;
```

### Build an embedding column for RAG

```sql
ALTER TABLE knowledge_base ADD COLUMN embedding VECTOR(FLOAT, 768);

UPDATE knowledge_base
SET embedding = SNOWFLAKE.CORTEX.AI_EMBED('e5-base-v2', content);
```

### Available embedding models

| Model | Dimensions | Best for |
|---|---|---|
| `e5-base-v2` | 768 | General-purpose, English text |
| `snowflake-arctic-embed-m-v1.5` | 768 | Multilingual, retrieval-optimized |

---

## Content Filtering — AI_FILTER

Boolean filter — does the text match a condition?

```sql
SELECT
    review_id,
    review_text
FROM product_reviews
WHERE SNOWFLAKE.CORTEX.AI_FILTER(review_text, 'mentions a competitor product');
```

---

## PII Redaction — AI_REDACT

Remove personally identifiable information from text.

```sql
SELECT SNOWFLAKE.CORTEX.AI_REDACT(
    'Call me at 555-123-4567 or email jane.doe@company.com'
);
-- Returns: "Call me at [PHONE_NUMBER] or email [EMAIL_ADDRESS]"
```

---

## Aggregated Analysis — AI_AGG

Summarize or analyze data across multiple rows.

```sql
SELECT SNOWFLAKE.CORTEX.AI_AGG(
    review_text,
    'What are the top 3 recurring complaints?'
) AS complaint_summary
FROM product_reviews
WHERE product_id = 'SKU-100';
```

---

## Document Processing — AI_PARSE_DOCUMENT

Extract text and structure from PDFs and images stored in Snowflake stages.

### Parse a PDF

```sql
SELECT SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT(
    @my_stage,
    'invoices/invoice_2025_001.pdf',
    {'mode': 'LAYOUT'}
);
```

### Batch — process all PDFs in a stage

```sql
SELECT
    relative_path,
    SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT(
        @my_stage,
        relative_path,
        {'mode': 'LAYOUT'}
    ):content::VARCHAR AS extracted_text
FROM DIRECTORY(@my_stage)
WHERE relative_path LIKE '%.pdf';
```

### Modes

| Mode | Use case |
|---|---|
| `LAYOUT` | Preserves document structure (headers, tables, paragraphs) |
| `OCR` | Optical character recognition for scanned documents and images |

---

## Best Practices

### Use batch processing

Process entire tables, not row-by-row. Snowflake parallelizes across rows automatically.

```sql
-- Good: batch on a table
SELECT id, SNOWFLAKE.CORTEX.AI_SENTIMENT(text) FROM reviews;

-- Avoid: calling in a loop or procedurally
```

### Cache AI outputs — don't recompute

Store results in columns instead of recomputing on every query.

```sql
ALTER TABLE reviews ADD COLUMN sentiment FLOAT;

UPDATE reviews
SET sentiment = SNOWFLAKE.CORTEX.AI_SENTIMENT(review_text)
WHERE sentiment IS NULL;
```

### Choose the right model for the job

- **High quality needed** (analysis, code, reasoning): `claude-3-5-sonnet`
- **Balanced workloads** (classification, extraction): `mistral-large2`
- **High volume / cost-sensitive**: `llama3.1-70b` or `llama3.1-8b`
- Use the smallest model that produces acceptable results.

### Use specialized functions over AI_COMPLETE when available

```sql
-- Prefer this (optimized, cheaper):
SELECT SNOWFLAKE.CORTEX.AI_SENTIMENT(text) FROM reviews;

-- Over this (general-purpose, more expensive):
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE('claude-3-5-sonnet', 'Rate sentiment of: ' || text) FROM reviews;
```

### Cost awareness

- AI functions consume credits based on tokens processed.
- Longer inputs = more tokens = higher cost.
- Truncate or pre-filter text when full content is not needed.
- Use `WHERE` clauses to limit rows processed.
- Monitor usage via `SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY` with `SERVICE_TYPE = 'AI_SERVICES'`.

### Rate limits and concurrency

- Cortex functions have per-account rate limits.
- For large batch jobs, use a dedicated warehouse.
- Process in batches with `LIMIT`/`OFFSET` if hitting rate limits.
- Smaller models have higher throughput limits than larger models.
