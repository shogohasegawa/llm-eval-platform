import os
import logging
import time
import datetime
import json
import re
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, Response
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse

from app.api import api_router
from app.utils.db import get_db
from app.utils.app_logging import setup_logging

# タイムゾーンをJST（日本標準時）に設定
os.environ['TZ'] = 'Asia/Tokyo'
time.tzset()  # システムのタイムゾーン設定を反映

# デフォルトのタイムゾーンを設定
DEFAULT_TIMEZONE = ZoneInfo('Asia/Tokyo')

# ロギングの設定
log_level = os.environ.get("LLMEVAL_LOG_LEVEL", "INFO")
setup_logging(log_level=log_level)
logger = logging.getLogger("llmeval")

app = FastAPI(title="LLM Evaluation API")

# CORS設定（React Appとの連携用）
# 環境変数から許可するオリジンを読み込む
cors_origins = os.environ.get("CORS_ORIGINS", "*")
if cors_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in cors_origins.split(",")]

logger.info(f"CORS設定: 許可オリジン = {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400  # 24時間キャッシュ
)

# データベース接続の初期化
db = get_db()

# プロキシルーターを追加
from app.api.endpoints import proxy

# JSONLデータセット推論APIルーターをインポート
from app.api.endpoints import jsonl_inference
from app.api.endpoints import jsonl_inference_ui

# APIルーターを追加（バージョン付きのRESTful API標準形式）
app.include_router(api_router, prefix="/api/v1")

# JSONLデータセット推論APIルーターを追加
app.include_router(jsonl_inference.router, prefix="/api/v1")

# JSONLデータセット推論UIを追加
app.include_router(jsonl_inference_ui.router, prefix="/api/v1")

