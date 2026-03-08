# Phase 3B — Code Execution Sandbox

> **What this phase does:** Adds a sandboxed code execution MCP server so your local model can write and run JavaScript/Node.js code in disposable Docker containers. This is the highest-risk MCP server in the constellation — it requires Docker socket access and creates sibling containers on your host.
>
> **Time estimate:** 30–45 minutes
>
> **Prerequisites:** Phase 3A complete — GitHub and PostgreSQL servers working, SSE transport pattern understood.

---

## Context for the AI assistant

The user is building **Samwell**, a self-hosted AI stack. Phases 0–3A are complete. Now adding a code execution sandbox using `mcp/node-code-sandbox` from Docker's MCP Catalog. The user types everything themselves.

**Key context:**
- Docker socket is already mounted from Phase 2.
- `mcpSettings.allowedDomains` is already configured from Phase 3A — new SSE services need to be added there.
- This server uses **Docker stdio** transport (same as Brave Search and GitHub).
- The server creates **sibling containers** on the host Docker daemon — not nested containers. This is the Docker-out-of-Docker (DooD) pattern.
- **JavaScript/Node.js only.** No Python execution with this server. For Python, alternatives exist but are less mature as Docker images.
- If tool calls fail silently, check the model first (`qwen3:8b` or `llama3.1:8b` recommended).

---

## Understanding the security model

Before configuring anything, understand what you're enabling. The code sandbox MCP server:

1. Mounts `/var/run/docker.sock` from the host (already done in your compose file)
2. When the model requests code execution, the server runs `docker create` / `docker start` to spin up a fresh `node:22-slim` container
3. Code runs inside that disposable container with configurable memory and CPU limits
4. The container is destroyed after execution
5. Output (stdout, stderr, exit code) is returned to the model

The containers are **siblings** on your host Docker daemon, not nested. They can see the same Docker network and volumes as your other containers unless explicitly restricted. The `SANDBOX_MEMORY_LIMIT` and `SANDBOX_CPU_LIMIT` settings are your primary controls.

### Official documentation

- Docker Hub: https://hub.docker.com/r/mcp/node-code-sandbox
- GitHub: https://github.com/alfonsograziano/node-code-sandbox-mcp

---

## Step 1: Pull the sandbox image and its runtime image

```
docker pull mcp/node-code-sandbox
docker pull node:22-slim
```

The second pull is important — `node:22-slim` is the image the sandbox uses for the disposable execution containers. Without it pre-pulled, the first code execution will be slow while Docker downloads it.

## Step 2: Create a sandbox output directory

```
mkdir volumes\sandbox-output
```

Add `volumes/sandbox-output/` to `.gitignore`.

## Step 3: Add the server to librechat.yaml

Add under your existing `mcpServers` block:

```yaml
  code-sandbox:
    command: docker
    args:
      - run
      - -i
      - --rm
      - -v
      - /var/run/docker.sock:/var/run/docker.sock
      - -e
      - SANDBOX_MEMORY_LIMIT
      - -e
      - SANDBOX_CPU_LIMIT
      - -e
      - SANDBOX_TIMEOUT
      - mcp/node-code-sandbox
    env:
      SANDBOX_MEMORY_LIMIT: "512m"
      SANDBOX_CPU_LIMIT: "0.75"
      SANDBOX_TIMEOUT: "15000"
    timeout: 30000
```

### Understanding the environment variables

- **`SANDBOX_MEMORY_LIMIT: "512m"`** — Each disposable execution container gets at most 512MB RAM. Raise if running memory-intensive computations, lower if you want tighter control.

- **`SANDBOX_CPU_LIMIT: "0.75"`** — Each execution container gets at most 75% of one CPU core. On your i9-13900K this is generous; on the MacBook later you may want to lower it to avoid stealing from Ollama.

- **`SANDBOX_TIMEOUT: "15000"`** — Execution timeout in milliseconds. 15 seconds is reasonable for most code snippets. The default (8 seconds) is often too short for anything involving network requests or complex computation.

- **Note the Docker socket mount in `args`:** Even though the socket is mounted on the LibreChat container, it needs to be explicitly mounted on the `mcp/node-code-sandbox` container too — this container needs to talk to Docker to create execution containers.

## Step 4: Restart and test

```
docker compose down
docker compose up -d
docker compose logs -f api
```

Test with prompts like:

> "Write and run JavaScript code that calculates the first 20 Fibonacci numbers"

> "Run code that fetches the current time and formats it nicely"

> "Write a Node.js script that generates a random password of 16 characters"

You should see the model write code, invoke the sandbox tool, and return the execution output.

**Check Docker Desktop** — you should see ephemeral containers appear briefly and then disappear as code runs and completes.

## Step 5: Test error handling

Ask the model to run intentionally broken code:

> "Run this JavaScript: console.log(undefinedVariable)"

The sandbox should return the error message rather than crashing. Verify the model handles the error gracefully and offers to fix the code.

## Step 6: Test resource limits

Ask for something memory-intensive:

> "Run code that creates an array of 100 million random numbers"

This should hit the 512MB memory limit and fail with an out-of-memory error rather than consuming all your host RAM. If it succeeds, your limit isn't being applied — check the environment variable is being passed correctly.

### Git checkpoint

```
P3B: add code execution sandbox MCP server
```

---

## Available tools

The code sandbox exposes these tools to the model:

- **`sandbox_initialize`** — Creates a new disposable container
- **`sandbox_run_code`** — Executes JavaScript/Node.js code in the sandbox
- **`sandbox_exec`** — Runs a shell command inside the sandbox container
- **`sandbox_stop`** — Destroys the sandbox container
- **`sandbox_search_packages`** — Searches npm for packages (the sandbox can install and use npm packages)

The model can install npm packages and use them in code execution, which is powerful but means network access from the execution container. For tighter security, you could add `--network none` to the execution container's Docker args, but this would break package installation.

---

## Checkpoint ✓

- [ ] Code sandbox MCP server configured
- [ ] Model can write and execute JavaScript code
- [ ] Error handling works (bad code returns errors, doesn't crash)
- [ ] Resource limits are enforced (memory, CPU, timeout)
- [ ] Ephemeral containers appear and disappear in Docker Desktop
- [ ] One git commit for this phase

**Next sub-phase:** Phase 3C — Qdrant Vector Database + RAG Pipeline. Return to the main Claude conversation when ready.

---

## Troubleshooting

**"Cannot connect to the Docker daemon" inside the sandbox:**
- The Docker socket must be mounted on the `mcp/node-code-sandbox` container via the `-v` arg
- Verify: `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock mcp/node-code-sandbox echo test`

**Execution times out with no output:**
- Increase `SANDBOX_TIMEOUT` (default 8000ms may be too short)
- Check Docker Desktop — is the execution container actually starting?
- `node:22-slim` may need to be pulled first

**"Image not found" errors during execution:**
- Pre-pull the runtime image: `docker pull node:22-slim`

**Model writes code but doesn't invoke the sandbox:**
- Model may not recognize it should use the tool. Try explicit prompts: "Use the code sandbox to run this"
- Switch to a model with better tool calling (`qwen3:8b`)
- Try using LibreChat Agents instead of basic chat mode

**Execution container keeps running (doesn't clean up):**
- Check Docker Desktop for orphaned containers with names starting with `sandbox-`
- Manual cleanup: `docker ps -a | grep sandbox | awk '{print $1}' | xargs docker rm -f`
