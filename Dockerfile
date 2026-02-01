FROM python:3.12-slim

WORKDIR /app

# Install game dependencies + server dependencies
COPY requirements.txt requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-server.txt

# Copy application code
COPY game/ game/
COPY server/ server/
COPY docs/ docs/

# Expose port
EXPOSE 8080

# Run with single worker (WebSocket sessions are stateful)
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
