# FitOS — Offline AI Fitness OS
# Multi-stage Docker build for portable offline deployment
# No external API dependencies — runs entirely offline

# ---- Stage 1: Builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/dev/null').execute('SELECT 1')" || exit 1

# Run database migrations and launch Streamlit
CMD ["sh", "-c", "python -c 'from app.database.migrations import migration_runner; migration_runner.run_all()' && streamlit run app/ui/app.py --server.port=8501 --server.address=0.0.0.0"]
