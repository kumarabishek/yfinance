FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv --no-cache-dir

# Copy server
COPY server.py .

# Create venv and install dependencies directly
RUN uv venv .venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install --no-cache \
    "mcp[cli]>=1.9.0" \
    "yfinance>=0.2.54" \
    "pandas>=2.0.0" \
    "uvicorn[standard]>=0.30.0" \
    "scikit-learn>=1.4.0" \
    "ta>=0.11.0" \
    "edgartools>=3.0.0"

# Default port (can be overridden by cloud platform)
ENV PORT=8000
EXPOSE 8000

CMD [".venv/bin/python", "server.py"]
