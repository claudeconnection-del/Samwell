# Phase 3A — GitHub + PostgreSQL MCP Servers

> **What this phase does:** Adds two MCP servers that teach different transport patterns. GitHub uses the familiar Docker stdio approach (quick win). PostgreSQL introduces **SSE transport** — a persistent Docker Compose service that LibreChat connects to by URL instead of spawning a process. This is the pattern you'll use for most production MCP servers.
>
> **Time estimate:** 60–90 minutes
>
> **Prerequisites:** Phase 2 complete — Filesystem and Brave Search MCP servers working.

---

## Context for the AI assistant

The user is building **Samwell**, a self-hosted AI stack (LibreChat + Ollama + containerized MCP servers). Phases 0–2 are complete. The user has working stdio MCP servers (filesystem, brave search). Now they're adding GitHub (Docker stdio) and PostgreSQL (SSE transport as a persistent Docker Compose service).

**Key lessons from previous phases:**
- If a config variable doesn't work, check official docs URLs in this document first.
- Tool calling depends on model choice — `qwen3:8b` and `llama3.1:8b` work best.
- The Docker socket is already mounted from Phase 2.

**Critical new concept this phase: SSE transport.** Unlike stdio (LibreChat spawns a process), SSE servers run as persistent Docker Compose services. LibreChat connects to them by URL. This requires `mcpSettings.allowedDomains` — without it, LibreChat's SSRF protection blocks Docker service names. **Adding `allowedDomains` switches LibreChat from "block known bad" to "allow only listed" mode** — a subtle but common source of broken connections.

---

## Part A: GitHub MCP Server (Docker Stdio)

GitHub's official MCP server is the most mature in the ecosystem. It uses the same Docker stdio pattern as Brave Search — a quick win that expands your toolkit.

### Official documentation

- GitHub MCP server repo: https://github.com/github/github-mcp-server
- Docker image: https://hub.docker.com/r/mcp/github (mirror) or `ghcr.io/github/github-mcp-server` (primary)
- LibreChat MCP config: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers

### Step 1: Create a GitHub Personal Access Token

Go to https://github.com/settings/tokens and create a **classic** token (not fine-grained). Classic tokens (`ghp_` prefix) are recommended because the GitHub MCP server **auto-hides tools your token can't use**, keeping the tool list clean for the LLM.

Select these scopes: `repo`, `read:org`, `gist`, `notifications`, `project`, `read:discussion`.

Add the token to your `.env`:

```
GITHUB_PAT=ghp_your_token_here
```

### Step 2: Pull the Docker image

```
docker pull ghcr.io/github/github-mcp-server
```

If you get authentication errors from GHCR, run `docker logout ghcr.io` first — expired credentials cause pull failures.

### Step 3: Pass the token through docker-compose.yml

Add `GITHUB_PAT` to the `api` service's environment in `docker-compose.yml`:

```yaml
    environment:
      # ... existing vars ...
      - GITHUB_PAT=${GITHUB_PAT}
```

### Step 4: Add GitHub to librechat.yaml

Add under your existing `mcpServers` block:

```yaml
  github:
    command: docker
    args:
      - run
      - -i
      - --rm
      - -e
      - GITHUB_PERSONAL_ACCESS_TOKEN
      - -e
      - GITHUB_TOOLSETS
      - ghcr.io/github/github-mcp-server
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_PAT}"
      GITHUB_TOOLSETS: "repos,issues,pull_requests,code_security"
    timeout: 30000
```

### Understanding the config

- **`GITHUB_TOOLSETS`** limits which tool groups are exposed to the LLM. The full server has 40+ tools across many groups — showing them all confuses smaller models. Start with `repos,issues,pull_requests,code_security` and expand as needed.

- **`GITHUB_READ_ONLY=1`** (optional) disables all write operations if you want a safety net while testing.

- The deprecated npm package `@modelcontextprotocol/server-github` is **non-functional since April 2025** — only use the Docker image.

