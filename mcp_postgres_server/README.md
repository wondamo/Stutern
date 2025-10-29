MCP Postgres Server (Python)

A Python MCP server that connects to PostgreSQL and exposes safe, read‑only tools over stdio. Great for enabling MCP‑compatible clients to query a Postgres database.

Project Structure

```
mcp_postgres_server/
  mcp_postgres_server/
    server.py                 # stdio MCP server (entrypoint: mcp-postgres)
    fastmcp_server.py         # stdio MCP server via FastMCP module
  sql/
    load_fx_flows.sql         # schema + COPY for sample data
  data/
    fx_flows.csv              # sample FX flows dataset
  pyproject.toml              # defines console script: mcp-postgres
  README.md
```

Setup

1) Install Docker
- Install Docker Desktop: https://docs.docker.com/get-started/get-docker/

2) Start Postgres and load sample data (from repo root)
```
# Start Postgres (exposes 5438 locally)
docker run -d --name postgres-fx \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=stutern \
  -p 5438:5432 -v pgdata_fx:/var/lib/postgresql/data postgres

# Copy data + SQL into the container
docker cp mcp_postgres_server/data/fx_flows.csv postgres-fx:/tmp/fx_flows.csv
docker cp mcp_postgres_server/sql/load_fx_flows.sql postgres-fx:/tmp/load_fx_flows.sql

# Create table and load the CSV
docker exec -it postgres-fx psql -U app -d stutern -f /tmp/load_fx_flows.sql
```

3) Install the package (so the console script is available)
```
cd mcp_postgres_server
pip install .
```

4) Configure your MCP client (Claude or ChatGPT)
- Use this server configuration and set `DATABASE_URL` to your instance:
```
{
  "postgres-fx": {
    "command": "mcp-postgres",
    "env": {
      "DATABASE_URL": "postgres://app:app@localhost:5438/stutern"
    }
  }
}
```
- Alternatively (without relying on the console script), you can target the module:
```
{
  "postgres-fx": {
    "command": "python",
    "args": ["-m", "mcp_postgres_server.fastmcp_server"],
    "env": { "DATABASE_URL": "postgres://app:app@localhost:5438/stutern" }
  }
}
```
- Claude Desktop: add the above under the `mcpServers` section of your `claude_desktop_config.json`.
- ChatGPT (MCP‑enabled builds): add an MCP server using the same JSON in your client’s MCP configuration UI or file.

Usage

- The MCP client launches the server via the config. If you want to run it manually:
  - Console script: `mcp-postgres`
  - Python module: `python -m mcp_postgres_server.server`

Environment

- `DATABASE_URL`: e.g. `postgres://user:pass@host:5432/dbname`
- Or use `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- `PGSSLMODE`: any value except `disable` enables SSL (verification off for convenience)

Provided Tools

- `pg_health` — server version, current db/schema, env summary
- `pg_list_tables(schema='public', include_views=False)` — list tables (and optionally views)
- `pg_describe_table(table, schema='public')` — describe table columns
- `pg_query(sql, params=None, row_limit=100)` — single read‑only query; appends LIMIT if missing

Safety Notes

- Enforces a single SELECT/WITH statement (after stripping SQL comments)
- Ensures a row limit if none is present

Troubleshooting

- If it won’t connect, call `pg_health` and verify credentials/host. For SSL hiccups, try `PGSSLMODE=disable`.
