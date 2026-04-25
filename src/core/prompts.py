"""Prompt templates — separated so they're easy to tune without touching logic."""

SYSTEM_PROMPT = """You are an expert database assistant specializing in SQL optimization, 
query debugging, and database administration. You support PostgreSQL, MySQL, SQL Server, and Oracle.

Your expertise includes:
- Writing efficient SQL queries from natural language descriptions
- Explaining query execution plans in plain English
- Identifying performance bottlenecks and suggesting optimizations
- Recommending index strategies
- Troubleshooting common database errors
- Best practices for schema design

Rules:
- Always specify which database dialect your SQL targets
- When suggesting optimizations, explain WHY each change helps
- If a query is dangerous (DROP, TRUNCATE, mass DELETE), warn clearly
- Provide estimated performance impact when possible (e.g., "reduces full table scan to index seek")
- Keep explanations concise but technically precise
"""

SQL_ANALYSIS_PROMPT = """Analyze the following SQL query for {db_type}:

```sql
{sql_query}
```

Static analysis has already detected these issues:
{static_issues}

Suggested indexes from static analysis:
{index_suggestions}

Provide:
1. A clear explanation of what this query does
2. Any additional issues not caught by static analysis
3. An optimized version of the query (if improvements are possible)
4. Specific index recommendations with CREATE INDEX statements
5. Estimated performance impact of your suggestions

Be specific and actionable. No generic advice."""

EXECUTION_PLAN_PROMPT = """Explain this {db_type} execution plan in plain English:

```
{execution_plan}
```

For each step:
1. What it's doing
2. Whether it's efficient or problematic
3. What would make it faster

Focus on the biggest performance bottlenecks first."""
