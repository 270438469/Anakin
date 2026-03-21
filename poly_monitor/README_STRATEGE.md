# BTC Updown 15m 监控策略

## 功能说明

这个脚本用于监控 Polymarket 的 BTC 15分钟价格预测市场，自动提取和保存预测所需的关键数据。

## 主要功能

### 1. 解析时间范围
- 从标题中提取时间范围（如 "2:45AM-3:00AM"）
- 显示开始时间和结束时间
- 使用Polymarket提供的剩余时间数据（优先）
- 如果Polymarket未提供，则从结束时间计算剩余时间

### 2. BTC价格跟踪
- **市场起始价格记录**：首次运行时记录市场起始时间对应的BTC价格作为基准
- **实时价格监控**：每60秒更新当前BTC价格
- **价格变化分析**：
  - 价格差额：当前价格 - 市场起始时间价格
  - 百分比变化
  - 方向指示：UP ⬆️ / DOWN ⬇️ / FLAT ➡️

### 3. 市场数据提取

提取以下关键预测数据：
- **事件信息**：
  - ticker（标的）
  - title（标题）
  - 时间范围（如 2:45AM-3:00AM）
  - 开始/结束日期时间
  - 剩余时间

- **市场预测数据**：
  - question（问题）
  - outcomes（结果选项，如 ['Up', 'Down']）
  - outcomePrices（赔率/价格）
  - 详细分析：
    - 每个结果的价格
    - 隐含概率（百分比）
    - 隐含赔率

- **交易数据**：
  - 交易量
  - 流动性
  - 最佳买价/卖价
  - 价差

### 4. 数据保存
- 自动保存到 `logs/` 目录
- 文件名格式：`{ticker}_{timestamp}.json`
- 包含完整的原始数据和提取的预测数据

## 使用方法

### 每日早 8 点自动汇报（默认）
```python
python stratege.py
```

脚本默认进入 `daily-report` 模式，会在**每天 08:00** 自动生成一次晨报，并输出到：

- `logs/latest.json`：最新结构化行情数据
- `logs/daily_reports/latest_report.md`：最新 Markdown 汇报
- `logs/daily_reports/report_YYYYMMDD_HHMMSS.md`：带时间戳的历史汇报

### 立即生成一次汇报
```python
python stratege.py --mode run-once
```

### 保持原来的分钟级监控模式
```python
python stratege.py --mode monitor --interval 60
```

### 自定义汇报时间
```python
python stratege.py --mode daily-report --hour 8 --minute 0
```

### 修改监控URL
编辑 `stratege.py` 文件的 `main()` 函数：

```python
def main():
    strategy = PolymarketStrategy()
    
    # 修改为你要监控的具体市场URL
    url = "https://polymarket.com/event/btc-updown-15m-1765179900?tid=1765180199075"
    
    # 监控间隔（秒）
    strategy.monitor_btc_updown_15m(url=url, interval=60)
```

## 输出示例

```
====================================================================================================
检查时间: 2025-12-08 15:40:20
BTC当前价格: $91,793.89
====================================================================================================

正在从URL获取事件数据...
成功从页面获取事件数据！

====================================================================================================
【从Polymarket页面获取的完整市场信息】
====================================================================================================

【基本信息】
ID: btc-updown-15m-1765179900
Ticker: btc-updown-15m-1765179900
Title: Bitcoin Up or Down - December 8, 2:45AM-3:00AM ET

【Markets 信息】
  === Market 1 ===
  Question: Will BTC be higher at 3:00AM than 2:45AM?
  Outcomes: ['Up', 'Down']
  Outcome Prices: ['0.52', '0.48']

====================================================================================================
【提取预测关键数据】
====================================================================================================

事件: Bitcoin Up or Down - December 8, 2:45AM-3:00AM ET
Ticker: btc-updown-15m-1765179900
⏰ 时间范围: 2:45AM-3:00AM
   开始时间: 2:45AM
   结束时间: 3:00AM
开始日期: 2025-12-08T02:45:00Z
结束日期: 2025-12-08T03:00:00Z
⏱️  距离结束剩余时间: 0:05:30
   (约 5.50 分钟)

💰 BTC价格分析:
   市场起始价格: $91,500.00
   市场起始时间: 2025-12-08T02:45:00Z
   当前BTC价格: $91,793.89
   价格变化: +$293.89
   变化百分比: +0.3211%
   方向: UP ⬆️

交易量: $125,432.50
流动性: $8,543.21

市场 1: Will BTC be higher at 3:00AM than 2:45AM?
  结果选项: ['Up', 'Down']
  价格/赔率: ['0.52', '0.48']
  详细分析:
    Up: 价格=0.52, 概率=52.00%, 赔率=1:1.92
    Down: 价格=0.48, 概率=48.00%, 赔率=1:2.08

✓ 数据已保存到文件: logs/btc-updown-15m-1765179900_20251208_154020.json
```

## JSON文件结构

保存的JSON文件包含：

```json
{
  "timestamp": "2025-12-08T15:40:20.123456",
  "btc_current_price": 91793.89,
  "event_info": {
    "ticker": "btc-updown-15m-1765179900",
    "title": "Bitcoin Up or Down - December 8, 2:45AM-3:00AM ET",
    "time_range": {
      "start": "2:45AM",
      "end": "3:00AM",
      "full_range": "2:45AM-3:00AM"
    },
    "start_date": "2025-12-08T02:45:00Z",
    "end_date": "2025-12-08T03:00:00Z",
    "remaining_seconds": 330,
    "remaining_minutes": 5.5,
    "time_until_end": "0:05:30"
  },
  "btc_price_analysis": {
    "market_start_price": 91500.00,
    "market_start_time": "2025-12-08T02:45:00Z",
    "current_price": 91793.89,
    "price_change": 293.89,
    "percent_change": 0.3211,
    "direction": "UP ⬆️"
  },
  "markets": [
    {
      "question": "Will BTC be higher at 3:00AM than 2:45AM?",
      "outcomes": ["Up", "Down"],
      "outcome_prices": ["0.52", "0.48"],
      "outcome_analysis": {
        "Up": {
          "price": 0.52,
          "probability_percent": "52.00%",
          "implied_odds": "1:1.92"
        },
        "Down": {
          "price": 0.48,
          "probability_percent": "48.00%",
          "implied_odds": "1:2.08"
        }
      }
    }
  ],
  "raw_data": { /* 完整原始数据 */ }
}
```

## 注意事项

1. **首次运行**：会记录当前BTC价格作为基准，后续运行会显示相对于基准的价格变化
2. **时区**：时间显示为市场所在时区（通常为ET - 美东时间）
3. **监控间隔**：默认60秒，可在调用时修改 `interval` 参数
4. **日志文件**：自动累积保存，每次运行生成新文件

## 停止监控

按 `Ctrl+C` 停止监控程序
