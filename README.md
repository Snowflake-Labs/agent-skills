# Cortex Skills

A collection of [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) skills for Snowflake migrations, data engineering, and operations.

## Installation

### Option 1: Remote (auto-synced)

Add this repo to your Cortex Code skills config at `~/.snowflake/cortex/skills.json`:

```json
{
  "remote": [
    {
      "source": "https://github.com/iamontheinet/cortex-skills",
      "ref": "main",
      "skills": [{ "name": "ssis-to-dbt-replatform-migration" }]
    }
  ]
}
```

Skills are cached locally and updated on next Cortex Code session.

### Option 2: Manual (local copy)

```bash
git clone https://github.com/iamontheinet/cortex-skills.git /tmp/cortex-skills
cp -r /tmp/cortex-skills/ssis-to-dbt-replatform-migration \
  ~/.snowflake/cortex/skills/ssis-to-dbt-replatform-migration
```

### Verify

In a Cortex Code session, run `/skill` to open the skill manager — the skill should appear under **Global** or **Remote** skills. You can also invoke it directly:

```
$ssis-to-dbt-replatform-migration
```

## Skills

| Skill | Description |
|-------|-------------|
| [ssis-to-dbt-replatform-migration](ssis-to-dbt-replatform-migration/) | Validates, deploys, and operationalizes SnowConvert AI Replatform output — SSIS packages converted to dbt projects and Snowflake TASKs |