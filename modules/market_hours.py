from datetime import datetime, time
import pytz

try:
    import jpholiday
    _HAS_JPHOLIDAY = True
except ImportError:
    _HAS_JPHOLIDAY = False

JST = pytz.timezone("Asia/Tokyo")

_MORNING_START = time(9, 0)
_MORNING_END = time(11, 30)
_AFTERNOON_START = time(12, 30)
_AFTERNOON_END = time(15, 30)


def is_tse_open() -> bool:
    """
    現在、東京証券取引所が開場中かどうかを返す。
    前場 9:00-11:30 / 後場 12:30-15:30 JST（月〜金、祝日除く）。
    """
    now = datetime.now(JST)

    if now.weekday() >= 5:
        return False

    if _HAS_JPHOLIDAY and jpholiday.is_holiday(now.date()):
        return False

    t = now.time()
    in_morning = _MORNING_START <= t <= _MORNING_END
    in_afternoon = _AFTERNOON_START <= t <= _AFTERNOON_END
    return in_morning or in_afternoon


def get_refresh_interval_ms() -> int | None:
    """
    東証開場中なら 60,000 ms（60秒）を返す。
    閉場中は None を返す。
    """
    return 60_000 if is_tse_open() else None


def market_status_label() -> str:
    """
    東証の開場状態を日本語で返す。
    """
    now = datetime.now(JST)
    if now.weekday() >= 5:
        return "🔴 週末（閉場中）"
    if _HAS_JPHOLIDAY and jpholiday.is_holiday(now.date()):
        return "🔴 祝日（閉場中）"
    t = now.time()
    if _MORNING_START <= t <= _MORNING_END:
        return "🟢 前場（開場中）"
    if _AFTERNOON_START <= t <= _AFTERNOON_END:
        return "🟢 後場（開場中）"
    if t < _MORNING_START:
        return "🟡 開場前"
    if _MORNING_END < t < _AFTERNOON_START:
        return "🟡 昼休み"
    return "🔴 閉場後"
