"""
タイムゾーン対応の日時操作ヘルパーモジュール

バックエンド全体で一貫した日時形式とタイムゾーン（JST）を使用するためのユーティリティ関数を提供します。
"""
import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Union


# JSTタイムゾーン
JST = ZoneInfo('Asia/Tokyo')


def get_current_time(timezone: ZoneInfo = JST) -> datetime.datetime:
    """
    現在の日時をJSTタイムゾーンで取得する

    Args:
        timezone: 使用するタイムゾーン（デフォルト: JST）

    Returns:
        datetime: タイムゾーン情報付きの現在時刻
    """
    return datetime.datetime.now(timezone)


def get_current_time_str(timezone: ZoneInfo = JST) -> str:
    """
    現在の日時をISO形式の文字列として取得する

    Args:
        timezone: 使用するタイムゾーン（デフォルト: JST）

    Returns:
        str: ISO形式のJST日時文字列
    """
    return get_current_time(timezone).isoformat()


def parse_datetime(date_str: Optional[str]) -> Optional[datetime.datetime]:
    """
    ISO形式の日時文字列をdatetimeオブジェクトに変換

    Args:
        date_str: 変換する日時文字列 (ISO形式)

    Returns:
        datetime: 変換されたdatetimeオブジェクト（タイムゾーン情報付き）、または入力がNoneの場合はNone
    """
    if not date_str:
        return None
    
    try:
        # タイムゾーン情報があればそのまま使用し、なければJSTと仮定
        dt = datetime.datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt
    except (ValueError, TypeError):
        # 他の形式の場合はJSTタイムゾーンで解析を試みる
        try:
            naive_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return naive_dt.replace(tzinfo=JST)
        except (ValueError, TypeError):
            return None


def format_datetime(dt: Optional[Union[datetime.datetime, str]], format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """
    datetimeオブジェクトまたは日時文字列を指定フォーマットに変換

    Args:
        dt: 変換するdatetimeオブジェクトまたは日時文字列
        format_str: 日時フォーマット文字列

    Returns:
        str: フォーマット済み日時文字列、または入力がNoneの場合はNone
    """
    if dt is None:
        return None
    
    # 文字列の場合はdatetimeに変換
    if isinstance(dt, str):
        dt = parse_datetime(dt)
        if dt is None:
            return None
    
    # タイムゾーン情報がなければJSTを追加
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    
    return dt.strftime(format_str)