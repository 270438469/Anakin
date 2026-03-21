from datetime import datetime
import sys
import types
from pathlib import Path

# Provide lightweight stubs so the unit tests can import the strategy module
# without requiring the full network scraping stack.
for module_name in ('aiohttp', 'requests', 'websockets'):
    if module_name not in sys.modules:
        sys.modules[module_name] = types.ModuleType(module_name)

if 'bs4' not in sys.modules:
    bs4_module = types.ModuleType('bs4')

    class BeautifulSoup:  # pragma: no cover - simple import stub
        def __init__(self, *args, **kwargs):
            pass

    bs4_module.BeautifulSoup = BeautifulSoup
    sys.modules['bs4'] = bs4_module

if 'crypto_price_tracker' not in sys.modules:
    tracker_module = types.ModuleType('crypto_price_tracker')

    class CryptoPriceTracker:
        def get_trigger_price(self, session, symbol, start_date):
            return None

        def calculate_time_to_end(self, end_date):
            return 'Unknown'

    tracker_module.CryptoPriceTracker = CryptoPriceTracker
    sys.modules['crypto_price_tracker'] = tracker_module

sys.path.append(str(Path(__file__).resolve().parent))

from stratege import PolymarketStrategy


def test_seconds_until_daily_report_before_target():
    now = datetime(2026, 3, 21, 7, 30, 0)
    assert PolymarketStrategy.seconds_until_daily_report(now=now, hour=8, minute=0) == 1800


def test_seconds_until_daily_report_after_target_rolls_next_day():
    now = datetime(2026, 3, 21, 8, 0, 1)
    assert PolymarketStrategy.seconds_until_daily_report(now=now, hour=8, minute=0) == 86399


def test_build_daily_report_text_contains_key_fields():
    strategy = object.__new__(PolymarketStrategy)
    prediction_data = {
        'event_info': {
            'title': 'Bitcoin Up or Down - March 21, 8:00AM-8:15AM ET',
            'symbol': 'BTCUSDT',
            'ticker': 'btc-updown-15m-123',
            'time_range': {'full_range': '8:00AM-8:15AM'},
            'end_date': '2026-03-21T12:15:00Z',
            'time_until_end': '0:15:00',
            'volume': 12345.67,
            'liquidity': 765.43,
        },
        'btc_price_analysis': {
            'current_price': 85000.12,
            'price_to_beat': 84980.00,
            'price_change': 20.12,
            'percent_change': 0.0237,
            'direction': 'UP ⬆️',
        },
        'markets': [
            {
                'question': 'Will BTC be higher?',
                'up_odds': 0.54,
                'down_odds': 0.46,
                'up_buy_price': 0.55,
                'down_buy_price': 0.47,
            }
        ],
    }

    report = strategy.build_daily_report_text(prediction_data, report_time=datetime(2026, 3, 21, 8, 0, 0))

    assert '# Claw 每日早报' in report
    assert '汇报时间：2026-03-21 08:00:00' in report
    assert '当前价格：$85,000.12' in report
    assert 'Up 概率/赔率：0.5400 / 54.00%' in report
