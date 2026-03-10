FROM python:3.11-slim

LABEL org.opencontainers.image.title="FlinkSQL Studio Kubernetes Operator"
LABEL org.opencontainers.image.authors="Nestor A. A <nestorabiawuh@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/coded-streams/flinksql-kube-operator"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy operator source
COPY api/ api/
COPY controllers/ controllers/

# Run as non-root
RUN useradd -u 65534 -r -M -g operator operator 2>/dev/null || true
USER 65534

ENTRYPOINT ["kopf", "run", "/app/controllers/flinksqlstudio_controller.py", "--all-namespaces"]