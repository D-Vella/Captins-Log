FROM python:3.12-slim

  WORKDIR /app

  RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
      && rm -rf /var/lib/apt/lists/*

  COPY requirements.txt .

  RUN pip install --no-cache-dir -r requirements.txt

  # Self-signed cert for local-network HTTPS. SAN covers the fixed hostname/IP of the
  # deployment target (melody / 192.168.0.119) plus localhost, so browsers don't also
  # flag a name mismatch on top of the expected self-signed warning.
  RUN openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
      -subj "/CN=melody" \
      -addext "subjectAltName=DNS:melody,DNS:melody.local,DNS:localhost,IP:192.168.0.119,IP:127.0.0.1"

  COPY . .

  EXPOSE 8501

  COPY entrypoint.sh .
  RUN chmod +x entrypoint.sh
    
  ENTRYPOINT ["./entrypoint.sh"]
  CMD ["streamlit", "run", "app.py", \
       "--server.address", "0.0.0.0", \
       "--server.sslCertFile", "cert.pem", \
       "--server.sslKeyFile", "key.pem"]