### Step 5: Restart and test

```
docker compose down
docker compose up -d
docker compose logs -f api
```

Test with prompts like:

> "List my GitHub repositories"
> "Search GitHub for MCP server projects in TypeScript"
> "Show me recent issues on the LibreChat repo"

### Git checkpoint

```
P3A: add github MCP server (docker stdio)
```

---

## Part B: PostgreSQL MCP Server (SSE Transport)

This is the architectural leap in Phase 3. Instead of LibreChat spawning a process, the PostgreSQL MCP server runs as a **persistent Docker Compose service** that LibreChat connects to via HTTP/SSE.

### Why not the official Anthropic server?

The Anthropic reference server (`mcp/postgres` on Docker Hub) has an **unpatched SQL injection vulnerability**. Despite wrapping queries in `BEGIN TRANSACTION READ ONLY`, the node-postgres driver allows multi-statement execution. An agent can escape read-only mode with `COMMIT; DROP SCHEMA public CASCADE;`. The image was archived July 2025 and remains unpatched.

Use **`crystaldba/postgres-mcp`** instead — 2,200+ GitHub stars, actively maintained, proper access control, and native SSE transport.

### Official documentation

- crystaldba/postgres-mcp: https://github.com/crystaldba/postgres-mcp
- LibreChat MCP settings (allowedDomains): https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_settings
- LibreChat MCP servers config: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers

### Step 1: Add PostgreSQL and the MCP server to docker-compose.yml

Add these two new services. The database itself is standard Postgres. The MCP server connects to it and exposes tools via SSE:

```yaml
  postgres-db:
    image: postgres:16
    container_name: samwell-postgres
    environment:
      POSTGRES_USER: samwell
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: samwell_db
    volumes:
      - ./volumes/postgres:/var/lib/postgresql/data
    restart: unless-stopped

  mcp-postgres:
    image: crystaldba/postgres-mcp:latest
    container_name: samwell-mcp-postgres
    command: ["--transport=sse", "--access-mode=restricted"]
    environment:
      DATABASE_URI: "postgresql://samwell:${POSTGRES_PASSWORD}@postgres-db:5432/samwell_db"
    ports:
      - "8001:8000"
    depends_on:
      - postgres-db
    restart: unless-stopped
```

### Understanding the new patterns

- **`command: ["--transport=sse", "--access-mode=restricted"]`** — This tells the MCP server to listen for SSE connections on port 8000 (its default), and to only allow read-only SQL queries. Use `unrestricted` when you need write access.

- **No `extra_hosts` needed** — Both services are on the same Docker network. `postgres-db` resolves by service name.

- **`ports: - "8001:8000"`** — Exposes the SSE endpoint to the host on port 8001 (for debugging). LibreChat connects internally via the Docker network on port 8000.

- **Why a separate `volumes/postgres` directory?** — Database data persists across `docker compose down`. Add this to `.gitignore` if you haven't already.

### Step 2: Add POSTGRES_PASSWORD to .env

```
POSTGRES_PASSWORD=samwell-pg-dev-password
```

Add `volumes/postgres/` to `.gitignore` if not already covered.

### Step 3: Add mcpSettings and the server to librechat.yaml

This is the critical new piece. You need **both** `mcpSettings` (to allow the Docker service name) and the server entry:

```yaml
mcpSettings:
  allowedDomains:
    - "mcp-postgres"
    - "host.docker.internal"

mcpServers:
  # ... your existing servers (filesystem, brave-search, github) ...

  postgres:
    type: sse
    url: "http://mcp-postgres:8000/sse"
    timeout: 30000
    initTimeout: 15000
```

### Understanding mcpSettings.allowedDomains

This is the most common source of confusion when adding SSE/HTTP MCP servers:

