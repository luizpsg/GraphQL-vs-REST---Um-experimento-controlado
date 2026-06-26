FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# Dependencias do sistema necessarias para numpy/scipy/pandas em wheels slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

# Healthcheck nativo do Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os,sys; \
    sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8501')+'/_stcore/health').status==200 else sys.exit(1)"

# Respeita a porta injetada pelo Coolify ($PORT) com fallback para 8501
CMD ["sh", "-c", "streamlit run dashboard/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
