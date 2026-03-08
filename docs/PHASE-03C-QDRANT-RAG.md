# Phase 3C — Qdrant Vector Database + RAG Pipeline

> **What this phase does:** Adds semantic search and document retrieval capabilities. You'll set up Qdrant as a vector database, pull an embedding model through Ollama, configure the official Qdrant MCP server, and then layer a RAG (Retrieval-Augmented Generation) pipeline on top for document ingestion and retrieval.
>
> **Time estimate:** 90–120 minutes (includes building a custom Docker image)
>
> **Prerequisites:** Phase 3B complete. All previous MCP servers working.

---

## Context for the AI assistant

The user is building **Samwell**, a self-hosted AI stack. Phases 0–3B are complete. Now adding Qdrant (vector DB) and a RAG pipeline. The user types everything themselves.

**Critical context for this phase:**
- The user runs **Ollama natively** on the host, not in Docker. Ollama is accessible at `host.docker.internal:11434` from containers.
- The official `qdrant/mcp-server-qdrant` uses **FastEmbed** for embeddings, not Ollama. It cannot be configured to use Ollama. This is fine — FastEmbed runs locally and requires no API keys.
- The official Qdrant MCP server has only 2 tools: `qdrant-store` and `qdrant-find`. It's a semantic memory store, not a full RAG engine.
- For full RAG (document upload → chunking → embedding → retrieval), a separate MCP server is needed. This phase covers both layers.
- No published Docker Hub image exists for the Qdrant MCP server — it must be built from the repo's Dockerfile or run via `uvx`.
- `mcpSettings.allowedDomains` must be updated to include any new Docker service names.
- Qdrant collection vector dimensions **must exactly match** the embedding model's output dimensions. Mismatches cause silent failures.

**Embedding model for Qdrant MCP server (FastEmbed):** Default is `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). FastEmbed downloads this automatically — no Ollama involved.

**Embedding model for RAG via Ollama:** Pull `nomic-embed-text` (768 dimensions, 274MB). Best all-rounder for local RAG. The Ollama embedding API is `POST http://host.docker.internal:11434/api/embed`.

---

## Part A: Qdrant Vector Database + Official MCP Server

### Official documentation

- Qdrant Docker: https://qdrant.tech/documentation/guides/installation/#docker
- Qdrant MCP server: https://github.com/qdrant/mcp-server-qdrant
- PyPI: https://pypi.org/project/mcp-server-qdrant/
- Qdrant + Ollama embeddings guide: https://qdrant.tech/documentation/embeddings/ollama/

### Step 1: Add Qdrant to docker-compose.yml

Qdrant is a standalone vector database. Add it as a persistent service:

```yaml
  qdrant:
    image: qdrant/qdrant:latest
    container_name: samwell-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./volumes/qdrant:/qdrant/storage
    restart: unless-stopped
```

Port 6333 is the REST API, port 6334 is gRPC. The web dashboard is at `http://localhost:6333/dashboard` — useful for inspecting collections.

### Step 2: Pull the Ollama embedding model

Even though the Qdrant MCP server uses FastEmbed (not Ollama), you'll want an Ollama embedding model for the RAG pipeline in Part B. Pull it now:

```
ollama pull nomic-embed-text
```

This is 274MB and produces 768-dimensional embeddings. You can test it:

```
curl http://localhost:11434/api/embed -d '{"model": "nomic-embed-text", "input": "Hello world"}'
```

### Step 3: Configure the Qdrant MCP server

The official server has no published Docker image. The cleanest approach for LibreChat is running it via `uvx` (Python) as a stdio server inside the LibreChat container. However, LibreChat's container may not have `uvx`/`uv` installed.

**Recommended approach: Docker stdio using uvx image.**

Add to `librechat.yaml` under `mcpServers`:

```yaml
  qdrant:
    command: docker
    args:
      - run
      - -i
      - --rm
      - --network
      - samwell_default
      - -e
      - QDRANT_URL
      - -e
      - COLLECTION_NAME
      - -e
      - EMBEDDING_MODEL
      - ghcr.io/astral-sh/uv:latest
      - uvx
      - mcp-server-qdrant
    env:
      QDRANT_URL: "http://qdrant:6333"
      COLLECTION_NAME: "samwell-memory"
      EMBEDDING_MODEL: "sentence-transformers/all-MiniLM-L6-v2"
    timeout: 60000
    initTimeout: 30000
```

