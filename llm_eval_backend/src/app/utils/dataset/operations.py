"""
データセット操作ユーティリティ

データセットの登録、一覧取得、詳細取得などの操作を行うユーティリティ関数群
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from app.api.models import DatasetItem, DatasetMetadata
from app.config.config import get_settings

# 設定情報の取得
settings = get_settings()
logger = logging.getLogger(__name__)


def save_json_file(dataset_name: str, data: Union[Dict, List], dataset_type: str) -> Path:
    """
    JSONデータをファイルとして保存する
    
    Args:
        dataset_name: データセット名
        data: 保存するJSONデータ
        dataset_type: データセットタイプ ('test' または 'n_shot')
        
    Returns:
        Path: 保存されたファイルのパス
    """
    # データセットタイプに応じたディレクトリを選択
    if dataset_type == "test":
        target_dir = settings.TEST_DATASETS_DIR
    else:  # "n_shot"
        target_dir = settings.NSHOT_DATASETS_DIR
    
    # ファイル名の生成 (データセット名)
    filename = f"{dataset_name}.json"
    file_path = target_dir / filename
    
    # 既に同名のファイルが存在する場合は新しい名前を作成
    counter = 1
    while file_path.exists():
        filename = f"{dataset_name}_{counter}.json"
        file_path = target_dir / filename
        counter += 1
    
    # JSONデータを保存
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"JSONデータを保存しました: {file_path}")
    return file_path


def get_datasets_list() -> List[DatasetMetadata]:
    """
    利用可能なデータセットの一覧を取得する
    
    Returns:
        List[DatasetMetadata]: データセットメタデータのリスト
    """
    datasets = []
    
    # テスト用データセットを取得
    test_datasets = _get_datasets_from_dir(settings.TEST_DATASETS_DIR, "test")
    datasets.extend(test_datasets)
    
    # n-shot用データセットを取得
    nshot_datasets = _get_datasets_from_dir(settings.NSHOT_DATASETS_DIR, "n_shot")
    datasets.extend(nshot_datasets)
    
    # データセットを作成日時でソート
    datasets.sort(key=lambda x: x.created_at, reverse=True)
    
    return datasets


def _get_datasets_from_dir(directory: Path, dataset_type: str) -> List[DatasetMetadata]:
    """
    指定ディレクトリからデータセット一覧を取得する
    
    Args:
        directory: 検索対象ディレクトリ
        dataset_type: データセットタイプ
        
    Returns:
        List[DatasetMetadata]: データセットメタデータのリスト
    """
    datasets = []
    
    # 絶対パスに変換
    directory = directory.resolve()
    
    logger.info(f"データセット検索ディレクトリ: {directory}")
    
    if not directory.exists():
        logger.warning(f"ディレクトリが存在しません: {directory}")
        return datasets
    
    # JSONファイルを検索
    for file_path in directory.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # ファイル名からデータセット名を取得
            dataset_name = file_path.stem
            
            # 説明文の取得（JSON内にあれば使用、なければ空文字）
            description = data.get("description", "") if isinstance(data, dict) else ""
            
            # アイテムの数を取得
            item_count = 0
            if isinstance(data, dict):
                if "items" in data and isinstance(data["items"], list):
                    item_count = len(data["items"])
                elif "samples" in data and isinstance(data["samples"], list):
                    item_count = len(data["samples"])
                elif "data" in data and isinstance(data["data"], list):
                    item_count = len(data["data"])
            elif isinstance(data, list):
                item_count = len(data)
            
            # データセットメタデータを作成
            metadata = DatasetMetadata(
                name=data.get("name", dataset_name) if isinstance(data, dict) else dataset_name,
                description=description,
                type=dataset_type,
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                item_count=item_count,
                file_path=str(file_path)
            )
            datasets.append(metadata)
        except Exception as e:
            logger.error(f"データセットファイルの読み込みに失敗しました: {file_path}, エラー: {e}")
    
    return datasets


def get_dataset_by_name(name: str, limit: int = 0) -> Optional[Dict[str, Any]]:
    """
    名前でデータセットを検索する
    
    Args:
        name: 検索するデータセット名
        limit: アイテムの最大取得数（0は制限なし）
        
    Returns:
        Optional[Dict[str, Any]]: データセットが見つかった場合はデータセット情報、見つからない場合はNone
    """
    datasets = get_datasets_list()
    
    # 名前が完全一致するデータセットを検索
    for dataset_meta in datasets:
        if dataset_meta.name == name:
            # ファイルからデータセットの内容を読み込む
            try:
                # パフォーマンス考慮: アイテム数制限付きでデータセットを取得
                dataset = get_dataset_by_path(dataset_meta.file_path, limit)
                if dataset:
                    return dataset
            except Exception as e:
                logger.error(f"データセットの読み込みに失敗しました: {dataset_meta.file_path}, エラー: {e}")
                return None
    
    return None


def get_dataset_by_path(file_path: str, limit: int = 0) -> Optional[Dict[str, Any]]:
    """
    ファイルパスでデータセットを取得する
    
    Args:
        file_path: データセットファイルのパス
        limit: アイテムの最大取得数（0は制限なし）
        
    Returns:
        Optional[Dict[str, Any]]: データセットが見つかった場合はデータセット情報、見つからない場合はNone
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"データセットファイルが存在しません: {file_path}")
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # データセットタイプを判断
        dataset_type = "test" if str(settings.TEST_DATASETS_DIR) in file_path else "n_shot"
        
        # データセット名（ファイル名から拡張子を除いたもの）
        dataset_name = path.stem
        
        # 説明文の取得（JSON内にあれば使用、なければ空文字）
        description = data.get("description", "") if isinstance(data, dict) else ""
        
        # アイテム数の計算
        item_count = 0
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                item_count = len(data["items"])
            elif "samples" in data and isinstance(data["samples"], list):
                item_count = len(data["samples"])
            elif "data" in data and isinstance(data["data"], list):
                item_count = len(data["data"])
        elif isinstance(data, list):
            item_count = len(data)
            
        # メタデータを作成
        metadata = DatasetMetadata(
            name=data.get("name", dataset_name) if isinstance(data, dict) else dataset_name,
            description=description,
            type=dataset_type,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            item_count=item_count,
            file_path=file_path
        )
        
        # アイテムをDatasetItemに変換
        items = []
        
        # 使用するアイテムリストを決定
        source_items = None
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                source_items = data["items"]
            elif "samples" in data and isinstance(data["samples"], list):
                source_items = data["samples"]
            elif "data" in data and isinstance(data["data"], list):
                source_items = data["data"]
        elif isinstance(data, list):
            source_items = data
        
        # アイテムリストがある場合は処理
        if source_items is not None:
            # アイテム数の制限（パフォーマンス向上のため）
            # limit が 0 の場合は全てのアイテムを処理
            items_to_process = source_items
            if limit > 0 and len(source_items) > limit:
                logger.info(f"アイテム数を {limit} に制限します（全 {len(source_items)} アイテム中）")
                items_to_process = source_items[:limit]
            
            for idx, item in enumerate(items_to_process):
                if isinstance(item, dict):
                    item_id = item.get("id", f"item_{idx}")
                    instruction = item.get("instruction", "")
                    input_text = item.get("input", None)
                    output = item.get("output", None)
                    additional_data = {k: v for k, v in item.items() if k not in ["id", "instruction", "input", "output"]}
                    
                    items.append(DatasetItem(
                        id=item_id,
                        instruction=instruction,
                        input=input_text,
                        output=output,
                        additional_data=additional_data
                    ))
        else:
            # その他の形式の場合、できるだけ対応する
            logger.warning(f"標準形式でないJSONデータです: {file_path}")
            if isinstance(data, dict):
                items.append(DatasetItem(
                    id="item_0",
                    instruction="Generated from non-standard JSON",
                    input=None,
                    output=None,
                    additional_data=data
                ))
        
        return {
            "metadata": metadata,
            "items": items
        }
    except Exception as e:
        logger.error(f"データセットの読み込みに失敗しました: {file_path}, エラー: {e}")
        return None


def delete_dataset(file_path: str) -> bool:
    """
    データセットを削除する
    
    Args:
        file_path: 削除するデータセットファイルのパス
        
    Returns:
        bool: 削除に成功した場合はTrue、失敗した場合はFalse
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"削除対象のデータセットファイルが存在しません: {file_path}")
        return False
    
    try:
        path.unlink()
        logger.info(f"データセットを削除しました: {file_path}")
        return True
    except Exception as e:
        logger.error(f"データセットの削除に失敗しました: {file_path}, エラー: {e}")
        return False
