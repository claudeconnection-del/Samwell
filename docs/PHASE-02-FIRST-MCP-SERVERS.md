# Phase 2 — First MCP Servers (Filesystem + Brave Search)

> **What this phase does:** Connects your first two MCP tool servers to LibreChat, teaching both the stdio transport pattern (server runs inside LibreChat's container) and the containerized HTTP pattern (server runs as its own Docker container). By the end, your local model will be able to read/write files on disk and search the web.
>
> **Time estimate:** 60–90 minutes
>
> **Prerequisites:** Phase 1 complete — LibreChat talking to Ollama, multiple models verified.

---

## Context for the AI assistant

The user is building **Samwell**, a self-hosted AI stack (LibreChat + Ollama + containerized MCP servers). Phases 0 and 1 are complete — the core chat loop works. Now they're adding their first MCP servers. The user types everything themselves to learn. Guide them through each step and explain what each configuration option does.

**Important lessons from earlier phases:**
- If the user reports a config variable isn't working, direct them to the official docs URLs listed in this document rather than guessing at the correct name. Previous hallucination of `ALLOW_USER_REGISTRATION` (correct: `ALLOW_REGISTRATION`) cost time.
- YAML formatting has been fine so far but remains a common error source — validate if issues arise.

**Critical note about MCP + Ollama:** Tool calling with local models is **model-dependent and sometimes unreliable**. Not all models support function/tool calling well. If the model doesn't generate proper tool-call responses, MCP tools won't work. Recommended models for tool calling: `qwen3:8b`, `llama3.1:8b`, `qwen3:1.7b` (surprisingly capable). Models like `deepseek-r1` and base `llama3.2` are weaker at tool calling. If tools aren't being invoked, the first thing to check is the model, not the MCP config.

**Streaming + tool calling issue:** There is a known issue where Ollama's streaming implementation can break tool/function calls. If tool calls silently fail (the model acknowledges it should use a tool but nothing happens), try disabling streaming or using the LibreChat Agents feature rather than basic chat mode, as Agents handle tool orchestration more explicitly.

---

## Part A: Filesystem MCP Server (Stdio Transport)

The filesystem server is the simplest possible MCP integration. It uses **stdio transport**, meaning LibreChat spawns the MCP server as a child process *inside its own container* and communicates via stdin/stdout. No networking, no ports, no separate container.

### Official documentation

- LibreChat MCP feature docs: https://www.librechat.ai/docs/features/mcp
- LibreChat MCP server config structure: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers
- LibreChat MCP settings (allowedDomains / SSRF): https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_settings
- Official filesystem MCP server: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem

### Step 1: Understand what you're about to configure

When you add a `command`-based MCP server to `librechat.yaml`, LibreChat runs that command **inside its own Docker container** at startup. The filesystem server (`@modelcontextprotocol/server-filesystem`) gives the model tools to read files, write files, list directories, search files, and get file metadata — all scoped to specific directories you specify.

The path you give the filesystem server must be a path **inside the LibreChat container**, which means it needs to be a volume you've already mounted. Your `docker-compose.yml` from Phase 1 already mounts `./volumes/shared-data:/data` — that's the path you'll use.

### Step 2: Add the mcpServers block to librechat.yaml

Open `librechat.yaml` in VS Code. Add the `mcpServers` section as a **top-level key** (same indentation level as `endpoints`). Do not nest it inside `endpoints`:

```yaml
version: 1.2.1

cache: true

mcpServers:
  filesystem:
    command: npx
    args:
      - -y
      - "@modelcontextprotocol/server-filesystem"
      - /data
    timeout: 30000

endpoints:
  custom:
    - name: "Ollama"
      # ... your existing Ollama config stays here unchanged
```

### Understanding each field

- **`filesystem`** — This is the server's name (your choice). It appears in LibreChat's UI dropdown.

- **`command: npx`** — The executable to run. Since LibreChat's container is Node-based, `npx` is available. It downloads and runs the npm package on the fly.

- **`args`** — Arguments passed to the command. `-y` auto-confirms the npx install prompt. The package name is the official MCP filesystem server. `/data` is the directory the server can access — this is the container-internal path that maps to your `./volumes/shared-data/` on the host.

- **`timeout: 30000`** — Milliseconds before a tool call times out. 30 seconds is generous for file operations.

- **Why no `type` field?** — When `command` is present and no `url` is specified, LibreChat infers `type: stdio` automatically.

### Step 3: Add a test file

Before restarting, create a file in your shared data directory so there's something for the model to find:

```
echo This is a test file for Samwell's filesystem MCP server. > volumes\shared-data\hello.txt
```

### Step 4: Restart LibreChat

```
docker compose restart api
```

Watch the logs for MCP initialization:

```
docker compose logs -f api
```

Look for log lines mentioning MCP server initialization. You should see the filesystem server starting up. If you see errors like "Failed to initialize," check:

1. Is the YAML valid? (indentation, colons, quotes)
2. Is `mcpServers` at the top level, not nested under another key?
3. Does the `/data` path exist in the container? (It should, from your Phase 1 volume mount)

### Step 5: Test the filesystem server

Open LibreChat in your browser (http://localhost:3080).

**Important:** MCP tools appear in a dropdown in the chat interface, below your text input, when you're using a compatible endpoint. Look for the MCP servers dropdown — you should see "filesystem" listed.

Select the filesystem server, then ask the model something like:

> "List all files in the /data directory"

or

> "Read the contents of /data/hello.txt"

The model should invoke the filesystem tool and return results.

**If tools don't appear in the dropdown:**
- You may need to use LibreChat's **Agents** feature instead of basic chat. Create an Agent (sidebar → Agents → New Agent), select your Ollama model, and enable the filesystem MCP tools in the agent builder.
- Verify you're using a model that supports tool calling (`qwen3:8b` or `llama3.1:8b` recommended).

**If the model acknowledges the tool but nothing happens:**
- This is likely the Ollama streaming + tool calling issue. Try a different model first. If the problem persists across models, it may require disabling streaming (discuss with Claude in the main conversation).

### Step 6: Test write operations

Ask the model to create a file:

> "Create a file at /data/samwell-test.txt with the contents 'Samwell filesystem MCP is working'"

Then verify it appeared on your host machine — check `volumes\shared-data\` in VS Code's file explorer or the terminal:

```
type volumes\shared-data\samwell-test.txt
```

### Git checkpoint

```
Stage and commit: P2: add filesystem MCP server (stdio transport)
```

---

## Part B: Brave Search MCP Server (Containerized Pattern)

Now you'll add a second MCP server using a different approach. The Brave Search server runs **as its own Docker container** via the official `mcp/brave-search` image from Docker's MCP Catalog. This teaches the containerized pattern you'll use for most MCP servers in Phase 3.

For this phase, you'll still use **stdio transport** via Docker — LibreChat spawns the container with `docker run -i` and communicates via stdin/stdout. The container is ephemeral (created per-session) rather than long-running. This is how Docker's MCP Catalog images are designed to work.

### Official documentation

- Brave Search MCP server (GitHub): https://github.com/brave/brave-search-mcp-server
- Docker MCP Catalog — Brave Search: https://hub.docker.com/r/mcp/brave-search
- Brave Search API signup: https://api-dashboard.search.brave.com

### Step 1: Get a Brave Search API key

Go to https://api-dashboard.search.brave.com and create an account.

**Pricing note (as of early 2026):** Brave recently replaced its free tier with a credit-based system. New signups get **$5 in monthly credits** (~1,000 queries at $5/1000 requests). This requires a credit card on file. The credits auto-renew monthly, so for development and testing purposes it's effectively free — but be aware that overages will be charged. You also need to add a Brave Search API attribution to your project for the free credits.

Once you have your key, add it to your `.env` file:

```
BRAVE_API_KEY=your-key-here
```

### Step 2: Pull the Docker image

```
docker pull mcp/brave-search
```

This is the official Brave Search MCP server from Docker's curated MCP Catalog — these images are security-reviewed and maintained.

### Step 3: Pass the API key into LibreChat's environment

Your `docker-compose.yml` needs to pass the Brave API key to the LibreChat container, since LibreChat will be spawning the Brave search Docker container and needs to forward the key.

Open `docker-compose.yml` and add `BRAVE_API_KEY` to the `api` service's environment:

```yaml
  api:
    image: ghcr.io/danny-avila/librechat-dev:latest
    container_name: samwell-librechat
    ports:
      - "3080:3080"
    depends_on:
      - mongodb
      - meilisearch
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - MONGO_URI=${MONGO_URI}
      - MEILI_HOST=http://meilisearch:7700
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
      - CREDS_KEY=${CREDS_KEY}
      - CREDS_IV=${CREDS_IV}
      - JWT_SECRET=${JWT_SECRET}
      - JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}
      - BRAVE_API_KEY=${BRAVE_API_KEY}
    volumes:
      - ./librechat.yaml:/app/librechat.yaml
      - ./volumes/shared-data:/data
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
```

**Critical addition: the Docker socket mount.** The line `- /var/run/docker.sock:/var/run/docker.sock` gives the LibreChat container the ability to spawn other Docker containers. This is necessary because the `docker run` command in the MCP config will be executed *from inside* the LibreChat container. Without this mount, `docker` commands will fail.

**Security note:** Mounting the Docker socket is a significant privilege — it effectively gives the container root-level access to the host's Docker daemon. This is acceptable for local development but should be reconsidered for production. We'll address this in Phase 4 (Guardrails).

### Step 4: Add Brave Search to librechat.yaml

Add the `brave-search` entry under your existing `mcpServers` block:

```yaml
mcpServers:
  filesystem:
    command: npx
    args:
      - -y
      - "@modelcontextprotocol/server-filesystem"
      - /data
    timeout: 30000

  brave-search:
    command: docker
    args:
      - run
      - -i
      - --rm
      - -e
      - BRAVE_API_KEY
      - mcp/brave-search
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"
    timeout: 30000
```

### Understanding this config vs the filesystem config

- **`command: docker`** — Instead of `npx`, this runs a Docker command. LibreChat will execute `docker run -i --rm -e BRAVE_API_KEY mcp/brave-search` as a child process.

- **`-i`** — Interactive mode, keeping stdin open. Required for stdio transport so LibreChat can send MCP messages to the container.

- **`--rm`** — Auto-remove the container when it exits. These are ephemeral — they spin up per session.

- **`-e BRAVE_API_KEY`** — Passes the environment variable into the container.

- **`env` block** — Tells LibreChat to set this environment variable before running the command. The `${BRAVE_API_KEY}` syntax reads from LibreChat's own environment (which gets it from your `.env` via `docker-compose.yml`).

- **This is still stdio transport** — even though it uses Docker, the communication mechanism is the same as filesystem: stdin/stdout piped through the process. The difference is that the process is a Docker container rather than a local npx package.

### Step 5: Restart and verify

```
docker compose down
docker compose up -d
docker compose logs -f api
```

Using `down` then `up` instead of `restart` because you changed `docker-compose.yml` (added the socket mount and env var). Watch the logs for both MCP servers initializing.

### Step 6: Test Brave Search

Open LibreChat, select the Brave Search MCP server from the dropdown, and ask:

> "Search the web for recent news about self-hosted AI tools"

The model should invoke the `brave_web_search` tool and return results with titles, URLs, and snippets.

Other tools available from Brave Search include: `brave_local_search` (businesses/places), `brave_image_search`, `brave_video_search`, `brave_news_search`, and `brave_summarize` (AI-summarized results).

**If the search fails with an API error:**
- Check your API key is correct in `.env`
- Verify the key works directly: `docker run --rm -e BRAVE_API_KEY=your-key mcp/brave-search` (should start without errors, then you can Ctrl+C)
- Check LibreChat logs for specific error messages

### Git checkpoint

```
Stage and commit: P2: add brave search MCP server (docker stdio transport)
```

---

## Understanding the Two Transport Patterns

You've now seen both fundamental patterns for connecting MCP servers to LibreChat:

**Pattern 1 — Inline stdio (Filesystem):**
LibreChat runs `npx @modelcontextprotocol/server-filesystem /data` as a child process inside its own container. Communication happens over stdin/stdout. The server has no network presence — it lives and dies with LibreChat.

**Pattern 2 — Docker stdio (Brave Search):**
LibreChat runs `docker run -i --rm mcp/brave-search` which spawns a *separate container* that communicates over stdin/stdout piped through Docker. The container is ephemeral — created for each session and destroyed after.

**Pattern 3 — HTTP/SSE (used in Phase 3):**
MCP servers run as *long-lived Docker services* in your docker-compose stack, each exposing an HTTP endpoint. LibreChat connects to them by URL. This is the pattern for servers that are expensive to start up, need persistent state, or that you want running continuously. In `librechat.yaml`, this uses `type: sse` or `type: streamable-http` with a `url` field instead of `command`.

Phase 3 will introduce Pattern 3 when you add the code execution sandbox, database servers, and other long-running services that belong in their own containers.

---

## Checkpoint ✓

At this point you should have:

- [ ] Filesystem MCP server working — model can read and write files in `/data`
- [ ] Brave Search MCP server working — model can search the web
- [ ] Understanding of stdio transport (both inline and Docker variants)
- [ ] Docker socket mounted for container-spawning capability
- [ ] `.env` updated with `BRAVE_API_KEY`
- [ ] Two git commits for this phase

**Your git log should now look something like:**

```
P2: add brave search MCP server (docker stdio transport)
P2: add filesystem MCP server (stdio transport)
P1: core loop functional — librechat + ollama verified
P1: add librechat.yaml with ollama endpoint
P1: add docker-compose.yml with librechat, mongodb, meilisearch
P0: scaffold project structure
```

**Next phase:** Phase 3 — MCP Constellation. Return to the main Claude conversation to plan which servers to add and how to use the HTTP/SSE transport pattern for long-running containerized services.

---

## Troubleshooting

**"MCP server not found" or servers don't appear in dropdown:**
- Verify `mcpServers` is a top-level key in `librechat.yaml`, not nested under `endpoints` or `interface`
- Restart LibreChat fully: `docker compose restart api`
- Check logs: `docker compose logs api | grep -i mcp`

**"docker: command not found" inside LibreChat container:**
- The Docker socket mount (`/var/run/docker.sock`) is missing from `docker-compose.yml`
- Also verify the Docker CLI is available in the LibreChat image (it should be in recent versions)

**Tool calls silently fail (model says "I'll search for that" but no results appear):**
1. Check the model — switch to `qwen3:8b` or `llama3.1:8b` which have solid tool-calling support
2. Try using LibreChat's **Agents** feature instead of basic chat
3. Check LibreChat logs for errors during tool execution
4. This may be the known Ollama streaming + tool calling issue

**Filesystem server can't find files:**
- Remember: paths in MCP tool calls are *container paths*, not host paths
- `/data` inside the container = `./volumes/shared-data/` on your host
- Check the file exists on the host side first

**Brave Search returns "401 Unauthorized":**
- API key issue. Verify in `.env`, verify it's passed through `docker-compose.yml` environment, and verify it's referenced in `librechat.yaml` env block
- Test the key directly: `curl -H "X-Subscription-Token: YOUR_KEY" "https://api.search.brave.com/res/v1/web/search?q=test"`

**"Domain is not allowed" error in logs:**
- LibreChat has SSRF protection. If you see this for MCP servers connecting to internal addresses, you may need to add an `mcpSettings.allowedDomains` block. See: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_settings
- This is more likely to be relevant in Phase 3 with HTTP-transport servers than in this phase.

**LibreChat exits on startup with validation error:**
- Your `librechat.yaml` has a schema error. Check the exact error message in logs.
- Validate YAML syntax at https://www.yamllint.com
- If needed, set `CONFIG_BYPASS_VALIDATION=true` temporarily to debug (not recommended for production)
- Docs: https://www.librechat.ai/docs/configuration/librechat_yaml