### Understanding this config

- **`--network samwell_default`** — The container needs to reach the `qdrant` service by name. Replace `samwell_default` with your actual Docker Compose network name. Check with `docker network ls` — it's typically `{project-directory-name}_default`.

- **`ghcr.io/astral-sh/uv:latest`** — The official `uv` Python package manager image. `uvx` downloads and runs `mcp-server-qdrant` from PyPI in an isolated environment.

- **`EMBEDDING_MODEL`** — FastEmbed model name. The default `all-MiniLM-L6-v2` produces 384-dimension vectors. FastEmbed downloads it on first run (~90MB), which is why `initTimeout` is set high.

- **`COLLECTION_NAME`** — The Qdrant collection where data is stored. Created automatically on first use.

**Important:** The first run will be slow (30–60 seconds) as FastEmbed downloads the embedding model. Subsequent runs use the cached model.

### Step 4: Update mcpSettings.allowedDomains

Add `qdrant` to your allowed domains:

```yaml
mcpSettings:
  allowedDomains:
    - "mcp-postgres"
    - "qdrant"
    - "host.docker.internal"
```

### Step 5: Start and test

```
docker compose down
docker compose up -d
```

Wait for Qdrant to start, then restart LibreChat:

```
docker compose restart api
```

Check Qdrant is running: open `http://localhost:6333/dashboard` in your browser.

Test the MCP server with prompts:

> "Store this information: The Samwell project uses LibreChat as its frontend, Ollama for inference, and Docker Compose for orchestration"

> "What do you know about the Samwell project's architecture?"

The first prompt should invoke `qdrant-store`, the second should invoke `qdrant-find` and return the stored information.

### Git checkpoint

```
P3C: add qdrant vector DB and MCP server (semantic memory)
```

---

## Part B: RAG Document Retrieval Pipeline

The Qdrant MCP server provides basic semantic memory (store text, search text). A **RAG pipeline** adds the missing pieces: ingesting documents (PDFs, markdown, text files), chunking them into searchable segments, embedding those segments, and storing them in Qdrant for retrieval.

This is the least standardized part of the MCP ecosystem. No single Docker image provides a production-ready RAG pipeline. You have two practical options:

**Option 1: `mcp-ragdocs`** — Full-featured Node.js RAG server with URL and file ingestion, supports Ollama embeddings, includes a web UI. Requires cloning and building.

**Option 2: Build the pipeline separately** — Use Qdrant directly via API calls, ingest documents with a Python script, and rely on the Qdrant MCP server for retrieval only.

This guide covers **Option 1** as it provides the most complete MCP integration.

### Step 6: Clone and build the RAG server

From your `samwell/` directory:

```
git clone https://github.com/qpd-v/mcp-ragdocs.git config/mcp/ragdocs
```

Create a Dockerfile for it at `config/mcp/ragdocs/Dockerfile`:

```dockerfile
FROM node:22-slim

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

EXPOSE 3030
CMD ["node", "dist/index.js"]
```

**Note:** Check the repo's actual structure before building. The README may include a Dockerfile or different build instructions. Adjust as needed — discuss with the AI assistant if the structure differs.

### Step 7: Add the RAG server to docker-compose.yml

```yaml
  mcp-ragdocs:
    build:
      context: ./config/mcp/ragdocs
    container_name: samwell-mcp-ragdocs
    environment:
      QDRANT_URL: "http://qdrant:6333"
      EMBEDDING_PROVIDER: "ollama"
      OLLAMA_URL: "http://host.docker.internal:11434"
      EMBEDDING_MODEL: "nomic-embed-text"
      COLLECTION_NAME: "samwell-docs"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - qdrant
    restart: unless-stopped
```

### Understanding the RAG config

- **`EMBEDDING_PROVIDER: "ollama"`** — Uses your local Ollama instance for embeddings instead of OpenAI.
- **`OLLAMA_URL`** — Points to Ollama on the host via Docker's special DNS name.
- **`COLLECTION_NAME: "samwell-docs"`** — Separate from the Qdrant MCP server's `samwell-memory` collection. Documents and chat memory stay separate.
- **`extra_hosts`** — Needed because this container talks to Ollama on the host.

