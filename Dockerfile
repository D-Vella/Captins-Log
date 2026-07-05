FROM python:3.12-slim

  WORKDIR /app

  COPY requirements.txt .

  # Added to install torch CPU version from PyTorch's official index URL to avoid compatibility issues with the slim image. Additionally, the deployment is expected to use CPU resources only.
  RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

  RUN pip install --no-cache-dir -r requirements.txt

  COPY . .

  EXPOSE 8501

  CMD ["streamlit", "run", "app.py", \
       "--server.address", "0.0.0.0", \
       "--server.sslCertFile", "cert.pem", \
       "--server.sslKeyFile", "key.pem"]