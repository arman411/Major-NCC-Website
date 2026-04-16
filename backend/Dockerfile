FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for Pillow and ReportLab
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Create necessary directories
RUN mkdir -p uploads certificates instance backups

EXPOSE 5000

# Use Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
