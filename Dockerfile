FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_WEB_SEARCH_MCP_TRANSPORT=http \
    AGENT_WEB_SEARCH_HTTP_HOST=0.0.0.0

WORKDIR /app

COPY . .
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.environ.get('AGENT_WEB_SEARCH_HTTP_PORT') or os.environ.get('PORT', '8000'); urllib.request.urlopen('http://127.0.0.1:' + port + '/healthz', timeout=3)"

CMD ["agent-web-search-mcp", "--transport", "http"]
