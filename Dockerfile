FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY server.py .

# Install dependencies
RUN uv sync --no-install-project

# Default port (can be overridden by cloud platform)
ENV PORT=8000
EXPOSE 8000

CMD ["uv", "run", "server.py"]
