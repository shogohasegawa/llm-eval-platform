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


def save_json_file(dataset_name: str, data: Union[Dict, List], dataset_type: str, is_jsonl: bool = False) -> Path:
    """
    JSONデータをファイルとして保存する

    Args:
        dataset_name: データセット名
        data: 保存するJSONデータ
        dataset_type: データセットタイプ ('test' または 'n_shot')
        is_jsonl: JSONLファイル形式として保存するかどうか

    Returns:
        Path: 保存されたファイルのパス
    """
    # データセットタイプに応じたディレクトリを選択
    if dataset_type == "test":
        target_dir = settings.TEST_DATASETS_DIR
    else:  # "n_shot"
        target_dir = settings.NSHOT_DATASETS_DIR

    # ファイル名の生成 (データセット名)
    file_extension = ".jsonl" if is_jsonl else ".json"
    filename = f"{dataset_name}{file_extension}"
    file_path = target_dir / filename

    # 既に同名のファイルが存在する場合は新しい名前を作成
    counter = 1
    while file_path.exists():
        filename = f"{dataset_name}_{counter}{file_extension}"
        file_path = target_dir / filename
        counter += 1

    # データを保存
    with open(file_path, "w", encoding="utf-8") as f:
        if is_jsonl:
            # JSONLフォーマットで保存（各行に1つのJSONオブジェクト）
            if isinstance(data, list):
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            else:
                # 辞書の場合は単一行のJSONLとして保存
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        else:
            # 通常のJSON形式で保存
            json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"データを保存しました: {file_path}")
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

    # JSONファイルとJSONLファイルを検索
    for file_pattern in ["*.json", "*.jsonl"]:
        for file_path in directory.glob(file_pattern):
            try:
                # JSONLファイルの場合
                if file_path.suffix == '.jsonl':
                    data = []
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():  # 空行をスキップ
                                data.append(json.loads(line))

                    # JSONLメタデータを作成（最初の行または全体をメタデータとして使用）
                    # JSONLファイルの場合は全体をリストとして扱う
                    meta_data = {
                        "is_jsonl": True,  # JSONLフラグを追加
                        "file_format": "jsonl"  # ファイル形式を明示的に設定
                    }
                    if data and isinstance(data[0], dict):
                        # 最初の行から基本情報を取得
                        meta_data.update(data[0].copy() if "category" in data[0] else {})
                else:
                    # 通常のJSONファイル
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # 通常のJSONファイルの場合
                    if isinstance(data, dict):
                        meta_data = data.copy()
                        # ファイル形式情報を追加
                        meta_data["is_jsonl"] = False
                        meta_data["file_format"] = "json"
                    else:
                        meta_data = {
                            "is_jsonl": False,
                            "file_format": "json"
                        }

                # ファイル名からデータセット名を取得
                dataset_name = file_path.stem

                # 説明文の取得（JSON内にあれば使用、なければ空文字）
                description = meta_data.get("description", "") if isinstance(meta_data, dict) else ""

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

                # ファイル形式の判定
                is_jsonl = file_path.suffix.lower() == '.jsonl'

                # ファイル形式に基づく表示設定
                display_config = {
                    "file_format": "jsonl" if is_jsonl else "json",
                    "is_jsonl": is_jsonl,
                    "labels": {
                        "primary": "質問",
                        "secondary": "指示",
                        "tertiary": "入力"
                    } if is_jsonl else None
                }

                # データセットメタデータを作成
                metadata = DatasetMetadata(
                    name=meta_data.get("name", dataset_name) if isinstance(meta_data, dict) else dataset_name,
                    description=description,
                    type=dataset_type,
                    created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                    item_count=item_count,
                    file_path=str(file_path),
                    additional_props={"format": "jsonl" if is_jsonl else "json"},
                    display_config=display_config  # 表示設定を追加
                )
                datasets.append(metadata)
            except Exception as e:
                logger.error(f"データセットファイルの読み込みに失敗しました: {file_path}, エラー: {e}")

    return datasets


