# Phase 1 — Core Loop (LibreChat + Ollama)

> **What this phase does:** Gets you chatting with a locally-running LLM through LibreChat's web interface. This is the foundation everything else builds on.
>
> **Time estimate:** 45–90 minutes (depending on model download speeds)
>
> **Prerequisites:** Phase 0 complete. Docker Desktop running on Windows 11.

---

## Context for the AI assistant

The user is building **Samwell**, a self-hosted AI stack. Phase 0 (scaffold) is done. Now they need LibreChat connected to Ollama for local inference. The user types everything themselves — provide guidance and let them build it. They should understand each config option, not just paste it. If they hit networking issues between Docker containers and the host-running Ollama, walk them through `host.docker.internal` and what it means. Common problems: Ollama not listening on all interfaces, wrong baseURL, token limit misconfiguration.

---

## Step 1: Install Ollama natively

Ollama must run natively on Windows (not in Docker) because you don't have a discrete GPU, and Docker can't pass through integrated graphics. On macOS later, this is even more critical — Docker cannot access Metal acceleration.

Download and install from https://ollama.com/download

After install, verify in a terminal:

```
ollama --version
```

Then pull a small, fast model for testing. This avoids waiting for large downloads while debugging configuration:

```
ollama pull llama3.2:3b
```

This is a ~2GB download. While it downloads, continue with the next steps.

Verify Ollama is serving its API:

```
curl http://localhost:11434/v1/models
```

You should see a JSON response listing your pulled models. If `curl` isn't available, open `http://localhost:11434` in a browser — you should see "Ollama is running".

### Understanding what just happened

Ollama runs as a background service on Windows, listening on port 11434. It exposes an **OpenAI-compatible API** at `/v1/` — this is what LibreChat will connect to. The model files live in `%USERPROFILE%\.ollama\models\`.

**Git checkpoint:** No project files changed yet — nothing to commit.

---

## Step 2: Create `docker-compose.yml`

Open VS Code in your `samwell/` directory. Create `docker-compose.yml` in the project root.

This file defines three services that LibreChat needs:

1. **api** — LibreChat itself (Node.js app serving the web UI)
2. **mongodb** — Database for conversations, users, settings
3. **meilisearch** — Search engine for conversation history

Type this yourself, understanding each section:

```yaml
version: '3.8'

services:
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
    volumes:
      - ./librechat.yaml:/app/librechat.yaml
      - ./volumes/shared-data:/data
    restart: unless-stopped

  mongodb:
    image: mongo:7
    container_name: samwell-mongodb
    volumes:
      - ./volumes/mongodb:/data/db
    restart: unless-stopped

  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: samwell-meilisearch
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
    volumes:
      - ./volumes/meilisearch:/meili_data
    restart: unless-stopped
```

### Key things to understand as you type this

- **`extra_hosts`** — This line is critical. It creates a DNS entry inside the LibreChat container so that `host.docker.internal` resolves to your Windows host machine's IP. This is how LibreChat reaches Ollama, which is running natively outside Docker.

- **`${MONGO_URI}`** — The `${}` syntax reads from your `.env` file. Docker Compose automatically loads `.env` from the same directory.

- **`volumes: - ./librechat.yaml:/app/librechat.yaml`** — This bind-mounts your local config file into the container, overriding LibreChat's default. Changes to this file take effect on container restart.

- **`depends_on`** — Tells Compose to start MongoDB and MeiliSearch before LibreChat. Note: this only waits for the container to *start*, not for the service to be *ready*. LibreChat handles reconnection internally.

### Git checkpoint

```
Stage and commit: P1: add docker-compose.yml with librechat, mongodb, meilisearch
```

---

## Step 3: Fill in `.env`

Open your `.env` file. You need to generate the secret values. Open a Git Bash terminal (comes with Git for Windows) and run:

```bash
echo "CREDS_KEY=$(openssl rand -hex 16)"
echo "CREDS_IV=$(openssl rand -hex 8)"
echo "JWT_SECRET=$(openssl rand -hex 32)"
echo "JWT_REFRESH_SECRET=$(openssl rand -hex 32)"
```

Copy each generated value into your `.env` file. Also fill in:

```bash
MONGO_URI=mongodb://mongodb:27017/LibreChat
MEILI_MASTER_KEY=samwell-meili-dev-key
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

The `MEILI_MASTER_KEY` can be any string in development. The `MONGO_URI` uses the Docker service name `mongodb` because LibreChat resolves it on the Docker network.

**Do NOT commit.** The `.env` file is git-ignored. Verify: `git status` should not show `.env`.

---

## Step 4: Create `librechat.yaml`

This is the heart of Samwell's configuration. Create `librechat.yaml` in the project root.

```yaml
version: 1.2.1

cache: true

endpoints:
  custom:
    - name: "Ollama"
      apiKey: "ollama"
      baseURL: "http://host.docker.internal:11434/v1/"
      models:
        default:
          - "llama3.2:3b"
        fetch: true
      titleConvo: true
      titleModel: "current_model"
      summarize: false
      modelDisplayLabel: "Ollama"
```

### Understanding each field

- **`name: "Ollama"`** — Must start with "ollama" (case-insensitive) to enable LibreChat's built-in Ollama icon and model-fetching logic.

- **`apiKey: "ollama"`** — Required by the schema but Ollama ignores it. Any non-empty string works.

