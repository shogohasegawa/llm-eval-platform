"""
JSONLデータセット推論実行UI

JSONLデータセット推論のためのシンプルなWebUIを提供します。
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository

router = APIRouter(tags=["jsonl-inference-ui"])

# ロガー設定
logger = logging.getLogger(__name__)


@router.get("/jsonl-inference-ui", response_class=HTMLResponse)
async def jsonl_inference_ui(
    request: Request,
    dataset_path: Optional[str] = Query(None, description="データセットパス")
):
    """
    JSONL推論実行用の簡易WebUI
    
    Args:
        request: リクエストオブジェクト
        dataset_path: データセットパス（オプション）
        
    Returns:
        HTMLResponse: HTML形式のレスポンス
    """
    # プロバイダとモデルの取得
    provider_repo = get_provider_repository()
    model_repo = get_model_repository()
    
    providers = provider_repo.get_all_providers()
    models = model_repo.get_all_models()
    
    # プロバイダごとにモデルをグループ化
    provider_models = {}
    for model in models:
        provider_id = model.get("provider_id")
        if provider_id not in provider_models:
            provider_models[provider_id] = []
        provider_models[provider_id].append(model)
    
    # プロバイダ選択オプションのHTML
    provider_options = ""
    for provider in providers:
        provider_id = provider.get("id")
        provider_name = provider.get("name")
        provider_options += f'<option value="{provider_id}">{provider_name}</option>'
    
    # モデル選択のJavaScriptコード
    model_js = "const providerModels = {"
    for provider_id, provider_model_list in provider_models.items():
        model_js += f'"{provider_id}": ['
        for model in provider_model_list:
            model_id = model.get("id")
            model_name = model.get("name")
            model_display = model.get("display_name") or model_name
            model_js += f'{{"id": "{model_id}", "name": "{model_display}"}}, '
        model_js += "],"
    model_js += "};"
    
    # 初期データセットパス
    default_dataset_path = dataset_path or ""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>マルチターン推論実行</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1 {{
                color: #1976d2;
                text-align: center;
                margin-bottom: 30px;
            }}
            .card {{
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 25px;
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }}
            input, select, textarea {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            textarea {{
                min-height: 100px;
                font-family: monospace;
            }}
            button {{
                background: #1976d2;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                display: block;
                width: 100%;
                font-weight: bold;
                transition: background 0.3s;
            }}
            button:hover {{
                background: #1565c0;
            }}
            button:disabled {{
                background: #cccccc;
                cursor: not-allowed;
            }}
            .response {{
                margin-top: 20px;
                background: #f8f9fa;
                border-left: 4px solid #1976d2;
                padding: 15px;
                border-radius: 4px;
                white-space: pre-wrap;
                font-family: monospace;
                max-height: 400px;
                overflow-y: auto;
            }}
            .error {{
                color: #d32f2f;
                background: #ffebee;
                border-left: 4px solid #d32f2f;
            }}
            .tabs {{
                display: flex;
                margin-bottom: 20px;
            }}
            .tab {{
                padding: 10px 20px;
                cursor: pointer;
                border-bottom: 2px solid transparent;
                transition: all 0.3s;
            }}
            .tab.active {{
                border-bottom: 2px solid #1976d2;
                font-weight: bold;
                color: #1976d2;
            }}
            .tab-content {{
                display: none;
            }}
            .tab-content.active {{
                display: block;
            }}
            .form-group {{
                margin-bottom: 15px;
            }}
            .progress {{
                height: 30px;
                background-color: #e0e0e0;
                border-radius: 4px;
                margin: 20px 0;
                overflow: hidden;
            }}
            .progress-bar {{
                height: 100%;
                background: linear-gradient(90deg, #1976d2, #64b5f6);
                width: 0%;
                transition: width 0.3s;
                text-align: center;
                line-height: 30px;
                color: white;
                font-weight: bold;
            }}
            .result-item {{
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 4px;
                background: #f9f9f9;
                border-left: 3px solid #1976d2;
            }}
            .user-message {{
                background: #e3f2fd;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 8px;
            }}
            .model-message {{
                background: #f1f8e9;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 8px;
            }}
            .message-label {{
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .flex-container {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
            }}
            .flex-container > div {{
                flex: 1;
            }}
            .notification {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                background: #4caf50;
                color: white;
                border-radius: 4px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.2);
                transform: translateX(120%);
                transition: transform 0.3s;
                z-index: 1000;
            }}
            .notification.show {{
                transform: translateX(0);
            }}
        </style>
    </head>
    <body>
        <h1>マルチターン推論実行</h1>
        
        <div class="card">
            <div class="tabs">
                <div class="tab active" data-tab="run-inference">推論実行</div>
                <div class="tab" data-tab="view-results">結果確認</div>
            </div>
            
            <div class="tab-content active" id="run-inference">
                <form id="inference-form">
                    <div class="form-group">
                        <label for="dataset-path">データセットパス:</label>
                        <input 
                            type="text" 
                            id="dataset-path" 
                            name="dataset_path" 
                            value="{default_dataset_path}" 
                            placeholder="/Users/.../datasets/test/japanese_mtbench_coding.jsonl" 
                            required
                        >
                    </div>
                    
                    <div class="flex-container">
                        <div>
                            <div class="form-group">
                                <label for="provider">プロバイダ:</label>
                                <select id="provider" name="provider_id" required>
                                    <option value="">選択してください</option>
                                    {provider_options}
                                </select>
                            </div>
                        </div>
                        <div>
                            <div class="form-group">
                                <label for="model">モデル:</label>
                                <select id="model" name="model_id" required disabled>
                                    <option value="">プロバイダを選択してください</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex-container">
                        <div>
                            <div class="form-group">
                                <label for="max-tokens">最大トークン数:</label>
                                <input type="number" id="max-tokens" name="max_tokens" value="1024" min="1" max="4096">
                            </div>
                        </div>
                        <div>
                            <div class="form-group">
                                <label for="temperature">温度:</label>
                                <input type="number" id="temperature" name="temperature" value="0.7" min="0" max="2" step="0.1">
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex-container">
                        <div>
                            <div class="form-group">
                                <label for="system-message">システムメッセージ:</label>
                                <textarea id="system-message" name="system_message">You are a helpful assistant.</textarea>
                            </div>
                        </div>
                        <div>
                            <div class="form-group">
                                <label for="num-samples">サンプル数 (空欄の場合は全て):</label>
                                <input type="number" id="num-samples" name="num_samples" placeholder="例: 5" min="1">
                            </div>
                        </div>
                    </div>
                    
                    <button type="submit" id="submit-button">推論を実行</button>
                </form>
                
                <div id="job-progress" style="display: none;">
                    <h3>処理状況</h3>
                    <div class="progress">
                        <div class="progress-bar" id="progress-bar">0%</div>
                    </div>
                    <p id="job-status">準備中...</p>
                </div>
                
                <div id="response-area" style="display: none;"></div>
            </div>
            
            <div class="tab-content" id="view-results">
                <div class="form-group">
                    <label for="job-id">ジョブID:</label>
                    <input type="text" id="job-id" placeholder="ジョブIDを入力してください" required>
                </div>
                
                <button id="check-button">結果を確認</button>
                
                <div id="results-area" style="display: none;"></div>
            </div>
        </div>
        
        <div class="notification" id="notification">コピーしました</div>
        
        <script>
            /* ページ読み込み時の処理 */
            document.addEventListener('DOMContentLoaded', function() {{
                /* タブ切り替え */
                const tabs = document.querySelectorAll('.tab');
                const tabContents = document.querySelectorAll('.tab-content');
                
                tabs.forEach(tab => {{
                    tab.addEventListener('click', () => {{
                        const tabId = tab.getAttribute('data-tab');
                        
                        /* タブとコンテンツのアクティブ状態を切り替え */
                        tabs.forEach(t => t.classList.remove('active'));
                        tabContents.forEach(c => c.classList.remove('active'));
                        
                        tab.classList.add('active');
                        document.getElementById(tabId).classList.add('active');
                    }});
                }});
                
                /* URLクエリパラメータからジョブIDを取得 */
                const urlParams = new URLSearchParams(window.location.search);
                const jobId = urlParams.get('job_id');
                if (jobId) {{
                    /* ジョブIDが指定されていれば結果確認タブをアクティブにする */
                    tabs[1].click();
                    document.getElementById('job-id').value = jobId;
                    document.getElementById('check-button').click();
                }}
                
                /* プロバイダとモデルの関連付け */
                {model_js}
                
                /* プロバイダ選択時の処理 */
                const providerSelect = document.getElementById('provider');
                const modelSelect = document.getElementById('model');
                
                providerSelect.addEventListener('change', function() {{
                    const providerId = this.value;
                    modelSelect.innerHTML = '<option value="">モデルを選択してください</option>';
                    
                    if (providerId && providerModels[providerId]) {{
                        providerModels[providerId].forEach(model => {{
                            const option = document.createElement('option');
                            option.value = model.id;
                            option.textContent = model.name;
                            modelSelect.appendChild(option);
                        }});
                        modelSelect.disabled = false;
                    }} else {{
                        modelSelect.disabled = true;
                    }}
                }});
                
                /* 推論実行フォームの送信処理 */
                const inferenceForm = document.getElementById('inference-form');
                const submitButton = document.getElementById('submit-button');
                const jobProgress = document.getElementById('job-progress');
                const progressBar = document.getElementById('progress-bar');
                const jobStatus = document.getElementById('job-status');
                const responseArea = document.getElementById('response-area');
                
                inferenceForm.addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    submitButton.disabled = true;
                    jobProgress.style.display = 'block';
                    responseArea.style.display = 'none';
                    responseArea.innerHTML = '';
                    
                    const formData = new FormData(this);
                    const jsonData = {{}};
                    
                    for (const [key, value] of formData.entries()) {{
                        if (key === 'num_samples' && value === '') {{
                            /* 空の場合はnullにする */
                            jsonData[key] = null;
                        }} else if (key === 'max_tokens' || key === 'num_samples') {{
                            /* 数値に変換 */
                            jsonData[key] = parseInt(value, 10);
                        }} else if (key === 'temperature') {{
                            /* 数値に変換 */
                            jsonData[key] = parseFloat(value);
                        }} else {{
                            jsonData[key] = value;
                        }}
                    }}
                    
                    try {{
                        /* 推論ジョブの作成 */
                        const response = await fetch('/api/v1/jsonl-inference', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify(jsonData)
                        }});
                        
                        if (!response.ok) {{
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'APIエラーが発生しました');
                        }}
                        
                        const data = await response.json();
                        
                        /* ジョブIDを取得 */
                        const jobId = data.job_id;
                        
                        /* 定期的にステータス確認 */
                        const checkInterval = setInterval(async () => {{
                            const statusResponse = await fetch(`/api/v1/jsonl-inference/${{jobId}}`);
                            const statusData = await statusResponse.json();
                            
                            /* 進捗状況の更新 */
                            updateJobStatus(statusData);
                            
                            /* 処理が完了またはエラーの場合 */
                            if (statusData.status === 'completed' || statusData.status === 'failed') {{
                                clearInterval(checkInterval);
                                submitButton.disabled = false;
                                
                                /* 結果表示 */
                                if (statusData.status === 'completed') {{
                                    showSuccessResult(statusData);
                                }} else {{
                                    showErrorResult(statusData);
                                }}
                            }}
                        }}, 2000);
                        
                    }} catch (error) {{
                        showError(error.message);
                        submitButton.disabled = false;
                    }}
                }});
                
                /* ジョブステータスの更新 */
                function updateJobStatus(statusData) {{
                    const status = statusData.status;
                    
                    switch (status) {{
                        case 'pending':
                            progressBar.style.width = '10%';
                            progressBar.textContent = '10%';
                            jobStatus.textContent = '準備中...';
                            break;
                        case 'running':
                            progressBar.style.width = '50%';
                            progressBar.textContent = '50%';
                            jobStatus.textContent = '推論実行中...';
                            break;
                        case 'completed':
                            progressBar.style.width = '100%';
                            progressBar.textContent = '100%';
                            jobStatus.textContent = '完了';
                            break;
                        case 'failed':
                            progressBar.style.width = '100%';
                            progressBar.textContent = '失敗';
                            jobStatus.textContent = `エラー: ${{statusData.message}}`;
                            break;
                    }}
                }}
                
                /* 成功時の結果表示 */
                function showSuccessResult(statusData) {{
                    responseArea.style.display = 'block';
                    
                    const resultHtml = `
                        <h3>推論が完了しました</h3>
                        <p><strong>ジョブID:</strong> <code>${{statusData.job_id}}</code> <button class="copy-button" data-text="${{statusData.job_id}}">コピー</button></p>
                        <p><strong>データセット:</strong> ${{statusData.dataset_path}}</p>
                        <p><strong>モデル:</strong> ${{statusData.model}}</p>
                        <p><strong>結果ファイル:</strong> <code>${{statusData.result_file || '未生成'}}</code> <button class="copy-button" data-text="${{statusData.result_file}}">コピー</button></p>
                        <p><a href="/api/v1/jsonl-inference-ui?job_id=${{statusData.job_id}}" target="_blank">結果の詳細を表示</a></p>
                    `;
                    
                    responseArea.innerHTML = resultHtml;
                    
                    /* コピーボタンのイベントリスナー設定 */
                    const copyButtons = responseArea.querySelectorAll('.copy-button');
                    copyButtons.forEach(button => {{
                        button.addEventListener('click', function() {{
                            const textToCopy = this.getAttribute('data-text');
                            copyToClipboard(textToCopy);
                        }});
                    }});
                }}
                
                /* エラー時の結果表示 */
                function showErrorResult(statusData) {{
                    responseArea.style.display = 'block';
                    responseArea.innerHTML = `
                        <h3>エラーが発生しました</h3>
                        <p><strong>ジョブID:</strong> <code>${{statusData.job_id}}</code></p>
                        <p><strong>エラーメッセージ:</strong> ${{statusData.message}}</p>
                    `;
                }}
                
                /* エラー表示 */
                function showError(message) {{
                    jobProgress.style.display = 'none';
                    responseArea.style.display = 'block';
                    responseArea.innerHTML = `<div class="response error"><strong>エラー:</strong> ${{message}}</div>`;
                }}
                
                /* 結果確認タブの処理 */
                const checkButton = document.getElementById('check-button');
                const jobIdInput = document.getElementById('job-id');
                const resultsArea = document.getElementById('results-area');
                
                checkButton.addEventListener('click', async function() {{
                    const jobId = jobIdInput.value.trim();
                    
                    if (!jobId) {{
                        alert('ジョブIDを入力してください');
                        return;
                    }}
                    
                    checkButton.disabled = true;
                    resultsArea.style.display = 'none';
                    resultsArea.innerHTML = '';
                    
                    try {{
                        /* ジョブステータス取得 */
                        const response = await fetch(`/api/v1/jsonl-inference/${{jobId}}`);
                        
                        if (!response.ok) {{
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'APIエラーが発生しました');
                        }}
                        
                        const data = await response.json();
                        
                        resultsArea.style.display = 'block';
                        
                        /* ステータスに応じた表示 */
                        if (data.status === 'completed' && data.result_file) {{
                            /* 結果ファイルから詳細データ取得 */
                            try {{
                                const fileResponse = await fetch(`/api/v1/files?path=${{encodeURIComponent(data.result_file)}}`);
                                const fileData = await fileResponse.json();
                                
                                showDetailedResults(data, fileData);
                            }} catch (error) {{
                                /* 結果ファイル取得失敗時は基本情報のみ表示 */
                                resultsArea.innerHTML = `
                                    <h3>結果概要</h3>
                                    <p><strong>ステータス:</strong> ${{data.status}}</p>
                                    <p><strong>データセット:</strong> ${{data.dataset_path}}</p>
                                    <p><strong>モデル:</strong> ${{data.model}}</p>
                                    <p><strong>結果ファイル:</strong> <code>${{data.result_file}}</code> <button class="copy-button" data-text="${{data.result_file}}">コピー</button></p>
                                    <p><strong>エラー:</strong> 結果ファイルの読み込みに失敗しました: ${{error.message}}</p>
                                `;
                            }}
                        }} else {{
                            /* 基本情報のみ表示 */
                            resultsArea.innerHTML = `
                                <h3>結果概要</h3>
                                <p><strong>ステータス:</strong> ${{data.status}}</p>
                                <p><strong>メッセージ:</strong> ${{data.message}}</p>
                                <p><strong>データセット:</strong> ${{data.dataset_path}}</p>
                                <p><strong>モデル:</strong> ${{data.model}}</p>
                                ${{data.result_file ? `<p><strong>結果ファイル:</strong> <code>${{data.result_file}}</code> <button class="copy-button" data-text="${{data.result_file}}">コピー</button></p>` : ''}}
                            `;
                        }}
                        
                        /* コピーボタンのイベントリスナー設定 */
                        const copyButtons = resultsArea.querySelectorAll('.copy-button');
                        copyButtons.forEach(button => {{
                            button.addEventListener('click', function() {{
                                const textToCopy = this.getAttribute('data-text');
                                copyToClipboard(textToCopy);
                            }});
                        }});
                        
                    }} catch (error) {{
                        resultsArea.style.display = 'block';
                        resultsArea.innerHTML = `<div class="response error"><strong>エラー:</strong> ${{error.message}}</div>`;
                    }} finally {{
                        checkButton.disabled = false;
                    }}
                }});
                
                /* 詳細結果表示 */
                function showDetailedResults(statusData, fileData) {{
                    const questions = fileData.questions || [];
                    
                    let resultsHtml = `
                        <h3>推論結果</h3>
                        <p><strong>ジョブID:</strong> <code>${{statusData.job_id}}</code> <button class="copy-button" data-text="${{statusData.job_id}}">コピー</button></p>
                        <p><strong>データセット:</strong> ${{statusData.dataset_path}}</p>
                        <p><strong>モデル:</strong> ${{statusData.model}}</p>
                        <p><strong>結果ファイル:</strong> <code>${{statusData.result_file}}</code> <button class="copy-button" data-text="${{statusData.result_file}}">コピー</button></p>
                        <p><strong>総質問数:</strong> ${{fileData.total_questions || 0}}</p>
                        <p><strong>完了質問数:</strong> ${{fileData.completed_questions || 0}}</p>
                    `;
                    
                    if (questions.length > 0) {{
                        resultsHtml += `<h3>質問の応答例 (最大5件)</h3>`;
                        
                        /* 最大5件の質問を表示 */
                        const displayQuestions = questions.slice(0, 5);
                        
                        displayQuestions.forEach((question, index) => {{
                            resultsHtml += `
                                <div class="result-item">
                                    <h4>質問 ${{index + 1}} (ID: ${{question.question_id}})</h4>
                                    <p><strong>カテゴリ:</strong> ${{question.category || 'なし'}}</p>
                                    <h5>ターン結果:</h5>
                            `;
                            
                            /* ターン結果の表示 */
                            if (question.turns && question.turns.length > 0) {{
                                question.turns.forEach((turn, turnIndex) => {{
                                    resultsHtml += `
                                        <div style="margin-bottom: 15px; border-left: 3px solid #4caf50; padding-left: 10px;">
                                            <p><strong>ターン ${{turnIndex + 1}}:</strong></p>
                                            <div class="user-message">
                                                <div class="message-label">ユーザー:</div>
                                                ${{turn.user_input}}
                                            </div>
                                            <div class="model-message">
                                                <div class="message-label">モデル:</div>
                                                ${{turn.model_output}}
                                            </div>
                                            <p><small>処理時間: ${{turn.latency ? turn.latency.toFixed(2) + '秒' : 'N/A'}}</small></p>
                                        </div>
                                    `;
                                }});
                            }} else {{
                                resultsHtml += `<p>ターン結果がありません</p>`;
                            }}
                            
                            resultsHtml += `</div>`;
                        }});
                        
                        /* 表示していない質問がある場合 */
                        if (questions.length > 5) {{
                            resultsHtml += `<p><em>他 ${{questions.length - 5}} 件の質問結果は省略されています。すべての結果は結果ファイルを確認してください。</em></p>`;
                        }}
                    }}
                    
                    resultsArea.innerHTML = resultsHtml;
                }}
                
                /* クリップボードにコピー */
                function copyToClipboard(text) {{
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    
                    /* 通知表示 */
                    const notification = document.getElementById('notification');
                    notification.classList.add('show');
                    
                    setTimeout(() => {{
                        notification.classList.remove('show');
                    }}, 2000);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content


@router.get("/jsonl-inference/status", response_class=HTMLResponse)
async def jsonl_inference_status_ui(
    request: Request,
    job_id: Optional[str] = Query(None, description="ジョブID")
):
    """
    JSONL推論ジョブのステータス確認用WebUI
    
    Args:
        request: リクエストオブジェクト
        job_id: ジョブID（オプション）
        
    Returns:
        HTMLResponse: HTML形式のレスポンス
    """
    # 推論UIページにリダイレクト
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0;url=/api/v1/jsonl-inference-ui?job_id={job_id or ''}">
        <title>リダイレクト中...</title>
    </head>
    <body>
        <p>リダイレクト中...</p>
        <p><a href="/api/v1/jsonl-inference-ui?job_id={job_id or ''}">自動的にリダイレクトされない場合はこちらをクリックしてください</a></p>
    </body>
    </html>
    """
    return html_content


@router.get("/files", tags=["files"])
async def get_file_content(path: str):
    """
    ファイルの内容を取得するAPI
    
    Args:
        path: ファイルパス
        
    Returns:
        Dict: ファイルの内容
    """
    import os
    import json
    
    if not os.path.exists(path):
        return {"error": "ファイルが存在しません"}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
        return content
    except Exception as e:
        logger.error(f"ファイル読み込みエラー: {e}", exc_info=True)
        return {"error": f"ファイル読み込みエラー: {str(e)}"}