- **Without `allowedDomains`:** LibreChat blocks internal domains (localhost, private IPs, `.internal`) but allows all external domains.
- **With `allowedDomains`:** LibreChat switches to allowlist-only mode. **Only listed domains work. Everything else is blocked.**
- You must include `host.docker.internal` if you still need it for Ollama connectivity.
- Docker service names (`mcp-postgres`) must be listed exactly as they appear in the `url` field.
- If you add more SSE servers later, they must be added here too.

### Step 4: Start the expanded stack

```
docker compose down
docker compose up -d
```

Watch the MCP server startup:

```
docker compose logs -f mcp-postgres
```

You should see it connect to PostgreSQL and start listening for SSE connections.

### Step 5: Create some test data

Connect to the database and create a sample table:

```
docker exec -it samwell-postgres psql -U samwell -d samwell_db
```

In the psql prompt:

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO projects (name, description) VALUES
    ('Samwell', 'Self-hosted AI stack with LibreChat, Ollama, and MCP servers'),
    ('Pickwick Papers', 'A journey of curious amateurs observing the world');

\q
```

### Step 6: Test the SSE server

In LibreChat, select the postgres MCP server and try:

> "List all tables in the database"
> "Show me all projects and their descriptions"
> "Describe the schema of the projects table"

The model should invoke SQL tools and return structured results.

**If the server doesn't appear or connections fail:**
- Check logs: `docker compose logs mcp-postgres`
- Verify `allowedDomains` includes the exact service name
- Check that `type: sse` and `url` are correct (note: `/sse` path at the end)
- Increase `initTimeout` if the server is slow to start

### Git checkpoint

```
P3A: add postgres MCP server (SSE transport) with crystaldba/postgres-mcp
```

---

## What you've learned in this phase

**Docker stdio (GitHub):** LibreChat spawns `docker run -i --rm ...` as a child process. Simple, ephemeral, no networking to configure. Best for stateless servers with no startup cost.

**SSE transport (PostgreSQL):** The MCP server runs as a persistent Docker Compose service exposing an HTTP/SSE endpoint. LibreChat connects by URL. Requires `mcpSettings.allowedDomains`. Best for stateful servers (databases), servers with expensive startup, or servers that need their own configuration and volumes.

**`mcpSettings.allowedDomains`:** The switch from "block known bad" to "allow only listed" mode. Every SSE/HTTP server's Docker service name must be listed.

---

## Checkpoint ✓

- [ ] GitHub MCP server working — model can search repos, list issues
- [ ] PostgreSQL database running with test data
- [ ] PostgreSQL MCP server running as persistent SSE service
- [ ] Model can query the database through the MCP server
- [ ] `mcpSettings.allowedDomains` configured correctly
- [ ] Understanding of SSE vs stdio transport patterns
- [ ] Two git commits for this phase

**Next sub-phase:** Phase 3B — Code Execution Sandbox. Return to the main Claude conversation when ready.

---

## Troubleshooting

**"Domain is not allowed" error in logs:**
- You need `mcpSettings.allowedDomains` with the Docker service name
- Remember: adding `allowedDomains` switches to allowlist mode — include `host.docker.internal` too
- Docs: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_settings

**PostgreSQL MCP server exits immediately:**
- Check `DATABASE_URI` format — must be `postgresql://user:pass@host:port/dbname`
- Ensure `postgres-db` service is healthy before `mcp-postgres` starts
- Check: `docker compose logs mcp-postgres`

**GitHub MCP server shows no tools:**
- Your PAT may lack required scopes. Regenerate with `repo`, `read:org`, `gist`, `notifications`, `project`, `read:discussion`
- Classic tokens (`ghp_`) auto-hide unavailable tools. Fine-grained tokens show all but fail at runtime.

**SSE server appears in dropdown but tool calls fail:**
- Check `initTimeout` — default 10 seconds may be insufficient. Use 15000+ ms.
- Verify the URL path ends with `/sse`
- Check LibreChat logs for specific error messages
