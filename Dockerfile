FROM python:3.11-slim

# FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Streamlit servirá en el puerto que define Render
CMD ["sh", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]
