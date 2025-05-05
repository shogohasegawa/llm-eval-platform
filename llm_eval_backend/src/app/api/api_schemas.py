"""
APIスキーマモデル定義

API用のリクエスト・レスポンスモデルを定義します。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


# キャメルケースとスネークケースの共通設定
class CamelModel(BaseModel):
    """キャメルケース変換機能を持つ基本モデル"""
    
    class Config:
        """Pydantic設定"""
        alias_generator = lambda string: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(string.split('_'))
        )
        populate_by_name = True  # v2系の設定名
        allow_population_by_field_name = True  # v1系の互換設定


# プロバイダーモデル
class ProviderBase(CamelModel):
    """プロバイダー基本モデル"""
    name: str = Field(..., description="プロバイダー名（例：OpenAI、Anthropic）")
    type: str = Field(..., description="プロバイダータイプ（例：openai、anthropic、ollama）")
    endpoint: Optional[str] = Field(None, description="APIエンドポイントURL（任意）")
    api_key: Optional[str] = Field(None, description="APIキー（任意）")
    is_active: bool = Field(True, description="プロバイダーが有効かどうか")


class ProviderCreate(ProviderBase):
    """プロバイダー作成モデル"""
    pass


class ProviderUpdate(CamelModel):
    """プロバイダー更新モデル"""
    name: Optional[str] = Field(None, description="プロバイダー名")
    type: Optional[str] = Field(None, description="プロバイダータイプ")
    endpoint: Optional[str] = Field(None, description="APIエンドポイントURL")
    api_key: Optional[str] = Field(None, description="APIキー")
    is_active: Optional[bool] = Field(None, description="プロバイダーが有効かどうか")


class Provider(ProviderBase):
    """プロバイダーレスポンスモデル"""
    id: str = Field(..., description="プロバイダーID")
    created_at: str = Field(..., description="作成日時")
    updated_at: str = Field(..., description="更新日時")

    class Config:
        """Pydantic設定"""
        from_attributes = True
        populate_by_name = True
        allow_population_by_field_name = True


# モデルモデル
class ModelBase(CamelModel):
    """モデル基本モデル"""
    provider_id: str = Field(..., description="プロバイダーID")
    name: str = Field(..., description="モデル名（API呼び出し用。例：gpt-4、claude-3-opus）")
    display_name: Optional[str] = Field(None, description="表示名（任意。指定がなければモデル名を使用）")
    description: Optional[str] = Field(None, description="モデルの説明（任意）")
    endpoint: Optional[str] = Field(None, description="APIエンドポイントURL（任意。指定がなければプロバイダーの値を使用）")
    api_key: Optional[str] = Field(None, description="APIキー（任意。指定がなければプロバイダーの値を使用）")
    parameters: Optional[Dict[str, Any]] = Field(None, description="モデルパラメータ（任意）")
    is_active: bool = Field(True, description="モデルが有効かどうか")


class ModelCreate(ModelBase):
    """モデル作成モデル"""
    pass


class ModelUpdate(CamelModel):
    """モデル更新モデル"""
    provider_id: Optional[str] = Field(None, description="プロバイダーID")
    name: Optional[str] = Field(None, description="モデル名")
    display_name: Optional[str] = Field(None, description="表示名")
    description: Optional[str] = Field(None, description="モデルの説明")
    endpoint: Optional[str] = Field(None, description="APIエンドポイントURL")
    api_key: Optional[str] = Field(None, description="APIキー")
    parameters: Optional[Dict[str, Any]] = Field(None, description="モデルパラメータ")
    is_active: Optional[bool] = Field(None, description="モデルが有効かどうか")


class Model(ModelBase):
    """モデルレスポンスモデル"""
    id: str = Field(..., description="モデルID")
    provider_name: str = Field(..., description="プロバイダー名")
    created_at: str = Field(..., description="作成日時")
    updated_at: str = Field(..., description="更新日時")

    class Config:
        """Pydantic設定"""
        from_attributes = True
        populate_by_name = True
        allow_population_by_field_name = True
