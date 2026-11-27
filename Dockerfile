FROM python:3.11-slim

# Install system runtime dependencies (FFmpeg for video cutting & subtitle burning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-color-emoji \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Montserrat fonts for ASS subtitle rendering (falls back gracefully if offline)
RUN mkdir -p /usr/local/share/fonts/montserrat && \
    curl -fsSL -o /usr/local/share/fonts/montserrat/Montserrat-Bold.ttf \
      "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf" || true && \
    curl -fsSL -o /usr/local/share/fonts/montserrat/Montserrat-ExtraBold.ttf \
      "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf" || true && \
    fc-cache -f

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TEMP_DIR=/tmp/clipforge \
    PORT=8000

RUN mkdir -p /tmp/clipforge

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
