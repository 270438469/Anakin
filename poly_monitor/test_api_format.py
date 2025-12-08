import requests
import json

# 测试 Gamma API 返回的数据格式
url = "https://gamma-api.polymarket.com/markets"
params = {'limit': 10}

print("正在获取前10个市场数据...")
response = requests.get(url, params=params, timeout=15)
markets = response.json()

print(f"\n获取到 {len(markets)} 个市场\n")
print("="*100)

# 打印第一个市场的所有字段
if markets:
    print("【第一个市场的完整数据结构】")
    print("="*100)
    first_market = markets[0]
    
    # 打印所有顶级字段
    print("\n所有字段名:")
    for key in first_market.keys():
        value = first_market[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            print(f"  {key}: {value}")
        elif isinstance(value, list):
            print(f"  {key}: [list with {len(value)} items]")
        elif isinstance(value, dict):
            print(f"  {key}: {{dict with {len(value)} keys}}")
    
    # 打印完整JSON
    print("\n【完整JSON】")
    print(json.dumps(first_market, indent=2, ensure_ascii=False))
    
    print("\n" + "="*100)
    
    # 搜索包含 btc 的市场
    print("\n【搜索包含 'btc' 的市场】")
    print("="*100)
    
    btc_count = 0
    for i, market in enumerate(markets):
        # 将整个市场对象转为JSON字符串进行搜索
        market_json = json.dumps(market, ensure_ascii=False).lower()
        
        if 'btc' in market_json:
            btc_count += 1
            print(f"\n市场 {i+1} (包含 'btc'):")
            
            # 打印可能相关的字段
            for field in ['question', 'description', 'title', 'ticker', 'slug', 'market_slug', 'groupItemTitle']:
                if field in market:
                    value = market[field]
                    if value and 'btc' in str(value).lower():
                        print(f"  {field}: {value}")
    
    print(f"\n共找到 {btc_count} 个包含 'btc' 的市场")

print("\n程序结束")
