from __future__ import annotations

import os
import re
import ssl as ssl_module
import asyncio
from typing import Any, Optional, List

from dotenv import load_dotenv
import asyncpg

from mcp.server.fastmcp import FastMCP

load_dotenv()

# Specify transport protocol: stdio for local, streamable-http for hosted
transport = os.getenv("TRANSPORT_PROTOCOL", "stdio")

if transport == "stdio":
    # For local deployment
    app = FastMCP("mcp-postgres")
elif transport == "streamable-http":
    # For hosted deployment on render
    app = FastMCP("mcp-postgres", port=8000, host="0.0.0.0")
else:
    raise Exception("Only stdio and streamable-http transport is supported")


_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments from a string.

    Strips block comments (/* ... */) and single-line comments (--) from the
    provided SQL text, returning the cleaned SQL string.
    """
    sql = re.sub(r"/\*[\s\S]*?\*/", " ", sql)
    sql = re.sub(r"--.*$", " ", sql, flags=re.MULTILINE)
    return sql


def _is_read_only_sql(sql: str) -> bool:
    """Return True if the SQL is a single read-only statement.

    After stripping comments and trailing semicolons, the statement must start
    with SELECT or WITH and contain no additional statements.
    """
    cleaned = _strip_sql_comments(sql).strip()
    cleaned = re.sub(r";+\s*$", "", cleaned)
    if ";" in cleaned:
        return False
    first = (cleaned.split() or [""])[0].upper()
    return first in {"SELECT", "WITH"}


def _has_limit(sql: str) -> bool:
    """Return True if the SQL already contains a LIMIT clause."""
    cleaned = _strip_sql_comments(sql).lower()
    return bool(re.search(r"\blimit\b", cleaned))


def _ensure_limit(sql: str, limit: Optional[int]) -> str:
    """Ensure a LIMIT is present when a positive limit is provided.

    If `limit` is truthy and the SQL has no LIMIT clause, append
    `limit {limit}` to the end of the (semicolon-stripped) statement.
    """
    if not limit:
        return sql
    if _has_limit(sql):
        return sql
    sql_stripped = re.sub(r";+\s*$", "", sql.strip())
    return f"{sql_stripped} limit {int(limit)}"


async def _create_pool() -> asyncpg.Pool:
    """Create an asyncpg connection pool from environment configuration.

    Honors `DATABASE_URL` if set; otherwise uses `PGHOST`, `PGPORT`, `PGUSER`,
    `PGPASSWORD`, and `PGDATABASE`. If `PGSSLMODE` is set and not "disable",
    a permissive SSL context is used. Returns the created pool.
    """
    db_url = os.getenv("DATABASE_URL")
    ssl_mode = (os.getenv("PGSSLMODE") or "").lower()

    ssl_ctx: Optional[ssl_module.SSLContext]
    if ssl_mode and ssl_mode != "disable":
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
    else:
        ssl_ctx = None

    if db_url:
        return await asyncpg.create_pool(dsn=db_url, ssl=ssl_ctx)

    host = os.getenv("PGHOST", "localhost")
    port = int(os.getenv("PGPORT", "5432"))
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    database = os.getenv("PGDATABASE")

    return await asyncpg.create_pool(
        host=host, port=port, user=user, password=password, database=database, ssl=ssl_ctx
    )


async def _get_pool() -> asyncpg.Pool:
    """Get or lazily initialize the global asyncpg pool (async-safe)."""
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await _create_pool()
    return _pool


def _rows_to_dicts(records: List[asyncpg.Record]) -> List[dict]:
    """Convert a list of asyncpg.Record into plain dicts."""
    return [dict(r) for r in records]


def _env_summary() -> dict:
    """Return a sanitized snapshot of relevant PG env vars for diagnostics."""
    keys = [
        "DATABASE_URL",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGDATABASE",
        "PGSSLMODE",
    ]
    out = {}
    for k in keys:
        v = os.getenv(k)
        if not v:
            continue
        if k in {"DATABASE_URL", "PGUSER"}:
            out[k] = "(set)"
        else:
            out[k] = v
    return out


@app.tool(name="pg_health", description="Check PostgreSQL connectivity and return server/database info.")
async def pg_health() -> dict:
    """Check connectivity and return basic server and session metadata.

    Returns a dict with: `version`, `database`, `schema`, and sanitized `env`.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        ver = await conn.fetchrow("select version() as version")
        db = await conn.fetchrow(
            "select current_database() as db, current_schema() as schema"
        )
    return {
        "version": ver["version"] if ver else None,
        "database": db["db"] if db else None,
        "schema": db["schema"] if db else None,
        "env": _env_summary(),
    }


@app.tool(
    name="pg_list_tables",
    description="List tables and views in a schema (default: public)",
)
async def pg_list_tables(schema: str = "public", include_views: bool = False) -> list[dict]:
    """List tables (and optionally views) in a schema.

    Parameters:
      - schema: Schema name to inspect (default: "public").
      - include_views: When True, include views and foreign/temp tables.

    Returns a list of dicts with `table_schema`, `table_name`, and `table_type`.
    """
    types_to_include = ["BASE TABLE"]
    if include_views:
        types_to_include += ["VIEW", "FOREIGN TABLE", "LOCAL TEMPORARY"]
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select table_schema, table_name, table_type
              from information_schema.tables
             where table_schema = $1
               and table_type = any($2)
             order by table_name asc
            """,
            schema,
            types_to_include,
        )
    return _rows_to_dicts(rows)


@app.tool(
    name="pg_describe_table",
    description="Describe columns for a given table (schema + table)",
)
async def pg_describe_table(table: str, schema: str = "public") -> list[dict]:
    """Describe columns for a table within a schema.

    Parameters:
      - table: Table name (without schema prefix).
      - schema: Schema name (default: "public").

    Returns column metadata (name, type, nullability, defaults, lengths,
    precision/scale) as a list of dicts.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select column_name,
                   data_type,
                   is_nullable,
                   column_default,
                   udt_name,
                   character_maximum_length as char_max_len,
                   numeric_precision,
                   numeric_scale
              from information_schema.columns
             where table_schema = $1 and table_name = $2
             order by ordinal_position asc
            """,
            schema,
            table,
        )
    return _rows_to_dicts(rows)


@app.tool(
    name="pg_query",
    description=(
        "Execute a read-only SQL query (SELECT/WITH). Use $1, $2, ... placeholders "
        "and pass values in params (e.g., sql='select * from users where id=$1', params=[123])."
    ),
)
async def pg_query(
    sql: str, params: Optional[list[Any]] = None, row_limit: int = 100
) -> list[dict]:
    """Run a parameterized, read-only SQL query and return rows.

    Enforces a single SELECT/WITH statement and ensures a LIMIT clause using
    `row_limit` if absent. Uses PostgreSQL-style positional parameters ($1, $2,
    ...) supplied via `params`.

    Parameters:
      - sql: The SQL string (must start with SELECT or WITH).
      - params: Optional list of positional parameter values.
      - row_limit: Max rows to return if no LIMIT present (default 100).

    Returns a list of dicts representing result rows.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql must be a non-empty string")
    if not _is_read_only_sql(sql):
        raise ValueError(
            "Only read-only queries are allowed (single statement starting with SELECT or WITH)."
        )
    final_sql = _ensure_limit(sql, row_limit)
    values = params if isinstance(params, list) else []
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(final_sql, *values)
    return _rows_to_dicts(rows)


def main():
    app.run(transport=transport)


if __name__ == "__main__":
    main()
