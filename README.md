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
$env:DATABASE_URL = "postgres://app:app@localhost:5432/stutern"
py -m mcp_postgres_server.server   # serves on 0.0.0.0:8000

# macOS/Linux
export TRANSPORT_PROTOCOL=streamable-http
export DATABASE_URL=postgres://app:app@localhost:5432/stutern
python3 -m mcp_postgres_server.server   # serves on 0.0.0.0:8000
```

Point your client to `http://<host>:8000/mcp`.


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
    psql "postgres://USER:PASSWORD@localhost:5432/DATABASE" -f sql/load_fx_flows.sql
    ```

After loading, point `DATABASE_URL` in `env` and `claude desktop settings` at your Postgres.

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

## How It Works (code overview)

- Entry point: `mcp_postgres_server/server.py`
- Framework: `mcp.server.fastmcp.FastMCP` defines an MCP app with tools.
- DB: `asyncpg` with a lazily‑initialized connection pool.
- Safety: `pg_query` only allows a single `SELECT`/`WITH` statement and auto‑adds `LIMIT` if missing. Comments are stripped to validate the first keyword.
- Transport: set via `TRANSPORT_PROTOCOL` to `stdio` or `streamable-http` (serves on `0.0.0.0:8000`).
- Env loading: `python-dotenv` loads `.env` if present.
