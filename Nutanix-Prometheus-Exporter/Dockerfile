# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user with UID 1000 to match Kubernetes
RUN groupadd -g 1000 exporter && useradd -r -u 1000 -g exporter exporter

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder to the correct user location
COPY --from=builder /root/.local /home/exporter/.local

# Copy application code
COPY nutanix_exporter.py .
COPY nutanix_client.py .
COPY collectors.py .

# Make sure scripts are executable
RUN chmod +x nutanix_exporter.py

# Change ownership to non-root user (UID 1000)
RUN chown -R 1000:1000 /app
RUN chown -R 1000:1000 /home/exporter/.local

# Switch to non-root user (UID 1000)
USER 1000:1000

# Set PATH to include local packages
ENV PATH="/home/exporter/.local/bin:$PATH"

# Expose metrics port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/metrics', timeout=5)" || exit 1

# Set default environment variables
ENV METRICS_PORT=8080
ENV COLLECTION_INTERVAL=60
ENV LOG_LEVEL=INFO
ENV TLS_VERIFY=true

# Run the exporter
CMD ["python", "nutanix_exporter.py"]
