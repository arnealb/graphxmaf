# dockerfile voor mcp tool
FROM python:3.11-slim

WORKDIR /app

COPY requirements_mcp.txt .
RUN pip install --no-cache-dir -r requirements_mcp.txt

COPY mcp_api_tool.py .
COPY config.cfg .
COPY graph/ ./graph/
COPY auth/ ./auth/
COPY entities/ ./entities/
COPY data/ ./data/

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

CMD ["python", "mcp_api_tool.py"]