# Build stage
FROM python:3.10-slim as builder

WORKDIR /app

# Cài đặt các dependencies cần thiết cho build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để tận dụng cache
COPY requirements.txt .

# Tạo virtual environment và cài đặt dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.10-slim

WORKDIR /app

# Copy virtual environment từ builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code và .env
COPY .env .
COPY . .

# Cấu hình Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8080


CMD ["python", "app.py"]
