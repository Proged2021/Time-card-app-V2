# Dockerfile

FROM python:3.11-slim

# PostgreSQL接続に必要なシステム依存関係を先にインストール
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ファイルをコピーする前に、依存関係のインストールを先に実行
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# その他のソースコードをコピー
COPY . .

CMD ["python", "run.py"]