### Step 8: Add to librechat.yaml

This depends on the transport the RAG server supports. If it's stdio-only, you'll need the Supergateway bridge. Check the repo's docs for transport support.

If it supports SSE/HTTP directly:

```yaml
  ragdocs:
    type: sse
    url: "http://mcp-ragdocs:3030/sse"
    timeout: 60000
    initTimeout: 30000
```

If stdio only, add it as a Docker stdio server or build a Supergateway bridge (the repo may include instructions for this).

Update `mcpSettings.allowedDomains` to include `mcp-ragdocs`.

### Step 9: Build and start

```
docker compose build mcp-ragdocs
docker compose down
docker compose up -d
docker compose logs -f mcp-ragdocs
```

### Step 10: Test the RAG pipeline

Place a markdown or text file in `volumes/shared-data/`:

```
echo # Samwell Architecture Notes > volumes\shared-data\architecture.md
echo. >> volumes\shared-data\architecture.md
echo Samwell uses a three-layer architecture: >> volumes\shared-data\architecture.md
echo 1. Inference layer (Ollama) >> volumes\shared-data\architecture.md
echo 2. Orchestration layer (LibreChat) >> volumes\shared-data\architecture.md
echo 3. Tool layer (MCP servers in Docker) >> volumes\shared-data\architecture.md
```

Then test ingestion and retrieval:

> "Add the document at /data/architecture.md to the knowledge base"

> "Search the knowledge base for information about Samwell's architecture layers"

### Git checkpoint

```
P3C: add RAG document retrieval pipeline with qdrant and ollama embeddings
```

---

## Important notes on embedding dimensions

The Qdrant MCP server (Part A) uses FastEmbed with `all-MiniLM-L6-v2` producing **384-dimension** vectors in the `samwell-memory` collection.

The RAG pipeline (Part B) uses Ollama with `nomic-embed-text` producing **768-dimension** vectors in the `samwell-docs` collection.

**These are separate collections with different dimensions — this is intentional and correct.** You cannot mix embedding models within a single collection. If you ever need to switch models, you must recreate the collection and re-embed all documents.

---

## Checkpoint ✓

- [ ] Qdrant running and accessible at `http://localhost:6333/dashboard`
- [ ] Qdrant MCP server working — model can store and retrieve semantic memories
- [ ] Ollama embedding model (`nomic-embed-text`) pulled and tested
- [ ] RAG pipeline built and running (or alternative approach chosen)
- [ ] Model can ingest documents and retrieve information from them
- [ ] Two git commits for this sub-phase

**Phase 3 complete!** Your full MCP constellation is now: Filesystem, Brave Search, GitHub, PostgreSQL, Code Sandbox, Qdrant, and RAG. Return to the main Claude conversation to plan Phase 4 (Guardrails).

---

## Troubleshooting

**Qdrant dashboard shows empty collections:**
- Collections are created on first use. Run a `qdrant-store` tool call first.

**"Connection refused" to Qdrant from MCP server:**
- Check the Docker network. The MCP container must be on the same network as the `qdrant` service.
- For Docker stdio containers, use `--network samwell_default` in the args.
- Check your network name: `docker network ls`

**FastEmbed download hangs or times out:**
- First run downloads ~90MB model. Increase `initTimeout` to 60000+.
- If persistent, the container may lack internet access. Check DNS resolution.

**Ollama embedding call fails from RAG container:**
- Verify `extra_hosts` includes `host.docker.internal:host-gateway`
- Test from inside the container: `docker exec samwell-mcp-ragdocs curl http://host.docker.internal:11434/api/embed -d '{"model":"nomic-embed-text","input":"test"}'`

**RAG server build fails:**
- Check the repo's README for current build instructions — the Dockerfile above is a template
- Node version requirements may differ. Check `package.json` for engine requirements.
- Discuss specific build errors with the AI assistant

**Dimension mismatch errors:**
- Qdrant rejects points with wrong vector dimensions
- Check which embedding model the server uses and what dimensions it produces
- You cannot change dimensions on an existing collection — delete and recreate it

**Search returns no results after ingestion:**
- The embedding model must be the same for ingestion and search
- Check the collection exists in the Qdrant dashboard
- Verify documents were actually embedded (check point count in dashboard)
