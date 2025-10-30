MCP Postgres Server (Python)

A Python MCP server that connects to PostgreSQL and exposes safe, read-only tools over stdio or streamable HTTP. Use it from MCP-compatible clients (Claude, ChatGPT) to query a Postgres database.

Project Structure

```
.
├─ mcp_postgres_server/
│  ├─ server.py              # MCP server (stdio or HTTP; entrypoint: mcp-postgres)
│  └─ __init__.py
├─ sql/
│  └─ load_fx_flows.sql      # schema + COPY for sample data
├─ data/
│  └─ fx_flows.csv           # sample FX flows dataset
├─ mcp_settings.json         # ready-to-paste Claude Desktop stdio config
├─ pyproject.toml            # defines console script: mcp-postgres
└─ README.md
```

Hosted Option (HTTP)

- Server URL: https://stutern.onrender.com/mcp
- No local setup required; the hosted database already contains the `fx_flows` dataset.
- ChatGPT: Settings > Connectors > Add MCP server (HTTP) > use the URL above.
- Claude Desktop: Settings > Tools > Add MCP server (HTTP) > use the URL above.

Local Option (stdio via Claude Desktop)

Only Claude Desktop supports launching local stdio MCP servers today.

1) Install Docker
- Install Docker Desktop: https://docs.docker.com/get-started/get-docker/

2) Start Postgres and load sample data (from repo root)
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

3) Install the package (console script: `mcp-postgres`)
```
pip install .
```

4) Configure Claude Desktop (stdio)
- Open your `claude_desktop_config.json` and under `mcpServers`, paste the contents of `mcp_settings.json`.
- Ensure `DATABASE_URL` matches your local instance, e.g. `postgres://app:app@localhost:5438/stutern`.

5) Optional: run locally by hand
```
# stdio (Claude will normally launch this for you)
set TRANSPORT_PROTOCOL=stdio
set DATABASE_URL=postgres://app:app@localhost:5438/stutern
mcp-postgres

# or
python -m mcp_postgres_server.server
```

HTTP Self‑Hosting (optional)

To run your own HTTP instance (for clients that support HTTP transport):
```
set TRANSPORT_PROTOCOL=streamable-http
set DATABASE_URL=postgres://app:app@localhost:5438/stutern
mcp-postgres   # serves on 0.0.0.0:8000
```
Then point your client’s MCP server URL to `http://<host>:8000/mcp`.

Provided Tools

- `pg_health` – server version, current db/schema, env summary
- `pg_list_tables(schema='public', include_views=False)` – list tables (and optionally views)
- `pg_describe_table(table, schema='public')` – describe table columns
- `pg_query(sql, params=None, row_limit=100)` – single read-only query; appends LIMIT if missing

Environment

- `DATABASE_URL` – full Postgres DSN, e.g. `postgres://user:pass@host:port/db`
- `PGSSLMODE` – set to `disable` to turn off SSL verification if needed
- `TRANSPORT_PROTOCOL` – `stdio` (local) or `streamable-http` (HTTP server)

Troubleshooting

- Call `pg_health` to verify connectivity and environment.
- For SSL hiccups to cloud DBs, try `PGSSLMODE=disable`.

