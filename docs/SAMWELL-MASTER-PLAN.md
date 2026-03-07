# Samwell — Master Plan

> *"It's over, and can't be helped, and that's one consolation, as they always says in Turkey, ven they cuts the wrong man's head off."*
> — Sam Weller, The Pickwick Papers

## What Samwell Is

A self-hosted AI stack providing a complete local alternative to commercial AI chat services:

- **LibreChat** — Web-based chat interface (frontend + agent orchestrator)
- **Ollama** — Local model inference engine (swappable models, 1B–70B parameters)
- **Containerized MCP Servers** — Tool capabilities (search, code exec, databases, APIs, RAG)
- **Docker Compose** — Container orchestration (no Kubernetes for now)
- **Guardrails Layer** — Safety and content filtering for open-source models

## Hardware

| Role | Machine | Key Specs | Model Range |
|------|---------|-----------|-------------|
| Development | Windows 11 Desktop | i9-13900K, 64GB DDR5, no discrete GPU | 1B–8B (interactive), up to 14B (slow) |
| Production | MacBook Pro | M2 Ultra, 96GB unified memory | 1B–70B (all interactive) |

## Workflow

Three windows, always open:

1. **VS Code** — Edit all files directly, use built-in Git (Source Control sidebar)
2. **Docker Desktop** — Monitor containers, view logs, manage lifecycle
3. **Claude Chat** — Architecture decisions, debugging, phase planning

For routine walkthrough steps, a dedicated **Haiku project** uses per-phase instruction sheets so this conversation stays focused on the hard problems.

## Git Strategy

Local-only version control. No remote repo. Commits at every stable checkpoint.

- **Branch:** `main` only (no feature branches needed for solo work)
- **Commit style:** Short present-tense messages, prefixed by phase
  - `P0: scaffold project structure`
  - `P1: add librechat.yaml with ollama endpoint`
  - `P1: docker compose up works, chat functional`
- **When to commit:** After every step that produces a working (or meaningfully changed) state
- **VS Code workflow:** Source Control panel (Ctrl+Shift+G) → stage files → type message → commit

---

## Phase Overview

### Phase 0 — Project Scaffold
**Goal:** Empty but well-organized project with version control.

- Initialize git repo
- Create directory structure
- Add `.gitignore`, `.env.example`, `README.md`
- First commit

**You'll learn:** Project structure conventions for Docker-based stacks.

**Haiku sheet:** `docs/phases/PHASE-00-SCAFFOLD.md`

---

### Phase 1 — Core Loop (LibreChat + Ollama)
**Goal:** Chat with a local model through LibreChat's web UI.

- Install Ollama natively on Windows
- Pull a small model (e.g., `llama3.2:3b` for fast iteration)
- Configure `librechat.yaml` with Ollama endpoint
- Write `docker-compose.yml` for LibreChat + MongoDB + MeiliSearch
- Verify model switching works in the UI
- Pull a larger model and confirm it also appears

**You'll learn:** How LibreChat's custom endpoint system works, how Ollama serves models via OpenAI-compatible API, Docker Compose networking basics.

**Haiku sheet:** `docs/phases/PHASE-01-CORE-LOOP.md`

**Key gotchas to watch for:**
- Ollama runs natively (not in Docker) on both platforms for GPU access
- Use `host.docker.internal` for container→host networking
- Set `titleModel: "current_model"` to avoid loading a second model
- Set `summarize: false` to avoid unsupported API calls
- LibreChat may default to 4,095 token limit for unknown models

---

### Phase 2 — First MCP Server
**Goal:** Add one MCP server and use it as a tool from LibreChat.

- Choose a simple, high-value MCP server (recommended: **Brave Search** for web search or **Filesystem** for local file access)
- Add it to `docker-compose.yml` as a new service
- Configure it in `librechat.yaml` under `mcpServers`
- Test tool invocation from the chat UI
- Understand the MCP transport types (stdio vs SSE vs Streamable HTTP)

**You'll learn:** How MCP protocol works in practice, how LibreChat discovers and presents tools, how to configure container networking for MCP servers.

**Haiku sheet:** `docs/phases/PHASE-02-FIRST-MCP.md`

---

### Phase 3 — MCP Constellation
**Goal:** Build out the full tool network.

Servers to add (in recommended order):

1. **Code Execution Sandbox** — Docker-in-Docker or sidecar pattern for safe code running
2. **Database Access** — PostgreSQL MCP server + Qdrant vector DB for embeddings
3. **GitHub Integration** — Official GitHub MCP server for repo/PR/issue management
4. **RAG / Document Retrieval** — Qdrant-based RAG pipeline with document ingestion
5. **Slack Integration** — If desired for notifications/queries

Each server follows the same pattern: add service to compose, add config to `librechat.yaml`, test, commit.

**You'll learn:** Docker networking between many containers, resource limits, MCP server configuration patterns.

**Haiku sheet:** `docs/phases/PHASE-03-MCP-CONSTELLATION.md`

---

