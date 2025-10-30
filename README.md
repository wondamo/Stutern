# MCP Postgres Server (Python)

A minimal MCP server that connects to PostgreSQL and exposes safe, read‑only tools over stdio or HTTP. Use it from MCP‑compatible clients (e.g., Claude Desktop for stdio, or any client that supports HTTP MCP) to query Postgres.

## Quick Start

Choose one path.

### Option A — Hosted (HTTP)
- Server URL: https://stutern.onrender.com/mcp
- In your MCP client, add an HTTP server and use the URL above.
  - ChatGPT: Settings → Connectors → Add MCP server → HTTP
  - Claude Desktop: Settings → Tools → Add MCP server → HTTP

### Option B — Local (stdio via Claude Desktop)
Only Claude Desktop launches local stdio MCP servers.

1) Start Postgres and load sample data (from repo root)
```
# Start Postgres (exposes 5438 locally)
docker run -d --name postgres-fx \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=stutern \
  -p 5438:5432 -v pgdata_fx:/var/lib/postgresql/data postgres

# Copy data + SQL into the container
docker cp data/fx_flows.csv postgres-fx:/tmp/fx_flows.csv
docker cp sql/load_fx_flows.sql postgres-fx:/tmp/load_fx_flows.sql

# Create table and load the CSV
docker exec -it postgres-fx psql -U app -d stutern -f /tmp/load_fx_flows.sql
```

2) Install the package
```
# Windows
python -m pip install .

# macOS/Linux
python3 -m pip install .
```

3) Point Claude Desktop to the server (stdio)
- Open Claude Desktop settings and add a local MCP server.
- Use the contents of `mcp_settings.json` as a template. It runs: `python -m mcp_postgres_server.server`.
- Ensure `DATABASE_URL` matches your local DB, e.g. `postgres://app:app@localhost:5438/stutern`.

Optional: run by hand (stdio)
```
# Windows (PowerShell)
$env:TRANSPORT_PROTOCOL = "stdio"
$env:DATABASE_URL = "postgres://app:app@localhost:5438/stutern"
py -m mcp_postgres_server.server

# macOS/Linux
export TRANSPORT_PROTOCOL=stdio
export DATABASE_URL=postgres://app:app@localhost:5438/stutern
python3 -m mcp_postgres_server.server
```

## HTTP Self‑Hosting (optional)
Run an HTTP endpoint your client can call.

```
# Windows (PowerShell)
$env:TRANSPORT_PROTOCOL = "streamable-http"
$env:DATABASE_URL = "postgres://app:app@localhost:5438/stutern"
py -m mcp_postgres_server.server   # serves on 0.0.0.0:8000

# macOS/Linux
export TRANSPORT_PROTOCOL=streamable-http
export DATABASE_URL=postgres://app:app@localhost:5438/stutern
python3 -m mcp_postgres_server.server   # serves on 0.0.0.0:8000
```

Point your client to `http://<host>:8000/mcp`.

## Usage — Tools

- `pg_health()`
  - Connectivity check. Returns server version, current db/schema, and sanitized env summary.
- `pg_list_tables(schema='public', include_views=False)`
  - Lists tables (and optionally views) in a schema.
- `pg_describe_table(table, schema='public')`
  - Describes columns for a table.
- `pg_query(sql, params=None, row_limit=100)`
  - Executes a single read‑only query (SELECT/WITH). Uses $1, $2… positional params; ensures a LIMIT if missing.

## Configuration

- `DATABASE_URL` — Postgres DSN, e.g. `postgres://user:pass@host:port/db`
- `PGSSLMODE` — set to `disable` to turn off SSL verification if needed
- `TRANSPORT_PROTOCOL` — `stdio` (local) or `streamable-http` (HTTP server)

`mcp_settings.json` contains a ready‑to‑use Claude Desktop stdio config. Example entry id is `postgres-fx`.

## Use Your Own Postgres (no Docker)

- Load `data/fx_flows.csv` with the provided SQL script.
- macOS/Linux:
  ```
  cp data/fx_flows.csv /tmp/fx_flows.csv
  psql "postgres://USER:PASS@localhost:5432/stutern" -f sql/load_fx_flows.sql
  ```
- Windows:
  - Edit `sql/load_fx_flows.sql` and replace the `\copy ... FROM '/tmp/fx_flows.csv'` path with your local CSV path, e.g. `C:/Users/you/path/data/fx_flows.csv`.
  - Then run:
    ```
    psql "postgres://USER:PASS@localhost:5432/stutern" -f sql/load_fx_flows.sql
    ```

After loading, point `DATABASE_URL` at your Postgres.

## How It Works (code overview)

- Entry point: `mcp_postgres_server/server.py`
- Framework: `mcp.server.fastmcp.FastMCP` defines an MCP app with tools.
- DB: `asyncpg` with a lazily‑initialized connection pool.
- Safety: `pg_query` only allows a single `SELECT`/`WITH` statement and auto‑adds `LIMIT` if missing. Comments are stripped to validate the first keyword.
- Transport: set via `TRANSPORT_PROTOCOL` to `stdio` or `streamable-http` (serves on `0.0.0.0:8000`).
- Env loading: `python-dotenv` loads `.env` if present.

## Project Structure

```
.
├─ mcp_postgres_server/
│  ├─ server.py              # MCP server (stdio or HTTP)
│  └─ __init__.py
├─ sql/
│  └─ load_fx_flows.sql      # schema + COPY for sample data
├─ data/
│  └─ fx_flows.csv           # sample dataset
├─ mcp_settings.json         # Claude Desktop stdio config template
├─ pyproject.toml            # console script: mcp-postgres
└─ README.md
```

## Troubleshooting

- Run `pg_health` to verify connectivity and environment.
- For SSL to certain cloud DBs, try `PGSSLMODE=disable`.
- Windows: if `mcp-postgres` is not on PATH, use the module form `python -m mcp_postgres_server.server` or configure Claude Desktop via `mcp_settings.json`.

