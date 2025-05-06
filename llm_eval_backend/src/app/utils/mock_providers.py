"""
モックプロバイダモジュール

テスト用の簡易的なLLMレスポンスを生成するモックを提供します。
実際のAPIを呼び出すことなく、評価プロセスやMLflowロギングのテストが可能になります。
"""
import random
import asyncio
import uuid
from typing import Dict, Any, List

async def mock_acompletion(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 100,
    temperature: float = 0.0,
    **kwargs
) -> Dict[str, Any]:
    """
    LiteLLMのacompletionと同様のインターフェースでモックレスポンスを生成します

    Args:
        model: モデル名
        messages: メッセージのリスト
        max_tokens: 最大トークン数（無視されます）
        temperature: 温度（無視されます）
        **kwargs: その他のパラメータ（すべて無視されます）

    Returns:
        LiteLLMの応答に似た形式のモックレスポンス
    """
    # ユーザーの最後の質問を取得（通常は最後のユーザーメッセージ）
    user_message = None
    for message in reversed(messages):
        if message["role"] == "user":
            user_message = message["content"]
            break
    
    # モックレスポンスを生成
    if not user_message:
        mock_content = "申し訳ありませんが、質問を理解できませんでした。"
    else:
        # 短い単純なモックレスポンス
        mock_content = f"これはテスト用のモックレスポンスです。受け取ったメッセージ：「{user_message[:50]}...」"
    
    # 少し遅延を入れて実際のAPIレスポンスをシミュレート
    await asyncio.sleep(0.2)
    
    return {
        "id": f"mock-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": 1683130070,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": mock_content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }

def patch_litellm_for_testing():
    """
    LiteLLMのacompletion関数をモック版にパッチします
    特定のプロバイダやモデルに対してのみモックを使用できるようにします
    """
    import litellm
    
    # オリジナルの関数を保存
    original_acompletion = litellm.acompletion
    
    async def patched_acompletion(**kwargs):
        model = kwargs.get("model", "")
        provider = kwargs.get("provider", "")
        
        # TestProviderの場合はモックを使用
        if provider.lower() == "testprovider" or model.lower().startswith("testprovider"):
            return await mock_acompletion(**kwargs)
        else:
            # それ以外は元の関数を使用
            return await original_acompletion(**kwargs)
    
    # LiteLLMの関数を置き換え
    litellm.acompletion = patched_acompletion
    
    return patched_acompletion

# このモジュールがインポートされたときに自動的にパッチを適用
patch_litellm_for_testing()