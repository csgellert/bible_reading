# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Run with gunicorn (production-ready WSGI server)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "app:create_app()"
