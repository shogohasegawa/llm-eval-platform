# ベースイメージとしてPython 3.12を使用
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数の設定
ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Tokyo

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ca-certificates \
    tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && echo "Asia/Tokyo" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# uv のインストール
# uvのインストーラーはcurlと証明書が必要なため、上記でインストール済み
ADD https://astral.sh/uv/0.5.16/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# uvバイナリがPATHに含まれるよう環境変数を設定
ENV PATH="/root/.local/bin/:$PATH"

# 仮想環境作成・有効化
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

RUN uv python pin 3.12

# ライブラリのインストール
COPY pyproject.toml uv.lock ./
COPY README.md ./README.md
RUN uv sync --frozen

# アプリケーションのソースコードをコピー
COPY src ./src

# データセットは外部からマウントするため、コンテナにはコピーしない
# コメントアウト: COPY datasets ./datasets

# ポートの公開
EXPOSE 8000

# アプリケーションの起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
