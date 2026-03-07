# Phase 0 — Project Scaffold

> **What this phase does:** Creates the Samwell project directory with proper structure, git version control, and all the config file skeletons you'll fill in during later phases.
>
> **Time estimate:** 15–20 minutes
>
> **Prerequisites:** Git and VS Code installed on Windows 11. Docker Desktop installed but not needed yet.

---

## Context for the AI assistant

You are helping the user set up the initial project scaffold for **Samwell**, a self-hosted AI stack using LibreChat, Ollama, and containerized MCP servers orchestrated by Docker Compose. The user is an intermediate Docker user learning this stack. They are typing everything themselves in VS Code to build understanding — do NOT give them large blocks to copy-paste. Walk them through each file's purpose and let them type it. They use VS Code's built-in git (Source Control sidebar, Ctrl+Shift+G).

---

## Step 1: Create the project directory

Open a terminal in VS Code (Ctrl+`). Navigate to where you keep projects and create the root:

```
mkdir samwell
cd samwell
```

## Step 2: Initialize git

```
git init
```

This creates the `.git` directory. You now have local version control. Confirm it worked:

```
git status
```

You should see "On branch main" (or "master" — either is fine, but if it says master and you want main):

```
git branch -m main
```

## Step 3: Create the directory structure

Create all the directories Samwell will need. Type these one at a time:

```
mkdir docs
mkdir docs\phases
mkdir config
mkdir config\guardrails
mkdir config\mcp
mkdir scripts
mkdir volumes
mkdir volumes\mongodb
mkdir volumes\meilisearch
mkdir volumes\qdrant
mkdir volumes\shared-data
```

## Step 4: Create `.gitignore`

Open VS Code's explorer (Ctrl+Shift+E) and create a new file in the project root called `.gitignore`. Type the following contents — each line tells git to ignore files matching that pattern:

```gitignore
# Environment secrets — never commit these
.env
docker-compose.override.yml

# Docker volume data — large and machine-specific
volumes/mongodb/
volumes/meilisearch/
volumes/qdrant/

# Ollama models are huge — don't track them
*.gguf

# OS junk
Thumbs.db
.DS_Store

# Editor state
.vscode/
*.swp
*.swo

# Node modules if any MCP servers need them locally
node_modules/

# Python virtual environments
__pycache__/
*.pyc
.venv/
```

**Why these entries matter:**
- `.env` will hold API keys and secrets — must never be committed
- `docker-compose.override.yml` is for per-machine customizations
- Volume directories contain database files that are large and machine-specific
- The `*.gguf` pattern prevents accidentally committing multi-gigabyte model files

## Step 5: Create `.env.example`

This is the **template** that shows what environment variables are needed without containing real values. Create `.env.example` in the project root:

```bash
# Samwell Environment Configuration
# Copy this to .env and fill in real values:  cp .env.example .env

# === LibreChat ===
CREDS_KEY=             # 32-char random hex: use `openssl rand -hex 16`
CREDS_IV=              # 16-char random hex: use `openssl rand -hex 8`
JWT_SECRET=            # Any long random string: use `openssl rand -hex 32`
JWT_REFRESH_SECRET=    # Any long random string: use `openssl rand -hex 32`

# === MongoDB ===
MONGO_URI=mongodb://mongodb:27017/LibreChat

# === MeiliSearch ===
MEILI_MASTER_KEY=      # Any random string for search index auth

# === Ollama ===
OLLAMA_BASE_URL=http://host.docker.internal:11434

# === MCP Server API Keys (add as needed per phase) ===
# BRAVE_API_KEY=
# GITHUB_TOKEN=
```

## Step 6: Create the actual `.env` from the template

```
copy .env.example .env
```

You'll fill this in during Phase 1. For now it exists so the structure is complete.

## Step 7: Create `README.md`

Create `README.md` in the project root. Write a brief description — this is your project, make it yours. At minimum it should contain:

```markdown
# Samwell

A self-hosted AI stack — named for Sam Weller, the resourceful servant from Dickens' *Pickwick Papers* who translates grand intentions into practical action.

## Components

- **LibreChat** — Chat interface and agent orchestrator
- **Ollama** — Local model inference (1B–70B parameters)
- **MCP Servers** — Containerized tool capabilities (search, code exec, databases, APIs)
- **Docker Compose** — Container orchestration

## Setup

See `docs/MASTER-PLAN.md` for the full build-out plan.

## Status

Phase 0: Scaffold ✓
```

## Step 8: Create placeholder files for docs

Create `docs/MASTER-PLAN.md` — either copy the master plan document into this location, or for now just create a placeholder:

```markdown
# Samwell — Master Plan

(Full plan document goes here. See the Claude conversation for the current version.)
```

Create `docs/ARCHITECTURE.md`:

```markdown
# Samwell — Architecture

(Diagrams and design decision records will go here as the project takes shape.)
```

## Step 9: Add empty `.gitkeep` files

Git doesn't track empty directories. Add placeholder files to keep the structure in version control:

```
echo. > config\guardrails\.gitkeep
echo. > config\mcp\.gitkeep
echo. > scripts\.gitkeep
echo. > volumes\shared-data\.gitkeep
```

Note: The other `volumes/` subdirectories are git-ignored so they don't need `.gitkeep` files.

## Step 10: First commit

Open the Source Control panel in VS Code (Ctrl+Shift+G). You should see all your new files listed under "Changes."

1. Click the **+** icon next to "Changes" to stage all files
2. Type the commit message: `P0: scaffold project structure`
3. Click the checkmark (✓) or press Ctrl+Enter to commit

Verify the commit:

```
git log --oneline
```

You should see one commit with your message.

---

## Checkpoint ✓

At this point you should have:

- [ ] A `samwell/` directory with the full folder structure
- [ ] Git initialized with one commit
- [ ] `.gitignore` protecting secrets and large files
- [ ] `.env.example` documenting required variables
- [ ] `.env` created (empty values, git-ignored)
- [ ] `README.md` with project description
- [ ] Doc placeholders in `docs/`

**Next phase:** Phase 1 — Core Loop (LibreChat + Ollama). Return to the main Claude conversation to begin.

---

## Troubleshooting

**"git is not recognized"** — Git isn't in your PATH. Install Git for Windows from https://git-scm.com and restart VS Code.

**VS Code Source Control shows nothing** — Make sure you opened the `samwell` folder in VS Code (File → Open Folder), not a parent directory.

**`.env` shows up in git status** — Check that `.gitignore` has `.env` on its own line (no leading spaces, no trailing characters). Run `git rm --cached .env` if it was already tracked.

**`mkdir` errors on Windows** — If using PowerShell, the syntax is the same. If using cmd.exe, the syntax above works. If using Git Bash, use forward slashes: `mkdir -p docs/phases`.