- **`baseURL`** — Points to Ollama's OpenAI-compatible endpoint. The `/v1/` suffix is required. Uses `host.docker.internal` because LibreChat runs in Docker while Ollama runs on the host.

- **`fetch: true`** — Tells LibreChat to query Ollama's API for available models. Any model you `ollama pull` automatically appears in the dropdown.

- **`titleConvo: true`** — Auto-generates conversation titles using the LLM.

- **`titleModel: "current_model"`** — Uses the already-loaded model for titles instead of loading a separate one. Critical for memory management on constrained hardware.

- **`summarize: false`** — Disables conversation summarization which uses API features Ollama doesn't fully support.

### Git checkpoint

```
Stage and commit: P1: add librechat.yaml with ollama endpoint
```

---

## Step 5: Start the stack

Make sure Ollama is running (it should be as a background service, but verify with `ollama list`).

In your terminal, from the `samwell/` directory:

```
docker compose up -d
```

Watch the logs to confirm startup:

```
docker compose logs -f api
```

Wait for LibreChat to show that it's listening on port 3080. This may take 30–60 seconds on first run as it initializes the database.

Open your browser to **http://localhost:3080**

You'll need to create an account (local-only, stored in your MongoDB). Use any email/password — this is your local instance.

---

## Step 6: Test the core loop

1. After logging in, look at the top of the chat interface — you should see a model selector
2. Select the **Ollama** endpoint
3. You should see `llama3.2:3b` in the model dropdown (and any other models you've pulled)
4. Type a message and verify you get a response
5. Check that the conversation gets a title automatically

### If it doesn't work

Common issues and what to check:

**"No models found" or empty dropdown:**
- Is Ollama running? Check: `ollama list`
- Can the container reach Ollama? Check: `docker exec samwell-librechat curl http://host.docker.internal:11434/v1/models`
- Is `fetch: true` set in librechat.yaml?

**Connection refused / timeout:**
- On some Windows setups, `host.docker.internal` doesn't resolve. Try using your machine's LAN IP instead in `baseURL`
- Check Windows Firewall isn't blocking port 11434

**Extremely slow responses:**
- Expected on i9-13900K with CPU inference for 3B model: ~15–25 tok/s
- If much slower, check Task Manager — Ollama should be using significant CPU

**Chat works but no title generated:**
- Verify `titleConvo: true` and `titleModel: "current_model"` in librechat.yaml
- Restart: `docker compose restart api`

---

## Step 7: Test model switching

Pull a second model to verify dynamic switching:

```
ollama pull qwen3:1.7b
```

After the download completes, go back to LibreChat and click the model dropdown. The new model should appear without restarting anything (thanks to `fetch: true`). Start a new conversation with the new model to verify it works.

### Understanding model loading

When you switch models in LibreChat, here's what happens under the hood:

1. LibreChat sends the API request with the model name in the payload
2. Ollama receives the request, checks if that model is loaded in RAM
3. If not loaded, Ollama unloads the current model and loads the new one (takes 5–30 seconds depending on model size)
4. Inference begins

With 64GB RAM and no GPU, Ollama will use system RAM for model weights. A 3B model at Q4 uses ~2GB, leaving plenty of room. You'll feel the constraint when trying models above ~8B.

### Git checkpoint

```
Stage and commit: P1: core loop functional — librechat + ollama verified
```

---

## Step 8 (Optional): Pull a larger model

If you want to test the boundaries of your Windows hardware:

```
ollama pull llama3.1:8b
```

This is a ~4.7GB download and the sweet spot for your i9-13900K. Expect ~10–20 tokens/second. You can also try `qwen3:8b` or `phi-4:14b` (the 14B will be noticeably slower).

Models beyond 14B will work but will be too slow for comfortable interactive use on CPU-only inference.

---

## Checkpoint ✓

At this point you should have:

- [ ] Ollama installed natively and running
- [ ] At least two models pulled and available
- [ ] LibreChat running in Docker, accessible at http://localhost:3080
- [ ] Model switching working in the LibreChat UI
- [ ] Conversation titles generating automatically
- [ ] Three git commits for this phase

**Your git log should look something like:**

```
P1: core loop functional — librechat + ollama verified
P1: add librechat.yaml with ollama endpoint
P1: add docker-compose.yml with librechat, mongodb, meilisearch
P0: scaffold project structure
```

**Next phase:** Phase 2 — First MCP Server. Return to the main Claude conversation to discuss which MCP server to add first and how the MCP transport layer works.

---

## Troubleshooting

**MongoDB fails to start:**
- Check if port 27017 is already in use: `netstat -an | findstr 27017`
- Check volume permissions: delete `volumes/mongodb/` contents and retry

**LibreChat shows "Internal Server Error":**
- Check logs: `docker compose logs api`
- Most common cause: malformed `librechat.yaml` (YAML is whitespace-sensitive)
- Validate your YAML at https://www.yamllint.com/

**`docker compose` not recognized:**
- Docker Desktop must be running
- Use `docker-compose` (with hyphen) if on an older Docker version

**Model responses are cut off mid-sentence:**
- This is the token limit issue. LibreChat may default to 4,095 tokens for unknown models.
- Add `modelSpecs` or increase `maxOutputTokens` in your endpoint config.
- Discuss this with Claude in the main conversation if you hit it.
