FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off

# Install system dependencies for ChromaDB and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 newsuser && \
    chown -R newsuser:newsuser /app
USER newsuser

# Use environment variables for volumes
VOLUME /app/$OUTPUT_DIR /app/$ANALYSIS_DIR /app/$VECTOR_DB_DIR

ENTRYPOINT ["python"]
CMD ["news_fetcher.py"]