# リクエスト・レスポンスのロギング
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"リクエスト受信: {request.method} {request.url}")
    
    # OPTIONSリクエストの場合は即座に応答
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",  # 24時間キャッシュ
        }
        return Response(status_code=200, headers=headers)
    
    try:
        response = await call_next(request)
        
        # レスポンスにCORSヘッダーを追加
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        logger.debug(f"レスポンス送信: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"リクエスト処理エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# エラーハンドリング
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    logger.error(f"バリデーションエラー: {exc.detail}")
    return JSONResponse(
        status_code=422,
        content={"detail": "リクエストのバリデーションに失敗しました。", "errors": exc.detail}
    )

# アプリ起動イベント
@app.on_event("startup")
async def startup_event():
    # アプリケーション起動時に実行する処理
    logger.info("アプリケーション起動中...")
    
    # タイムゾーン設定の確認と表示
    current_time = datetime.datetime.now()
    current_time_utc = datetime.datetime.now(datetime.timezone.utc)
    current_time_jst = datetime.datetime.now(ZoneInfo('Asia/Tokyo'))
    
    logger.info(f"システム時間: {current_time}")
    logger.info(f"UTC時間: {current_time_utc}")
    logger.info(f"JST時間: {current_time_jst}")
    logger.info(f"現在のタイムゾーン設定: {time.tzname}")
    
    # LLM 設定に関する情報を表示
    logger.info("=== LLM 設定ポリシー ===")
    logger.info("環境変数からの設定読み込みは無効化されています")
    logger.info("APIキーとエンドポイントはプロバイダ設定またはモデル設定から取得されます")
    logger.info("設定の優先順位: 1. モデル設定, 2. プロバイダ設定")
    logger.info("===============================")
    
    # LiteLLMキャッシュとルーターの初期化
    from app.utils.litellm_helper import init_litellm_cache, init_router_from_db
    
    # キャッシュ初期化
    init_litellm_cache()
    
    # ルーター初期化
    logger.info("LiteLLM Routerを初期化中...")
    init_router_from_db()
    logger.info("LiteLLM Router初期化完了")
    
    logger.info("アプリケーション起動完了")

# アプリ終了イベント    
@app.on_event("shutdown")
async def shutdown_event():
    # アプリケーション終了時に実行する処理
    logger.info("アプリケーション終了中...")
    
    # データベース接続のクローズなど
    db.close()
    
    logger.info("アプリケーション終了完了")

# ルートエンドポイント
@app.get("/")
async def root():
    logger.debug("ルートエンドポイントへのアクセス")
    return {"message": "LLM Evaluation Platform API"}

@app.get("/debug-mlflow", response_class=HTMLResponse)
async def debug_mlflow():
    """
    MLflowデバッグ用のHTMLページを返す
    """
    logger.info("MLflowデバッグページへのアクセス")
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLflow Debug Page</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body, html {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #4CAF50;
            }
            .server-group {
                margin-bottom: 20px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                text-decoration: none;
                display: inline-block;
                margin: 10px 5px;
                cursor: pointer;
                border-radius: 4px;
            }
            .status {
                margin-top: 10px;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
            iframe {
                width: 100%;
                height: 500px;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MLflow デバッグページ</h1>
            
            <div class="server-group">
                <h2>MLflow 直接アクセス</h2>
                <p>MLflowサーバーに直接アクセスします (ポート5000)</p>
                <a href="http://localhost:5000" target="_blank" class="button">Open MLflow (Direct)</a>
                <div class="status" id="direct-status">Checking...</div>
            </div>
            
            <div class="server-group">
                <h2>MLflow プロキシアクセス</h2>
                <p>APIサーバー経由でMLflowにアクセスします (ポート8001)</p>
                <a href="/proxy-mlflow/" target="_blank" class="button">Open MLflow (Proxy)</a>
                <div class="status" id="proxy-status">Checking...</div>
            </div>
            
            <div class="server-group">
                <h2>MLflow UI (iframe)</h2>
                <iframe src="/proxy-mlflow/" id="mlflow-frame"></iframe>
            </div>
            
            <div class="server-group">
                <h2>API テスト</h2>
                <a href="/api/v1/evaluations/metrics" target="_blank" class="button">Get Metrics</a>
                <div class="status" id="api-status">API status...</div>
            </div>
        </div>
        
        <script>
            // サーバー状態をチェック
            async function checkServer(url, statusId) {
                try {
                    const startTime = new Date().getTime();
                    const response = await fetch(url);
                    const endTime = new Date().getTime();
                    const duration = endTime - startTime;
                    
                    document.getElementById(statusId).innerHTML = 
                        `Status: ${response.status} ${response.statusText}<br>` +
                        `Response time: ${duration}ms<br>` +
                        `Content-Type: ${response.headers.get('content-type')}`;
                    
                    if (response.headers.get('content-type')?.includes('json')) {
                        const data = await response.json();
                        document.getElementById(statusId).innerHTML += 
                            `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    }
                } catch (e) {
                    document.getElementById(statusId).innerHTML = 
                        `Error: ${e.message}`;
                }
            }
            
            // 初期化
            window.onload = function() {
                // サーバー状態をチェック
                checkServer('http://localhost:5000', 'direct-status');
                checkServer('/proxy-mlflow/', 'proxy-status');
                checkServer('/api/v1/evaluations/metrics', 'api-status');
            };
        </script>
    </body>
    </html>
    """
    return html_content

# MLflow UI をiframeで表示するページ
# MLflowページの任意のパスへのアクセスをサポートするためのリダイレクトハンドラー
@app.get("/mlflow/{path:path}")
async def mlflow_redirect(path: str):
    return RedirectResponse(url=f"/proxy-mlflow/{path}")

# 404エラーを返すグラフQLエンドポイント（クライアントが何度もリトライしないように）
@app.get("/graphql")
@app.post("/graphql")
@app.options("/graphql")
async def graphql_404(request: Request):
    """
    GraphQLエンドポイント - 404エラーを返します。
    フロントエンドからのリクエストが存在しないエンドポイントにループしないようにするため。
    """
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    
    # OPTIONSリクエストの場合は200を返す（CORS対応）
    if request.method == "OPTIONS":
        return Response(content=b"", status_code=200, headers=headers)
    
    # それ以外は404エラーを返す
    return JSONResponse(
        content={"detail": "GraphQL endpoint not supported"},
        status_code=404,
        headers=headers
    )

# MLflowのGraphQLエンドポイントは不要なため一時的に無効化
# GraphQLエンドポイントの問題が解決されるまでコメントアウト
"""
# 現在は使用していないMLflow GraphQLエンドポイント
# 必要になった場合は再度有効化する
# @app.get("/proxy-mlflow/graphql")
# @app.post("/proxy-mlflow/graphql") 
# @app.options("/proxy-mlflow/graphql")
async def graphql_proxy(request: Request):
    # MLflowサービスへの内部URL（Docker Composeネットワーク内）
    mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
    mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
    target_url = f"http://{mlflow_host}:{mlflow_port}/graphql"
    logger.debug(f"GraphQL proxy request: {request.method} {target_url}")
    
    # OPTIONSリクエストの場合は直接レスポンスを返す
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        return Response(
            content=b"",
            status_code=200,
            headers=headers
        )
    
    # 省略
"""

@app.get("/mlflow-ui", response_class=HTMLResponse)
async def mlflow_ui():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLflow UI - LLM Evaluation Platform</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                overflow: hidden;
                font-family: Arial, sans-serif;
            }
            .container {
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            .header {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                z-index: 10;
            }
            .header h1 {
                margin: 0;
                font-size: 20px;
            }
            iframe {
                flex-grow: 1;
                border: none;
                width: 100%;
                height: calc(100% - 60px);
            }
            .loader {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: calc(100% - 60px);
                background-color: #f5f5f5;
            }
            .spinner {
                border: 4px solid rgba(0, 0, 0, 0.1);
                width: 36px;
                height: 36px;
                border-radius: 50%;
                border-left-color: #4CAF50;
                animation: spin 1s linear infinite;
                margin-bottom: 16px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .fallback {
                padding: 40px 20px;
                text-align: center;
                background-color: #f9f9f9;
                border-radius: 8px;
                margin: 40px auto;
                max-width: 600px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                display: none;
            }
            .button {
                background-color: white;
                color: #4CAF50;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
                text-decoration: none;
                display: inline-block;
                transition: all 0.2s ease;
            }
            .button:hover {
                background-color: #f0f0f0;
                transform: translateY(-2px);
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .direct-link {
                margin-top: 16px;
                display: inline-block;
                color: #666;
                text-decoration: underline;
            }
            .error-message {
                color: #d32f2f;
                margin-bottom: 24px;
                font-weight: bold;
            }
            .note {
                font-size: 14px;
                color: #666;
                margin-top: 16px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>MLflow メトリクスダッシュボード</h1>
                <a href="/" class="button">メインに戻る</a>
            </div>
            
            <!-- ローディング表示 -->
            <div id="loader" class="loader">
                <div class="spinner"></div>
                <p>MLflow UIを読み込み中...</p>
            </div>
            
            <!-- iframeでMLflowを表示 -->
            <iframe 
                src="/proxy-mlflow/" 
                id="mlflow-frame"
                style="display: none;"
                onload="frameLoaded()"
                onerror="frameError()">
            </iframe>
            
            <!-- フォールバック表示 -->
            <div class="fallback" id="fallback">
                <h2>MLflow UIの読み込みに失敗しました</h2>
                <p class="error-message" id="error-message">403 Forbidden エラーが発生しました</p>
                <p>以下のいずれかの方法でMLflowにアクセスしてください:</p>
                <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 20px;">
                    <a href="/proxy-mlflow/" target="_blank" class="button">1. MLflow UIをプロキシ経由で開く</a>
                    <a href="/proxy-mlflow/" target="_self" class="button">2. このページを再読み込み</a>
                </div>
                
                <div id="debug-info" style="text-align: left; margin-top: 30px; background: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <h3>トラブルシューティング情報</h3>
                    <p>以下の情報を確認してください:</p>
                    <ul style="margin-bottom: 15px;">
                        <li>MLflowサーバーのステータス: <span id="mlflow-status">確認中...</span></li>
                        <li>プロキシ接続のステータス: <span id="proxy-status">確認中...</span></li>
                        <li>ブラウザ情報: <span id="browser-info">取得中...</span></li>
                    </ul>
                    
                    <button onclick="checkConnections()" style="background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                        接続を再確認
                    </button>
                </div>
                
                <p class="note">※ MLflowサーバーが起動していることを確認してください。<br>ブラウザのCORS制限により、iframeでのアクセスがブロックされている可能性があります。</p>
                
                <script>
                    // 接続テスト用関数
                    async function checkConnections() {
                        document.getElementById('mlflow-status').textContent = "確認中...";
                        document.getElementById('proxy-status').textContent = "確認中...";
                        
                        // MLflowサーバーへのプロキシアクセスをテスト
                        try {
                            const directResp = await fetch('/proxy-mlflow/', {
                                method: 'GET'
                            });
                            document.getElementById('mlflow-status').textContent = "接続OK (ステータス: " + directResp.status + ")";
                        } catch (e) {
                            document.getElementById('mlflow-status').textContent = "接続エラー: " + e.message;
                        }
                        
                        // プロキシアクセスをテスト（ajax-apiエンドポイントを使用）
                        try {
                            const proxyResp = await fetch('/proxy-mlflow/ajax-api/2.0/mlflow/experiments/search?max_results=100', {
                                method: 'GET'
                            });
                            document.getElementById('proxy-status').textContent = 
                                "接続OK (ステータス: " + proxyResp.status + ")";
                        } catch (e) {
                            document.getElementById('proxy-status').textContent = "接続エラー: " + e.message;
                        }
                        
                        // ブラウザ情報を表示
                        document.getElementById('browser-info').textContent = 
                            navigator.userAgent;
                    }
                    
                    // ページ読み込み時に接続テスト実行
                    checkConnections();
                </script>
            </div>
        </div>
        <script>
            let loadTimerId = null;
            
            function frameLoaded() {
                console.log('MLflow frame loaded successfully');
                // ローディング表示を非表示にする
                document.getElementById('loader').style.display = 'none';
                
                // Check if we can access the iframe content
                try {
                    const frame = document.getElementById('mlflow-frame');
                    frame.style.display = 'block';
                    
                    // Try to access iframe content - will throw if cross-origin issues
                    const frameContent = frame.contentWindow.document;
                    
                    // Check if there's an error message in the iframe content
                    const frameBody = frameContent.body.innerText;
                    if (frameBody.includes('403 Forbidden') || 
                        frameBody.includes('Access Denied') ||
                        frameBody.includes('Error')) {
                        throw new Error('エラーページが表示されています: ' + 
                            frameBody.substring(0, 100) + '...');
                    }
                    
                    // If we reach here, the iframe loaded successfully
                    if (loadTimerId) {
                        clearTimeout(loadTimerId);
                        loadTimerId = null;
                    }
                    
                    console.log('MLflow UI successfully loaded in iframe');
                } catch (e) {
                    console.error('MLflow access error after load:', e);
                    document.getElementById('error-message').textContent = 
                        e.message || 'アクセス拒否または接続エラー';
                    showFallback();
                }
            }
            
            function frameError() {
                console.error('MLflow frame failed to load (onerror event)');
                document.getElementById('error-message').textContent = 
                    'iframeの読み込みエラー - リソースが見つからないか、アクセスが拒否されました';
                showFallback();
            }
            
            function showFallback() {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('mlflow-frame').style.display = 'none';
                document.getElementById('fallback').style.display = 'block';
                
                // タイマーがセットされていたらクリア
                if (loadTimerId) {
                    clearTimeout(loadTimerId);
                    loadTimerId = null;
                }
                
                // 自動的に接続テストを実行
                if (typeof checkConnections === 'function') {
                    checkConnections();
                }
            }
            
            // iframeの読み込みが完了したかどうかをチェックするタイマー
            loadTimerId = setTimeout(() => {
                try {
                    // Try to access the iframe content
                    const frame = document.getElementById('mlflow-frame');
                    if (frame.style.display === 'none') {
                        // If the iframe is still hidden, the load event hasn't fired
                        document.getElementById('error-message').textContent = 
                            'タイムアウト: MLflow UIの読み込みに時間がかかっています';
                        showFallback();
                    }
                } catch (e) {
                    console.error('MLflow timeout check error:', e);
                    showFallback();
                }
            }, 10000);
            
            // 直接アクセスするためのURLをホスト名に基づいて設定
            window.addEventListener('DOMContentLoaded', () => {
                // プロキシリンクで置き換える (直接アクセスは403エラーになるため)
                const directLinks = document.querySelectorAll('a[href^="http://"]');
                
                directLinks.forEach(link => {
                    if (link.href.includes(':5000')) {
                        link.href = `/proxy-mlflow`;
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    return html_content

# MLflow UIへのプロキシエンドポイント
@app.get("/proxy-mlflow/{path:path}")
@app.post("/proxy-mlflow/{path:path}")
@app.put("/proxy-mlflow/{path:path}")
@app.delete("/proxy-mlflow/{path:path}")
@app.patch("/proxy-mlflow/{path:path}")
@app.options("/proxy-mlflow/{path:path}")
async def proxy_mlflow(path: str, request: Request):
    # MLflowサービスへの内部URL（Docker Composeネットワーク内）
    # ホスト名を環境変数から取得（デフォルトはmlflow）
    mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
    mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
    
    # 接続試行対象URLリスト - 優先順位順
    connection_attempts = [
        # 1. 環境変数で指定されたホスト（デフォルト：mlflow:5000）
        f"http://{mlflow_host}:{mlflow_port}/{path}",
        # 2. ローカルホスト（同一コンテナ内からの接続用）
        f"http://localhost:{mlflow_port}/{path}",
        # 3. Docker内部ネットワークの一般的なアドレス
        f"http://host.docker.internal:{mlflow_port}/{path}",
        # 4. Docker Bridgeネットワークのデフォルトゲートウェイ
        f"http://172.17.0.1:{mlflow_port}/{path}"
    ]
    
    # 最初の接続試行先URLをログ
    target_url = connection_attempts[0]
    logger.debug(f"MLflow primary target URL: {target_url}")
    
    # フォールバック情報を記録
    fallback_urls = connection_attempts[1:]
    logger.debug(f"MLflow fallback URLs: {fallback_urls}")
    
    # クエリパラメータをURLリストに適用
    query_string = ""
    if request.query_params:
        query_string = "?" + str(request.query_params)
    
    # 正規化されたURLリストを作成（クエリパラメータを含む）
    attempt_urls = [url + query_string for url in connection_attempts]
    primary_url = attempt_urls[0]
    
    logger.debug(f"MLflowへのプロキシリクエスト: {request.method} {primary_url}")
    
    try:
        # リクエストヘッダーをコピー（一部のヘッダーは除外）
        headers = {}
        for name, value in request.headers.items():
            if name.lower() not in ("host", "content-length"):
                headers[name] = value
        
        # CORSヘッダーを追加
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        # OPTIONSリクエストの場合は直接レスポンスを返す
        if request.method == "OPTIONS":
            return Response(
                content=b"",
                status_code=200,
                headers=headers
            )
        
        # リクエストボディを取得
        body = await request.body() if request.method != "GET" else None
        
        # 接続エラーを蓄積
        errors = []
        response = None
        
        # 複数URLを試行するフォールバックメカニズム
        for url_index, current_url in enumerate(attempt_urls):
            try:
                # リクエストメソッドに応じたHTTPリクエストを送信
                async with httpx.AsyncClient(timeout=15.0) as client:  # タイムアウトを適切に設定
                    if request.method == "GET":
                        response = await client.get(current_url, headers=headers, follow_redirects=True)
                    elif request.method == "POST":
                        response = await client.post(current_url, headers=headers, content=body, follow_redirects=True)
                    elif request.method == "PUT":
                        response = await client.put(current_url, headers=headers, content=body, follow_redirects=True)
                    elif request.method == "DELETE":
                        response = await client.delete(current_url, headers=headers, follow_redirects=True)
                    elif request.method == "PATCH":
                        response = await client.patch(current_url, headers=headers, content=body, follow_redirects=True)
                    else:
                        return JSONResponse(
                            status_code=405,
                            content={"detail": f"Method {request.method} not allowed"}
                        )
                
                # 成功した場合、使用したURLをログに記録して処理を続行
                if url_index > 0:
                    logger.info(f"MLflow接続: フォールバックURL({url_index})を使用しました: {current_url}")
                
                # レスポンスヘッダーから不要なものを除外
                headers_to_forward = dict(response.headers)
                headers_to_remove = ["content-encoding", "content-length", "transfer-encoding", "connection"]
                for header in headers_to_remove:
                    if header in headers_to_forward:
                        del headers_to_forward[header]
                
                # CORSヘッダーを追加
                headers_to_forward["Access-Control-Allow-Origin"] = "*"
                headers_to_forward["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                headers_to_forward["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                
                # 接続が成功したので、レスポンス処理に進む
                break
                
            except Exception as e:
                # 失敗した場合はエラーを記録して次のURLを試す
                error_msg = f"URL{url_index} '{current_url}': {str(e)}"
                errors.append(error_msg)
                logger.warning(f"MLflow接続エラー: {error_msg}")
                
                # 最後のURLまで試したが全て失敗した場合
                if url_index == len(attempt_urls) - 1:
                    raise Exception(f"全ての接続先で接続失敗: {', '.join(errors)}")
                
                # 次のURLを試す
                continue
        
        # 全ての接続試行が終了後、レスポンスがない場合はエラーを返す
        if response is None:
            return JSONResponse(
                status_code=500,
                content={"detail": "MLflowサーバーへの接続に失敗しました。レスポンスが取得できませんでした。"}
            )
            
        # コンテンツタイプのチェック
        content_type = response.headers.get("content-type", "")
        content = response.content
        
        # HTMLの場合、相対パスを絶対パスに変換する
        if content_type.startswith("text/html"):
            content_text = content.decode("utf-8")
            
            # 相対パスを '/proxy-mlflow/' で始まる絶対パスに変換
            content_text = content_text.replace('href="./static-files/', 'href="/proxy-mlflow/static-files/')
            content_text = content_text.replace('src="static-files/', 'src="/proxy-mlflow/static-files/')
            content_text = content_text.replace('src="./static-files/', 'src="/proxy-mlflow/static-files/')
            content_text = content_text.replace('href="static-files/', 'href="/proxy-mlflow/static-files/')
            content_text = content_text.replace('href="api/', 'href="/proxy-mlflow/api/')
            content_text = content_text.replace('href="#/', 'href="/proxy-mlflow#/')
            
            # 絶対パスのMLflowへの参照をプロキシに変換
            content_text = content_text.replace('http://localhost:5000', '/proxy-mlflow')
            content_text = content_text.replace('"http://mlflow:5000', '"/proxy-mlflow')
            content_text = content_text.replace("'http://mlflow:5000", "'/proxy-mlflow")
            
            # 環境変数で設定されたMLflowホスト名も置換
            mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
            mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
            if mlflow_host != "mlflow" or mlflow_port != "5000":
                content_text = content_text.replace(f'http://{mlflow_host}:{mlflow_port}', '/proxy-mlflow')
                content_text = content_text.replace(f'"http://{mlflow_host}:{mlflow_port}', '"/proxy-mlflow')
                content_text = content_text.replace(f"'http://{mlflow_host}:{mlflow_port}", "'/proxy-mlflow")
            
            # IPアドレスベースのURLも置換
            content_text = content_text.replace('http://0.0.0.0:5000', '/proxy-mlflow')
            
            # 異なるネットワーク間でのアクセス用に、様々なIPアドレスパターンを書き換え
            import re
            # 任意のIPアドレスとポート5000のパターンを検出して置換
            ip_pattern = r'(https?://)((?:\d{1,3}\.){3}\d{1,3}):5000'
            content_text = re.sub(ip_pattern, r'\1\2:8001/proxy-mlflow', content_text)
            
            # artifact_uri内のファイルパス参照を修正（クロスネットワークアクセス時の問題修正）
            if '"artifact_uri"' in content_text or "'artifact_uri'" in content_text:
                # JSON内でartifact_uriフィールドのパスを検出して置換
                artifact_pattern = r'(["\'])artifact_uri[\'"]\s*:\s*["\']file:///mlflow/artifacts/([^"\']*)[\'"]\s*([,}])'
                content_text = re.sub(artifact_pattern, r'\1artifact_uri\1: \1/proxy-mlflow/get-artifact?path=\2\1\3', content_text)
            
            content = content_text.encode("utf-8")
        
        # CSSの場合も、相対パスを絶対パスに変換
        elif content_type.startswith("text/css"):
            try:
                content_text = content.decode("utf-8")
                content_text = content_text.replace('url(../', 'url(/proxy-mlflow/static-files/')
                content_text = content_text.replace('url("../', 'url("/proxy-mlflow/static-files/')
                content_text = content_text.replace("url('../", "url('/proxy-mlflow/static-files/")
                content = content_text.encode("utf-8")
            except:
                # デコードに失敗した場合は元のコンテンツを使用
                pass
        
        # JavaScriptの場合も、URLを書き換え
        elif content_type.startswith("application/javascript") or content_type.startswith("text/javascript"):
            try:
                content_text = content.decode("utf-8")
                content_text = content_text.replace('http://localhost:5000', '/proxy-mlflow')
                content_text = content_text.replace('"http://mlflow:5000', '"/proxy-mlflow')
                content_text = content_text.replace("'http://mlflow:5000", "'/proxy-mlflow")
                
                # 環境変数で設定されたMLflowホスト名も置換
                mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
                mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
                if mlflow_host != "mlflow" or mlflow_port != "5000":
                    content_text = content_text.replace(f'http://{mlflow_host}:{mlflow_port}', '/proxy-mlflow')
                    content_text = content_text.replace(f'"http://{mlflow_host}:{mlflow_port}', '"/proxy-mlflow')
                    content_text = content_text.replace(f"'http://{mlflow_host}:{mlflow_port}", "'/proxy-mlflow")
                
                # IPアドレスベースのURLも置換
                content_text = content_text.replace('http://0.0.0.0:5000', '/proxy-mlflow')
                
                # 異なるネットワーク間でのアクセス用に、様々なIPアドレスパターンを書き換え
                import re
                # 任意のIPアドレスとポート5000のパターンを検出して置換
                ip_pattern = r'(https?://)((?:\d{1,3}\.){3}\d{1,3}):5000'
                content_text = re.sub(ip_pattern, r'\1\2:8001/proxy-mlflow', content_text)
                
                content = content_text.encode("utf-8")
            except:
                # デコードに失敗した場合は元のコンテンツを使用
                pass
        
        # JSONの場合も、URLを書き換え
        elif content_type.startswith("application/json"):
            try:
                content_text = content.decode("utf-8")
                
                # JSONとして解析して、空の場合やnullの場合は空のJSONオブジェクトを返す
                if not content_text.strip() or content_text.strip() == "null":
                    logger.warning("空のJSONレスポンスまたはnullが返されました。空のオブジェクトに置き換えます。")
                    content_text = "{}"
                
                # すべてのMLflow絶対URLをプロキシURLに変換
                content_text = content_text.replace('http://localhost:5000', '/proxy-mlflow')
                content_text = content_text.replace('http://mlflow:5000', '/proxy-mlflow')
                
                # 環境変数で設定されたホスト名も置換
                mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
                mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
                if mlflow_host != "mlflow" or mlflow_port != "5000":
                    content_text = content_text.replace(f'http://{mlflow_host}:{mlflow_port}', '/proxy-mlflow')
                
                # IPアドレスベースのURLも置換
                content_text = content_text.replace('http://0.0.0.0:5000', '/proxy-mlflow')
                
                # 一般的なIPアドレスパターンも置換（任意のIPアドレスを検出）
                import re
                # 単純なIP置換（http://IP:5000 → /proxy-mlflow）
                ip_pattern = r'http://\d+\.\d+\.\d+\.\d+:5000'
                content_text = re.sub(ip_pattern, '/proxy-mlflow', content_text)
                
                # 外部ネットワークから見える形式に書き換え（http://IP:5000 → http://IP:8001/proxy-mlflow）
                ip_ext_pattern = r'(https?://)((?:\d{1,3}\.){3}\d{1,3}):5000'
                content_text = re.sub(ip_ext_pattern, r'\1\2:8001/proxy-mlflow', content_text)
                
                # artifact_uri内のファイルパス参照を修正（クロスネットワークアクセス時の問題修正）
                if '"artifact_uri"' in content_text or "'artifact_uri'" in content_text:
                    # JSON内でartifact_uriフィールドのパスを検出して置換
                    artifact_pattern = r'(["\'])artifact_uri[\'"]\s*:\s*["\']file:///mlflow/artifacts/([^"\']*)[\'"]\s*([,}])'
                    content_text = re.sub(artifact_pattern, r'\1artifact_uri\1: \1/proxy-mlflow/get-artifact?path=\2\1\3', content_text)
                
                # JSONとして解析可能か検証
                try:
                    json.loads(content_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSONとして解析できないコンテンツ: {e}")
                    # 解析できない場合は空のJSONオブジェクトを返す
                    content_text = "{}"
                
                content = content_text.encode("utf-8")
                
                # ここで明示的にログ出力して確認
                logger.info(f"処理後のJSONコンテンツ: {content_text[:100]}...")
                
            except Exception as e:
                logger.warning(f"JSONコンテンツの書き換えに失敗しました: {e}")
                # エラーが発生した場合は空のJSONオブジェクトを返す
                content = b"{}"
        
        # レスポンスの内容を返す
        return Response(
            content=content,
            status_code=response.status_code,
            headers=headers_to_forward,
            media_type=content_type or "text/html"
        )
    except httpx.TimeoutException:
        logger.error(f"MLflowへのリクエストがタイムアウトしました: {target_url}")
        return JSONResponse(
            status_code=504,
            content={"detail": "MLflowへのリクエストがタイムアウトしました"}
        )
    except Exception as e:
        # 接続試行の詳細情報を含むエラーメッセージを作成
        error_details = str(e)
        if "全ての接続先で接続失敗" in error_details:
            # 詳細なエラーメッセージはすでに含まれている
            pass
        else:
            # 単一のエラーの場合はURLのリストを表示
            attempted_urls = "\n".join([f"- URL{i}: {url}" for i, url in enumerate(attempt_urls)]) if 'attempt_urls' in locals() else f"- URL: {target_url}"
            error_details = f"{error_details}\n試行したURL:\n{attempted_urls}"
        
        logger.error(f"MLflowへのプロキシ中にエラーが発生しました: {error_details}", exc_info=True)
        
        # ユーザーフレンドリーなエラーメッセージを返す
        return JSONResponse(
            status_code=500,
            content={
                "detail": "MLflowサーバーへの接続に失敗しました。",
                "error": str(e),
                "suggestions": [
                    "MLflowコンテナが起動していることを確認してください。",
                    "ネットワーク接続を確認してください。",
                    "/debug-mlflow エンドポイントでMLflow接続状態を確認できます。"
                ]
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )

# MLflowアーティファクトへのアクセスを提供するエンドポイント
@app.get("/proxy-mlflow/get-artifact")
async def get_mlflow_artifact(path: str):
    """
    MLflowアーティファクトへのアクセスを提供するエンドポイント。
    異なるネットワーク間でのアーティファクトアクセスをサポート。
    
    Args:
        path: アーティファクトパス
    """
    logger.info(f"アーティファクトへのアクセス: {path}")
    
    # アーティファクトのパスを構築
    artifact_path = f"/mlflow/artifacts/{path}"
    
    # ファイルが存在するか確認
    if not os.path.exists(artifact_path):
        logger.error(f"アーティファクトが見つかりません: {artifact_path}")
        return JSONResponse(
            status_code=404,
            content={"detail": f"Artifact not found: {path}"},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    # ファイルタイプの判定
    content_type = None
    if artifact_path.endswith(".json"):
        content_type = "application/json"
    elif artifact_path.endswith(".csv"):
        content_type = "text/csv"
    elif artifact_path.endswith(".txt"):
        content_type = "text/plain"
    elif artifact_path.endswith(".png"):
        content_type = "image/png"
    elif artifact_path.endswith(".jpg") or artifact_path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif artifact_path.endswith(".html"):
        content_type = "text/html"
    else:
        content_type = "application/octet-stream"
    
    # ファイルを読み込んでレスポンスとして返す
    try:
        with open(artifact_path, "rb") as f:
            content = f.read()
            
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=86400"  # 24時間キャッシュ
            }
        )
    except Exception as e:
        logger.error(f"アーティファクト取得エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error accessing artifact: {str(e)}"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# ルートパスへのアクセスもプロキシ
@app.get("/proxy-mlflow", response_class=Response)
@app.post("/proxy-mlflow", response_class=Response)
@app.put("/proxy-mlflow", response_class=Response)
@app.delete("/proxy-mlflow", response_class=Response)
@app.patch("/proxy-mlflow", response_class=Response)
@app.options("/proxy-mlflow", response_class=Response)
async def proxy_mlflow_root(request: Request):
    logger.info(f"MLflowルートパスへのアクセス: {request.method}")
    # OPTIONSリクエストの場合は明示的に処理
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        return Response(
            content=b"",
            status_code=200,
            headers=headers
        )
    
    try:
        # プロキシ呼び出し
        return await proxy_mlflow("", request)
    except Exception as e:
        logger.error(f"MLflowルートパスアクセスエラー: {str(e)}", exc_info=True)
        # フロントエンド向けにわかりやすいエラーを返す
        return JSONResponse(
            status_code=500,
            content={"detail": "MLflowサーバーへの接続に失敗しました", "error": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# Ollamaへのプロキシエンドポイント
@app.get("/proxy-ollama")
@app.post("/proxy-ollama")
@app.put("/proxy-ollama")
@app.delete("/proxy-ollama")
@app.patch("/proxy-ollama")
@app.options("/proxy-ollama")
async def proxy_ollama_root(request: Request):
    """
    Ollamaサーバーのルートパスへのプロキシ
    """
    logger.debug(f"Ollamaルートパスへのアクセス: {request.method}")
    return await proxy_ollama("", request)

@app.get("/proxy-ollama/{path:path}")
@app.post("/proxy-ollama/{path:path}")
@app.put("/proxy-ollama/{path:path}")
@app.delete("/proxy-ollama/{path:path}")
@app.patch("/proxy-ollama/{path:path}")
@app.options("/proxy-ollama/{path:path}")
async def proxy_ollama(path: str, request: Request):
    """
    Ollamaサーバーへのリクエストをプロキシするエンドポイント
    
    Args:
        path: Ollamaのエンドポイントパス
        request: リクエストオブジェクト
    """
    # Ollamaサービスへの内部URL（環境変数から取得）
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
    
    # プロトコルが含まれていることを確認
    if not ollama_base_url.startswith(('http://', 'https://')):
        ollama_base_url = f"http://{ollama_base_url}"
    
    # 末尾のスラッシュを削除
    if ollama_base_url.endswith('/'):
        ollama_base_url = ollama_base_url[:-1]
    
    # 接続試行対象URLリスト - 優先順位順
    connection_attempts = [
        # 1. 環境変数で指定されたURL
        f"{ollama_base_url}/{path}",
        # 2. ローカルホスト（同一コンテナ内からの接続用）
        f"http://localhost:11434/{path}",
        # 3. Docker内部ネットワークの一般的なアドレス
        f"http://host.docker.internal:11434/{path}"
    ]
    
    # 最初の接続先URLをログ
    target_url = connection_attempts[0]
    logger.debug(f"Ollamaプロキシリクエスト: {request.method} {target_url}")
    
    # クエリパラメータをURLリストに適用
    query_string = ""
    if request.query_params:
        query_string = "?" + str(request.query_params)
    
    # 正規化されたURLリストを作成（クエリパラメータを含む）
    attempt_urls = [url + query_string for url in connection_attempts]
    primary_url = attempt_urls[0]
    
    # OPTIONSリクエストの場合は直接レスポンスを返す
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        return Response(
            content=b"",
            status_code=200,
            headers=headers
        )
    
    try:
        # リクエストヘッダーをコピー
        headers = {}
        for name, value in request.headers.items():
            if name.lower() not in ("host", "content-length"):
                headers[name] = value
        
        # リクエストボディを取得
        body = await request.body() if request.method != "GET" else None
        
        # 接続エラーを蓄積
        errors = []
        response = None
        
        # 複数URLを試行するフォールバックメカニズム
        for url_index, current_url in enumerate(attempt_urls):
            try:
                # リクエストメソッドに応じたHTTPリクエストを送信
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if request.method == "GET":
                        response = await client.get(
                            current_url, 
                            headers=headers,
                            follow_redirects=True
                        )
                    elif request.method == "POST":
                        response = await client.post(
                            current_url, 
                            headers=headers, 
                            content=body,
                            follow_redirects=True
                        )
                    elif request.method == "PUT":
                        response = await client.put(
                            current_url, 
                            headers=headers, 
                            content=body,
                            follow_redirects=True
                        )
                    elif request.method == "DELETE":
                        response = await client.delete(
                            current_url, 
                            headers=headers,
                            follow_redirects=True
                        )
                    elif request.method == "PATCH":
                        response = await client.patch(
                            current_url, 
                            headers=headers, 
                            content=body,
                            follow_redirects=True
                        )
                    else:
                        return JSONResponse(
                            status_code=405,
                            content={"detail": f"Method {request.method} not allowed"}
                        )
                
                # 成功した場合、使用したURLをログに記録して処理を続行
                if url_index > 0:
                    logger.info(f"Ollama接続: フォールバックURL({url_index})を使用しました: {current_url}")
                
                # 接続が成功したので、レスポンス処理に進む
                break
            
            except Exception as e:
                # 失敗した場合はエラーを記録して次のURLを試す
                error_msg = f"URL{url_index} '{current_url}': {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Ollama接続エラー: {error_msg}")
                
                # 最後のURLまで試したが全て失敗した場合
                if url_index == len(attempt_urls) - 1:
                    raise Exception(f"全ての接続先で接続失敗: {', '.join(errors)}")
                
                # 次のURLを試す
                continue
        
        # 全ての接続試行が終了後、レスポンスがない場合はエラーを返す
        if response is None:
            return JSONResponse(
                status_code=500,
                content={"detail": "Ollamaサーバーへの接続に失敗しました。レスポンスが取得できませんでした。"}
            )
        
        # レスポンスヘッダーから不要なものを除外
        headers_to_forward = dict(response.headers)
        headers_to_remove = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        for header in headers_to_remove:
            if header in headers_to_forward:
                del headers_to_forward[header]
        
        # CORSヘッダーを追加
        headers_to_forward["Access-Control-Allow-Origin"] = "*"
        headers_to_forward["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers_to_forward["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        # レスポンスの内容を返す
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers_to_forward,
            media_type=response.headers.get("content-type", "application/json")
        )
        
    except Exception as e:
        logger.error(f"Ollamaサーバーへのプロキシ中にエラーが発生しました: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Ollamaサーバーへの接続に失敗しました。",
                "error": str(e),
                "suggestions": [
                    "Ollamaコンテナが起動していることを確認してください。",
                    "ネットワーク接続を確認してください。",
                    "環境変数 OLLAMA_BASE_URL を確認してください。"
                ]
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )


# 静的ファイル用のプロキシエンドポイント（CSSやJSなど）
@app.get("/proxy-mlflow/static-files/{file_path:path}")
@app.options("/proxy-mlflow/static-files/{file_path:path}")
async def proxy_mlflow_static(file_path: str, request: Request):
    # 静的ファイルへのパスを構築
    mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
    mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
    target_url = f"http://{mlflow_host}:{mlflow_port}/static-files/{file_path}"
    logger.debug(f"MLflow静的ファイルへのプロキシリクエスト: {request.method} {target_url}")
    
    # OPTIONSリクエストの場合は直接レスポンスを返す
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Cache-Control": "public, max-age=86400"
        }
        return Response(
            content=b"",
            status_code=200,
            headers=headers
        )
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(target_url, follow_redirects=True)
            
            headers_to_forward = dict(response.headers)
            headers_to_remove = ["content-encoding", "content-length", "transfer-encoding", "connection"]
            for header in headers_to_remove:
                if header in headers_to_forward:
                    del headers_to_forward[header]
            
            # キャッシュヘッダーを追加
            headers_to_forward["Cache-Control"] = "public, max-age=86400"
            headers_to_forward["Access-Control-Allow-Origin"] = "*"
            
            # 静的ファイルの内容を取得
            content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")
            
            # JavaScriptや他のテキストベースのファイルでURLの書き換えを行う
            if content_type.startswith("text/") or content_type.startswith("application/javascript"):
                try:
                    content_text = content.decode("utf-8")
                    # MLflowへの絶対URLをプロキシURLに変換
                    content_text = content_text.replace('http://localhost:5000', '/proxy-mlflow')
                    content_text = content_text.replace('"http://mlflow:5000', '"/proxy-mlflow')
                    content_text = content_text.replace("'http://mlflow:5000", "'/proxy-mlflow")
                    content = content_text.encode("utf-8")
                except:
                    # デコードに失敗した場合は元のコンテンツを使用
                    pass
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=headers_to_forward,
                media_type=content_type
            )
    except Exception as e:
        logger.error(f"MLflow静的ファイルへのプロキシ中にエラーが発生しました: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"MLflow静的ファイルへのアクセスに失敗しました: {str(e)}"}
        )

# MLflow APIエンドポイントへのプロキシ
@app.get("/proxy-mlflow/api/{path:path}")
@app.post("/proxy-mlflow/api/{path:path}")
@app.put("/proxy-mlflow/api/{path:path}")
@app.delete("/proxy-mlflow/api/{path:path}")
@app.patch("/proxy-mlflow/api/{path:path}")
@app.options("/proxy-mlflow/api/{path:path}")
async def proxy_mlflow_api(path: str, request: Request):
    # MLflow APIへのパスを構築
    mlflow_host = os.environ.get("MLFLOW_HOST", "mlflow")
    mlflow_port = os.environ.get("MLFLOW_PORT", "5000")
    target_url = f"http://{mlflow_host}:{mlflow_port}/api/{path}"
    logger.debug(f"MLflow APIへのプロキシリクエスト: {request.method} {target_url}")
    
    try:
        # リクエストヘッダーをコピー
        headers = {}
        for name, value in request.headers.items():
            if name.lower() not in ("host", "content-length"):
                headers[name] = value
        
        # CORSヘッダーを追加
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        # OPTIONSリクエストの場合は直接レスポンスを返す
        if request.method == "OPTIONS":
            return Response(
                content=b"",
                status_code=200,
                headers=headers
            )
        
        # リクエストボディを取得
        body = await request.body() if request.method != "GET" else None
        
        # リクエスト実行
        async with httpx.AsyncClient(timeout=30.0) as client:
            if request.method == "GET":
                response = await client.get(
                    target_url, 
                    headers=headers, 
                    params=dict(request.query_params),
                    follow_redirects=True
                )
            elif request.method == "POST":
                response = await client.post(
                    target_url, 
                    headers=headers, 
                    content=body,
                    follow_redirects=True
                )
            elif request.method == "PUT":
                response = await client.put(
                    target_url, 
                    headers=headers, 
                    content=body,
                    follow_redirects=True
                )
            elif request.method == "DELETE":
                response = await client.delete(
                    target_url, 
                    headers=headers,
                    follow_redirects=True
                )
            elif request.method == "PATCH":
                response = await client.patch(
                    target_url, 
                    headers=headers, 
                    content=body,
                    follow_redirects=True
                )
            else:
                return JSONResponse(
                    status_code=405,
                    content={"detail": f"Method {request.method} not allowed"}
                )
        
        # レスポンスヘッダーから不要なものを除外
        headers_to_forward = dict(response.headers)
        headers_to_remove = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        for header in headers_to_remove:
            if header in headers_to_forward:
                del headers_to_forward[header]
        
        # CORSヘッダーを追加
        headers_to_forward["Access-Control-Allow-Origin"] = "*"
        headers_to_forward["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers_to_forward["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        # JSONレスポンスの場合、内容を確認して必要に応じて変更
        content = response.content
        content_type = response.headers.get("content-type", "")
        
        if content_type.startswith("application/json"):
            try:
                content_text = content.decode("utf-8")
                content_text = content_text.replace('http://localhost:5000', '/proxy-mlflow')
                content_text = content_text.replace('http://mlflow:5000', '/proxy-mlflow')
                content = content_text.encode("utf-8")
            except:
                # パースに失敗した場合は元のコンテンツをそのまま使用
                pass
        
        return Response(
            content=content,
            status_code=response.status_code,
            headers=headers_to_forward,
            media_type=content_type
        )
    except Exception as e:
        logger.error(f"MLflow APIへのプロキシ中にエラーが発生しました: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"MLflow APIへのアクセスに失敗しました: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
