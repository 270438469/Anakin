import requests
import json

# 获取更多市场数据，搜索BTC updown 15m
url = "https://gamma-api.polymarket.com/markets"
params = {'limit': 500}

print("正在获取500个市场数据...")
response = requests.get(url, params=params, timeout=15)
markets = response.json()

print(f"获取到 {len(markets)} 个市场\n")
print("="*100)

# 搜索包含 btc-updown 或 btc updown 或 15m 的市场
print("【搜索包含 'btc', 'updown', '15m' 相关的市场】")
print("="*100)

found_markets = []

for i, market in enumerate(markets):
    market_json = json.dumps(market, ensure_ascii=False).lower()
    
    # 检查是否包含 btc 和 updown 或 15m
    has_btc = 'btc' in market_json
    has_updown = 'updown' in market_json or 'up-down' in market_json or 'up or down' in market_json
    has_15m = '15m' in market_json or '15-m' in market_json or 'fifteen' in market_json
    
    if has_btc and (has_updown or has_15m):
        found_markets.append({
            'index': i,
            'market': market,
            'has_btc': has_btc,
            'has_updown': has_updown,
            'has_15m': has_15m
        })

print(f"\n共找到 {len(found_markets)} 个相关市场\n")

for fm in found_markets:
    market = fm['market']
    print(f"\n{'='*100}")
    print(f"市场索引: {fm['index']} | BTC: {fm['has_btc']} | UpDown: {fm['has_updown']} | 15m: {fm['has_15m']}")
    print(f"{'='*100}")
    
    # 打印市场基本信息
    print(f"ID: {market.get('id')}")
    print(f"Question: {market.get('question')}")
    print(f"Slug: {market.get('slug')}")
    print(f"Active: {market.get('active')}")
    print(f"Closed: {market.get('closed')}")
    
    # 检查 events 数组中的 ticker
    events = market.get('events', [])
    if events:
        print(f"\n【Events 数组】(共 {len(events)} 个)")
        for j, event in enumerate(events):
            print(f"\n  Event {j+1}:")
            print(f"    ID: {event.get('id')}")
            print(f"    Ticker: {event.get('ticker')}")
            print(f"    Slug: {event.get('slug')}")
            print(f"    Title: {event.get('title')}")
            print(f"    Start Date: {event.get('startDate')}")
            print(f"    End Date: {event.get('endDate')}")
    else:
        print("\n【Events】: 空数组")
    
    print(f"\n【完整JSON】")
    print(json.dumps(market, indent=2, ensure_ascii=False)[:2000] + "...")

# 如果没找到，尝试只搜索 btc
if len(found_markets) == 0:
    print("\n" + "="*100)
    print("未找到包含 btc+updown/15m 的市场，搜索所有包含 'btc' 的市场...")
    print("="*100)
    
    btc_markets = []
    for i, market in enumerate(markets):
        market_json = json.dumps(market, ensure_ascii=False).lower()
        if 'btc' in market_json or 'bitcoin' in market_json:
            btc_markets.append({
                'index': i,
                'question': market.get('question', 'N/A'),
                'slug': market.get('slug', 'N/A'),
                'ticker_in_events': None
            })
            
            # 检查 events 中的 ticker
            events = market.get('events', [])
            if events and len(events) > 0:
                btc_markets[-1]['ticker_in_events'] = events[0].get('ticker', 'N/A')
    
    print(f"\n找到 {len(btc_markets)} 个包含 'btc' 或 'bitcoin' 的市场:\n")
    for bm in btc_markets[:10]:  # 只显示前10个
        print(f"Index {bm['index']}: {bm['question'][:80]}...")
        print(f"  Slug: {bm['slug']}")
        print(f"  Event Ticker: {bm['ticker_in_events']}")
        print()

print("\n程序结束")