### Phase 4 — Guardrails Layer
**Goal:** Add safety and content filtering for open-source models.

- Deploy **LLM Guard** as a containerized proxy (input/output scanning)
- Configure **NeMo Guardrails** with Colang rules for dialog flow control
- Optionally run **Llama Guard** (8B safety classifier) as an Ollama sidecar model
- Wire guardrails into the request pipeline (user → guard → model → guard → response)
- Test with adversarial prompts to verify filtering

**You'll learn:** How guardrails frameworks intercept and filter LLM traffic, Colang dialog flow language, layered security architecture.

**Haiku sheet:** `docs/phases/PHASE-04-GUARDRAILS.md`

---

### Phase 5 — Monitoring & Polish
**Goal:** Make the stack observable and maintainable.

- Add **Langfuse** (self-hosted) for LLM request tracing and analytics
- Configure Docker health checks for all services
- Add a `Makefile` or shell scripts for common operations
- Document environment variables and configuration options
- Stress test with concurrent requests and large contexts
- Optimize memory allocation across all containers

**You'll learn:** LLM observability, Docker health management, performance tuning.

**Haiku sheet:** `docs/phases/PHASE-05-MONITORING.md`

---

### Phase 6 — macOS Migration
**Goal:** Move the proven stack to the MacBook Pro M2 Ultra.

- Install OrbStack (not Docker Desktop) for dramatically better macOS performance
- Install Ollama natively (Metal acceleration is automatic, zero config)
- Copy `docker-compose.yml` and `librechat.yaml` — these are platform-portable
- Adjust `.env` for macOS paths and memory allocation
- Pull larger models (32B, 70B) that the M2 Ultra can handle
- Tune `OLLAMA_KEEP_ALIVE`, `OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`
- Verify all MCP servers work identically

**You'll learn:** Apple Silicon memory architecture, OrbStack vs Docker Desktop, large model optimization.

**Haiku sheet:** `docs/phases/PHASE-06-MACOS-MIGRATION.md`

---

## Directory Structure (Target)

```
samwell/
├── README.md
├── .gitignore
├── .env.example                  # Template for environment variables
├── .env                          # Actual env vars (git-ignored)
├── docker-compose.yml            # Core services
├── docker-compose.override.yml   # Local overrides (git-ignored)
├── librechat.yaml                # LibreChat configuration
├── docs/
│   ├── MASTER-PLAN.md            # This file
│   ├── ARCHITECTURE.md           # Diagrams and design decisions
│   └── phases/
│       ├── PHASE-00-SCAFFOLD.md
│       ├── PHASE-01-CORE-LOOP.md
│       ├── PHASE-02-FIRST-MCP.md
│       ├── PHASE-03-MCP-CONSTELLATION.md
│       ├── PHASE-04-GUARDRAILS.md
│       ├── PHASE-05-MONITORING.md
│       └── PHASE-06-MACOS-MIGRATION.md
├── config/
│   ├── guardrails/               # NeMo Guardrails Colang configs
│   └── mcp/                      # Per-server MCP configurations
├── scripts/                      # Helper scripts (backup, health checks)
└── volumes/                      # Docker volume mount points
    ├── mongodb/
    ├── meilisearch/
    ├── qdrant/
    └── shared-data/              # Files accessible to MCP servers
```

## Key Links & References

- [LibreChat Docs — Ollama Setup](https://www.librechat.ai/docs/configuration/librechat_yaml/ai_endpoints/ollama)
- [LibreChat Docs — MCP Servers](https://www.librechat.ai/docs/features/mcp)
- [LibreChat Docs — MCP Server Object Structure](https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs/learn/architecture)
- [Docker MCP Catalog](https://hub.docker.com/u/mcp)
- [Docker MCP Gateway (GitHub)](https://github.com/docker/mcp-gateway)
- [ToolHive — MCP Server Manager](https://github.com/stacklok/toolhive)
- [MCP-Compose](https://github.com/phildougherty/mcp-compose)
- [awesome-mcp-servers (curated list)](https://github.com/appcypher/awesome-mcp-servers)
- [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- [LLM Guard](https://llm-guard.com)
- [Langfuse (self-hosted observability)](https://langfuse.com)
- [OrbStack (macOS Docker alternative)](https://orbstack.dev)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| TBD | Docker Compose over Kubernetes | Personal-scale, single-machine, learning-focused. K8s adds abstraction without benefit at this scale. Migration-ready if needed later. |
| TBD | Ollama native (not containerized) | GPU/Metal acceleration requires native install. Docker cannot access Metal on macOS. |
| TBD | OrbStack over Docker Desktop (macOS) | ~1GB idle RAM vs 4–6GB, 2-second startup vs 10–30 seconds. |
| TBD | Streamable HTTP transport for MCP | Newer spec (March 2025), replaces deprecated SSE. Supports load balancing and standard HTTP auth. |
| TBD | Q4_K_M as default quantization | ~95% quality at 28% FP16 size. Best balance for constrained hardware. |