# Samwell

A self-hosted AI stack named for Sam Weller, the resourceful servant from Dickens' **Pickwick Papers**.

## Components

- **LibreChat** - Chat interface and agent orchestrator
- **Ollama** - Local model inference
- **MCP Servers** - Containerized tool capabilities
- **Docker Compose** - Container orchestration

## Deployment

### macOS
1. Install OrbStack
`brew install orbstack`
2. Install Ollama natively
`brew install ollama`
3. Clone repo
`git clone https://github.com/claudeconnection-del/Samwell.git`
`cd Samwell`
`cp .env.example .env`
4. Fill in .env with keys
5. in /Samwell/librechat.yaml - uncomment the macOS specific version and comment out the Windows/WSL version
6. Pull models in Ollama
`ollama pull qwen3:8b`
`ollama pull qwen3:32b-q4_K_M`
`ollama pull nomic-embed-text`
`ollama pull qwen3:70b-q4_K_M` for use on more powerful hardware
7. Start the stack
`docker compose up -d`


## Status

Phase 0: Scaffold - ✅ DONE
Phase 1: Core Loop - ✅ COMPLETE
Phase 2: Expansion - 🚀 In progress (adding AI capabilities and integration points)

"*A resourceful servant doesn't rest on past achievements - they build toward the next task*" - Charles Dickens