def get_dataset_by_name(name: str, type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    名前とタイプでデータセットを検索する
    
    Args:
        name: 検索するデータセット名
        type: 検索するデータセットタイプ (オプション)
        
    Returns:
        Optional[Dict[str, Any]]: データセットが見つかった場合はデータセット情報、見つからない場合はNone
    """
    datasets = get_datasets_list()
    
    # タイプが指定されている場合はタイプでフィルタリング
    if type:
        filtered_datasets = [d for d in datasets if d.type == type and d.name == name]
    else:
        filtered_datasets = [d for d in datasets if d.name == name]
    
    # 一致するデータセットが見つかった場合
    for dataset_meta in filtered_datasets:
        # ファイルからデータセットの内容を読み込む
        try:
            dataset = get_dataset_by_path(dataset_meta.file_path)
            if dataset:
                # デバッグ情報を追加
                logger.info(f"データセットを取得しました: {dataset_meta.name} (タイプ: {dataset_meta.type}), パス: {dataset_meta.file_path}")
                return dataset
        except Exception as e:
            logger.error(f"データセットの読み込みに失敗しました: {dataset_meta.file_path}, エラー: {e}")
            continue
    
    # 一致するデータセットが見つからなかった場合
    logger.warning(f"データセットが見つかりません: {name}{' (タイプ: ' + type + ')' if type else ''}")
    return None


def get_dataset_by_path(file_path: str) -> Optional[Dict[str, Any]]:
    """
    ファイルパスでデータセットを取得する

    Args:
        file_path: データセットファイルのパス

    Returns:
        Optional[Dict[str, Any]]: データセットが見つかった場合はデータセット情報、見つからない場合はNone
    """
    path = Path(file_path)

    if not path.exists():
        logger.error(f"データセットファイルが存在しません: {file_path}")
        return None

    try:
        # JSONLファイルかどうかを判定
        is_jsonl = path.suffix.lower() == '.jsonl'

        # データの読み込み
        if is_jsonl:
            data = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():  # 空行をスキップ
                        data.append(json.loads(line))
            # JSONLメタデータを初期化
            meta_data = {}
            if data and isinstance(data[0], dict):
                # 最初の行から基本情報を取得（カテゴリ情報があれば）
                meta_data = data[0].copy() if "category" in data[0] else {}
        else:
            # 通常のJSONファイル
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta_data = data if isinstance(data, dict) else {}

        # データセットタイプを判断
        dataset_type = "test" if str(settings.TEST_DATASETS_DIR) in file_path else "n_shot"

        # データセット名（ファイル名から拡張子を除いたもの）
        dataset_name = path.stem

        # 説明文の取得（JSON内にあれば使用、なければ空文字）
        description = meta_data.get("description", "") if isinstance(meta_data, dict) else ""

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
            name=meta_data.get("name", dataset_name) if isinstance(meta_data, dict) else dataset_name,
            description=description,
            type=dataset_type,
            created_at=datetime.fromtimestamp(path.stat().st_mtime),
            item_count=item_count,
            file_path=file_path,
            additional_props={"format": "jsonl" if is_jsonl else "json"}
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
            # リストの場合、各要素をアイテムとして扱う
            source_items = data

        # アイテムリストがある場合は処理
        if source_items is not None:
            for idx, item in enumerate(source_items):
                if isinstance(item, dict):
                    # JSONL特有の形式への対応（question_id, turns, categoryなど）
                    if is_jsonl and "turns" in item:
                        item_id = str(item.get("question_id", f"item_{idx}"))

                        # turnsを処理
                        turns = item.get("turns", [])

                        # 最初のターンをinstructionとして扱う
                        instruction = turns[0] if len(turns) > 0 else ""

                        # 2番目のターンをinputとして扱う（従来の互換性のため）
                        input_text = turns[1] if len(turns) > 1 else None

                        # 全ターンとその数をadditional_dataに格納（3ターン以上に対応するため）
                        additional_data = {
                            "turn_data": turns,  # 全ターンデータを格納
                            "turn_count": len(turns),  # ターン数を格納
                            # 既存の属性も保持
                            **{k: v for k, v in item.items() if k not in ["id", "question_id", "turns"]}
                        }
                        output = None
                    else:
                        # 標準形式
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
            logger.warning(f"標準形式でないJSONまたはJSONLデータです: {file_path}")
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
