FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV FASTEMBED_CACHE_PATH=/cache
ENV PYTHONUNBUFFERED=1

RUN uv tool install mcp-server-qdrant

ARG HF_TOKEN=""
RUN HF_TOKEN="${HF_TOKEN}" \
    /root/.local/share/uv/tools/mcp-server-qdrant/bin/python3 -c \
    "from fastembed import TextEmbedding; \
    model = TextEmbedding('sentence-transformers/all-MiniLM-L6-v2'); \
    list(model.embed(['warmup']))"

EXPOSE 8000

ENTRYPOINT ["uv", "tool", "run", "mcp-server-qdrant", "--transport", "sse"]