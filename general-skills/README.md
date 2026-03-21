# General-Purpose Skills for AI Coding Agents

Skills that teach AI coding agents general development patterns — containerization, ORM scaffolding, auth, and more. These work with any stack, not just Snowflake.

## Installation

Run in your project root:

```bash
# Install all skills (Snowflake + general)
curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/snowflake-skills/install_skills.sh | bash

# Install a specific general skill
curl -sSL .../snowflake-skills/install_skills.sh | bash -s -- docker-dev-setup

# List available skills
curl -sSL .../snowflake-skills/install_skills.sh | bash -s -- --list
```

## Available Skills

<!-- BEGIN_SKILLS_TABLE -->
| Skill | What it does |
|-------|-------------|
| [docker-dev-setup](docker-dev-setup/) | Containerize an application with a production-grade Dockerfile, Docker Compose for local development, and optional Dev Container configuration |
| [drizzle-orm-setup](drizzle-orm-setup/) | Scaffold a Drizzle ORM project with TypeScript schema, relations, database client, and migrations |
| [supabase-auth-rls](supabase-auth-rls/) | Scaffold a Supabase project with database schema, Row Level Security policies, and auth integration |
<!-- END_SKILLS_TABLE -->

## Custom Skills

Create your own using the [TEMPLATE](TEMPLATE/):

```bash
cp -r TEMPLATE/ my-new-skill/
# Edit my-new-skill/SKILL.md with your patterns
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full guide.
