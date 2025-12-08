import time
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup
import json
import re
import os
import sys

# 确保本地模块可导入
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from crypto_price_tracker import CryptoPriceTracker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolymarketStrategy:
    """Polymarket BTC 价格预测自动交易策略"""
    
    def __init__(self, api_key: str = "", private_key: str = "", log_dir: str = "logs"):
        """
        初始化策略
        :param api_key: Polymarket API密钥
        :param private_key: 钱包私钥
        :param log_dir: 日志文件保存目录
        """
        self.api_key = api_key
        self.private_key = private_key
        self.base_url = "https://clob.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.trade_executed = False
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 复用 price tracker 的时间/价格工具
        self.price_tracker = CryptoPriceTracker()
        
        # 创建日志目录
        self.log_dir = log_dir
        import os
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            logger.info(f"创建日志目录: {self.log_dir}")
        
        # 若基础页面不可用，使用已知live URL作为种子
        self.seed_live_url = "https://polymarket.com/event/btc-updown-15m-1765180800"

    async def _fetch_trigger_price_with_tracker(self, symbol: str, start_date: str) -> Optional[float]:
        """使用 CryptoPriceTracker 的方法获取触发价（异步）"""
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                return await self.price_tracker.get_trigger_price(session, symbol, start_date)
        except Exception as e:
            logger.error(f"通过 tracker 获取触发价失败: {e}")
            return None

    def get_trigger_price_with_tracker(self, symbol: str, start_date: str) -> Optional[float]:
        """同步封装，便于在当前策略中直接调用"""
        try:
            return asyncio.run(self._fetch_trigger_price_with_tracker(symbol, start_date))
        except Exception as e:
            logger.error(f"运行触发价协程失败: {e}")
            return None

    def calc_time_remaining_with_tracker(self, end_date: str) -> str:
        """借用 CryptoPriceTracker 的时间剩余计算逻辑"""
        try:
            return self.price_tracker.calculate_time_to_end(end_date)
        except Exception as e:
            logger.error(f"计算剩余时间失败: {e}")
            return "Unknown"

    def _extract_symbol_from_slug_local(self, slug: str) -> Optional[str]:
        """本地回退：根据 slug 解析 BTCUSDT 样式"""
        try:
            slug = slug.lower()
            match = re.search(r'^([a-z]+)-(?:up-?or-?down|updown).*?(?:15m|30m|60m|1h)', slug)
            if match:
                return match.group(1).upper() + "USDT"
            match = re.search(r'^([a-z]+)-', slug)
            if match:
                return match.group(1).upper() + "USDT"
        except Exception:
            return None
        return None
    
    def get_all_markets(self, limit: int = 500) -> List[Dict]:
        """
        获取所有市场数据
        :param limit: 最大数量
        :return: 市场列表
        """
        try:
            url = f"{self.gamma_api}/markets"
            params = {'limit': limit}
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            markets = response.json()
            logger.info(f"成功获取 {len(markets)} 个市场")
            return markets
        except Exception as e:
            logger.error(f"获取所有市场失败: {e}")
            return []
    
    def find_markets_by_ticker(self, ticker_keyword: str) -> List[Dict]:
        """
        通过ticker关键词查找市场（搜索events数组中的ticker）
        :param ticker_keyword: ticker关键词（如 'btc-updown-15m'）
        :return: 匹配的市场列表
        """
        try:
            all_markets = self.get_all_markets()
            
            # 过滤包含ticker关键词的市场
            matched_markets = []
            for market in all_markets:
                # 检查顶层字段
                question = str(market.get('question', '')).lower()
                slug = str(market.get('slug', '')).lower()
                
                # 检查 events 数组中的 ticker
                events = market.get('events', [])
                for event in events:
                    ticker = str(event.get('ticker', '')).lower()
                    event_slug = str(event.get('slug', '')).lower()
                    event_title = str(event.get('title', '')).lower()
                    
                    # 如果ticker或slug以关键词开头，或包含关键词
                    if (ticker.startswith(ticker_keyword.lower()) or
                        event_slug.startswith(ticker_keyword.lower()) or
                        ticker_keyword.lower() in ticker or
                        ticker_keyword.lower() in event_slug or
                        ticker_keyword.lower() in event_title or
                        ticker_keyword.lower() in question or
                        ticker_keyword.lower() in slug):
                        matched_markets.append(market)
                        break  # 找到一个匹配的event就跳出
            
            logger.info(f"找到 {len(matched_markets)} 个包含 '{ticker_keyword}' 的市场")
            
            # 如果没找到，打印前5个市场的events.ticker以供调试
            if len(matched_markets) == 0 and len(all_markets) > 0:
                logger.info("调试：前5个市场的events.ticker:")
                for i, m in enumerate(all_markets[:5], 1):
                    events = m.get('events', [])
                    if events:
                        ticker = events[0].get('ticker', 'N/A')
                        title = events[0].get('title', 'N/A')
                        logger.info(f"  {i}. events[0].ticker='{ticker}', events[0].title='{title}'")
                    else:
                        logger.info(f"  {i}. question='{m.get('question', 'N/A')[:80]}'")
            
            return matched_markets
            
        except Exception as e:
            logger.error(f"查找市场失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def print_markets_summary(self, markets: List[Dict], keyword: str = ""):
        """
        打印市场摘要信息
        :param markets: 市场列表
        :param keyword: 搜索关键词
        """
        logger.info("="*100)
        logger.info(f"【搜索结果】找到 {len(markets)} 个包含 '{keyword}' 的市场")
        logger.info("="*100)
        
        for i, market in enumerate(markets, 1):
            logger.info(f"\n【市场 {i}】")
            logger.info(f"Title: {market.get('title', 'N/A')}")
            logger.info(f"Question: {market.get('question', 'N/A')}")
            logger.info(f"Ticker: {market.get('ticker', 'N/A')}")
            logger.info(f"Market Slug: {market.get('market_slug', 'N/A')}")
            logger.info(f"Slug: {market.get('slug', 'N/A')}")
            logger.info(f"ClobTokenIds: {market.get('clobTokenIds', 'N/A')}")
            logger.info(f"Active: {market.get('active', 'N/A')}")
            logger.info(f"Closed: {market.get('closed', 'N/A')}")
            logger.info(f"End Date: {market.get('end_date_iso', 'N/A')}")
            logger.info(f"Volume: ${float(market.get('volume', 0)):,.2f}")
            logger.info(f"Liquidity: ${float(market.get('liquidity', 0)):,.2f}")
            logger.info("-" * 100)
        
        logger.info("\n")
    
    def get_event_by_slug(self, event_slug: str) -> Optional[Dict]:
        """
        通过事件slug获取完整市场数据（使用Polymarket页面）
        :param event_slug: 事件slug (如 'btc-updown-15m' 或 'btc-updown-15m-1765179900')
        :return: 市场数据
        """
        try:
            # 构建Polymarket事件页面URL
            url = f"https://polymarket.com/event/{event_slug}"
            logger.info(f"正在从页面获取事件数据: {url}")
            
            market_data = self.scrape_polymarket_page(url)
            return market_data
            
        except Exception as e:
            logger.error(f"获取事件数据失败: {e}")
            return None

    def get_event_by_url(self, url: str) -> Optional[Dict]:
        """
        通过完整URL获取市场数据
        :param url: 完整的Polymarket事件URL
        :return: 市场数据
        """
        try:
            logger.info(f"正在从URL获取事件数据: {url}")
            market_data = self.scrape_polymarket_page(url)
            return market_data
        except Exception as e:
            logger.error(f"获取事件数据失败: {e}")
            return None
    
    def get_latest_btc_updown_event(self) -> Optional[str]:
        """
        获取最新的 btc-updown-15m 事件的完整 URL：优先选择带 live 标签的未来场次
        如果基础页面 404，则使用种子 live URL 页面提取 markets 列表
        """
        try:
            # 先尝试通过 gamma API 获取最新一场（按结束时间排序、未关闭、标题含 Bitcoin Up or Down）
            gamma_url = self._get_latest_btc_event_via_gamma()
            if gamma_url:
                logger.info(f"(gamma) 选取最新15分钟事件: {gamma_url}")
                return gamma_url

            base_url = "https://polymarket.com/event/btc-updown-15m"
            logger.info("正在获取最新的 btc-updown-15m 事件列表...")

            page_data = self.scrape_polymarket_page(base_url)

            # 若基础页面失败，尝试种子 live URL
            if not page_data:
                logger.warning("未能获取基础页面，尝试种子live页面")
                page_data = self.scrape_polymarket_page(self.seed_live_url)
                if page_data:
                    logger.info(f"使用种子live页面成功: {self.seed_live_url}")

            if not page_data:
                logger.warning("未能获取 btc-updown-15m 任一页面数据")
                return None

            markets = page_data.get('markets', [])
            if not markets:
                logger.warning("页面未找到 markets 列表")
                return None

            # 调试：打印第一个market的键，便于确认live字段
            first_keys = list(markets[0].keys()) if markets else []
            logger.debug(f"markets[0] keys: {first_keys}")

            def is_live(m: Dict) -> bool:
                return bool(
                    m.get('live')
                    or m.get('isLive')
                    or str(m.get('status', '')).lower() == 'live'
                    or any(str(tag).lower() == 'live' for tag in m.get('tags', []) if isinstance(tag, str))
                )

            # 收集未来场次，标记live，且标题包含 "Bitcoin Up or Down"
            candidates = []
            now = datetime.now(timezone.utc)
            for m in markets:
                title = str(m.get('title') or m.get('question') or '').lower()
                if 'bitcoin up or down' not in title:
                    continue

                end_date = m.get('endDate') or m.get('end_date_iso') or m.get('closesAt')
                slug = m.get('slug') or m.get('conditionId') or m.get('marketSlug') or m.get('market_slug')
                live_flag = is_live(m)
                if end_date and slug:
                    try:
                        end_dt = datetime.fromisoformat(str(end_date).replace('Z', '+00:00'))
                        if end_dt >= now:
                            candidates.append((end_dt, slug, live_flag))
                    except Exception:
                        continue

            # 优先选择live的未来场次
            live_future = [c for c in candidates if c[2]]
            prefer_live = bool(live_future)
            pick_pool = live_future if prefer_live else candidates

            if not pick_pool:
                logger.warning("未找到未来的15分钟场次，尝试使用最新一场")
                # 如果没有未来场次，退回到最新一场
                sorted_all = sorted(
                    [
                        (datetime.fromisoformat(str(m.get('endDate', '')).replace('Z', '+00:00')),
                         m.get('slug') or m.get('conditionId') or m.get('marketSlug') or m.get('market_slug'))
                        for m in markets
                        if m.get('endDate') and (m.get('slug') or m.get('conditionId') or m.get('marketSlug') or m.get('market_slug'))
                    ],
                    key=lambda x: x[0],
                    reverse=True
                )
                if sorted_all:
                    slug = sorted_all[0][1]
                    return f"https://polymarket.com/event/{slug}"
                return None

            # 取最近未来一场（若有live优先live池）
            pick_pool.sort(key=lambda x: x[0])
            latest_slug = pick_pool[0][1]
            full_url = f"https://polymarket.com/event/{latest_slug}"
            logger.info(f"选取最新15分钟事件: {full_url} (live优先: {'是' if prefer_live else '否'})")
            return full_url

        except Exception as e:
            logger.error(f"获取最新15分钟事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _get_latest_btc_event_via_gamma(self) -> Optional[str]:
        """使用 gamma 分页接口获取最新 BTC up-or-down-15m 市场（未关闭且标题包含 Bitcoin Up or Down）"""
        try:
            params = {
                "limit": 200,
                "active": "true",
                "archived": "false",
                "closed": "false",
                "tag_slug": "crypto-prices",
                "order": "endDate",
                "ascending": "true",
                "offset": 0,
            }
            url = f"{self.gamma_api}/events/pagination"
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", [])
            now = datetime.now(timezone.utc)
            candidates = []
            for ev in data:
                title = str(ev.get("title") or ev.get("question") or "").lower()
                ticker = str(ev.get("ticker") or ev.get("slug") or "").lower()
                if "bitcoin up or down" not in title:
                    continue
                if "btc-updown-15m" not in ticker and "btc-up-or-down-15m" not in ticker:
                    continue
                markets = ev.get("markets", [])
                for m in markets:
                    end_date = m.get("endDate") or m.get("end_date_iso") or m.get("closesAt")
                    slug = m.get("slug") or m.get("conditionId") or m.get("marketSlug") or ev.get("slug")
                    if not (end_date and slug):
                        continue
                    try:
                        end_dt = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
                        if end_dt >= now:
                            candidates.append((end_dt, slug))
                    except Exception:
                        continue
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0])
            latest_slug = candidates[0][1]
            return f"https://polymarket.com/event/{latest_slug}"
        except Exception:
            return None
    
    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """
        通过slug获取市场详情
        :param slug: 市场slug (如 'btc-updown-15m')
        :return: 市场详情
        """
        try:
            # 尝试直接获取
            url = f"{self.gamma_api}/markets/{slug}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            # 如果直接获取失败，尝试作为事件slug获取
            logger.info(f"直接获取失败，尝试作为事件slug获取...")
            return self.get_event_by_slug(slug)
            
        except Exception as e:
            logger.error(f"获取市场详情失败: {e}")
            return None
    
    def print_market_details(self, market_data: Dict):
        """
        打印市场的所有详细信息
        :param market_data: 市场数据
        """
        logger.info("="*100)
        logger.info("【POLYMARKET 市场完整数据】")
        logger.info("="*100)
        
        # 打印所有字段
        logger.info(f"\n【基础信息】")
        logger.info(f"Market ID: {market_data.get('id', 'N/A')}")
        logger.info(f"Condition ID: {market_data.get('condition_id', 'N/A')}")
        logger.info(f"Question ID: {market_data.get('question_id', 'N/A')}")
        logger.info(f"Slug: {market_data.get('slug', 'N/A')}")
        logger.info(f"Question: {market_data.get('question', 'N/A')}")
        logger.info(f"Description: {market_data.get('description', 'N/A')}")
        logger.info(f"Market Slug: {market_data.get('market_slug', 'N/A')}")
        
        logger.info(f"\n【时间信息】")
        logger.info(f"Created At: {market_data.get('created_at', 'N/A')}")
        logger.info(f"Updated At: {market_data.get('updated_at', 'N/A')}")
        logger.info(f"End Date (ISO): {market_data.get('end_date_iso', 'N/A')}")
        logger.info(f"Game Start Time: {market_data.get('game_start_time', 'N/A')}")
        logger.info(f"Closes At: {market_data.get('closes_at', 'N/A')}")
        logger.info(f"Expiration: {market_data.get('expiration', 'N/A')}")
        
        logger.info(f"\n【状态信息】")
        logger.info(f"Active: {market_data.get('active', 'N/A')}")
        logger.info(f"Closed: {market_data.get('closed', 'N/A')}")
        logger.info(f"Archived: {market_data.get('archived', 'N/A')}")
        logger.info(f"Accepting Orders: {market_data.get('accepting_orders', 'N/A')}")
        logger.info(f"Enable Order Book: {market_data.get('enable_order_book', 'N/A')}")
        
        logger.info(f"\n【市场数据】")
        logger.info(f"Volume: ${float(market_data.get('volume', 0)):,.2f}")
        logger.info(f"Volume 24h: ${float(market_data.get('volume24hr', 0)):,.2f}")
        logger.info(f"Liquidity: ${float(market_data.get('liquidity', 0)):,.2f}")
        logger.info(f"Min Incentive Size: {market_data.get('min_incentive_size', 'N/A')}")
        logger.info(f"Max Incentive Spread: {market_data.get('max_incentive_spread', 'N/A')}")
        
        logger.info(f"\n【分类标签】")
        logger.info(f"Tags: {market_data.get('tags', [])}")
        logger.info(f"Category: {market_data.get('category', 'N/A')}")
        logger.info(f"Group Item Title: {market_data.get('group_item_title', 'N/A')}")
        logger.info(f"Group Item Threshold: {market_data.get('group_item_threshold', 'N/A')}")
        
        logger.info(f"\n【图片资源】")
        logger.info(f"Image: {market_data.get('image', 'N/A')}")
        logger.info(f"Icon: {market_data.get('icon', 'N/A')}")
        logger.info(f"Thumbnail: {market_data.get('thumbnail', 'N/A')}")
        
        # 打印Outcomes（结果选项）
        outcomes = market_data.get('outcomes', [])
        logger.info(f"\n【结果选项】(共 {len(outcomes)} 个)")
        for i, outcome in enumerate(outcomes, 1):
            logger.info(f"\n  === 选项 {i} ===")
            for key, value in outcome.items():
                logger.info(f"  {key}: {value}")
        
        # 打印Tokens信息
        tokens = market_data.get('tokens', [])
        if tokens:
            logger.info(f"\n【代币信息】(共 {len(tokens)} 个)")
            for i, token in enumerate(tokens, 1):
                logger.info(f"\n  === Token {i} ===")
                for key, value in token.items():
                    logger.info(f"  {key}: {value}")
        
        # 打印Rewards信息
        rewards = market_data.get('rewards', {})
        if rewards:
            logger.info(f"\n【奖励信息】")
            logger.info(f"{json.dumps(rewards, indent=2, ensure_ascii=False)}")
        
        # 打印其他所有字段
        logger.info(f"\n【其他字段】")
        skip_keys = ['outcomes', 'tokens', 'rewards', 'id', 'condition_id', 'question_id', 
                     'question', 'description', 'active', 'closed', 'volume', 'liquidity', 
                     'tags', 'image', 'icon', 'created_at', 'end_date_iso']
        for key, value in market_data.items():
            if key not in skip_keys:
                logger.info(f"{key}: {value}")
        
        # 打印完整JSON
        logger.info(f"\n【完整JSON数据】")
        logger.info(json.dumps(market_data, indent=2, ensure_ascii=False))
        
        logger.info("="*100 + "\n")
    
    def monitor_btc_updown_15m(self, url: str = None, interval: int = 60):
        """
        监控 BTC updown 15m 市场（自动获取最新场次）
        :param url: 可选，指定固定场次URL；若为空，自动获取最新15分钟场次
        :param interval: 检查间隔(秒)，默认60秒；循环内会对齐到整分钟
        """
        logger.info(f"开始监控 BTC updown 15m 市场，检查间隔: {interval}秒\n")
        if url:
            logger.info(f"使用指定URL: {url}\n")

        while True:
            try:
                loop_start = datetime.now()
                logger.info("="*100)
                logger.info(f"检查时间: {loop_start.strftime('%Y-%m-%d %H:%M:%S')}")

                # 获取最新场次URL（如未指定固定URL）
                current_url = url
                if current_url is None:
                    current_url = self.get_latest_btc_updown_event()
                    if not current_url:
                        logger.error("未能确定最新15分钟事件URL，稍后重试")
                        # 对齐整分钟等待
                        sleep_sec = max(1, 60 - datetime.now().second)
                        time.sleep(sleep_sec)
                        continue

                logger.info(f"当前监控URL: {current_url}")

                # 获取BTC当前价格
                btc_price = self.get_btc_price()
                logger.info(f"BTC当前价格: ${btc_price:,.2f}")
                logger.info("="*100 + "\n")

                # 抓取当前场次数据
                event_data = self.get_event_by_url(current_url)

                if event_data:
                    logger.info("成功获取事件数据！")
                    self.print_market_info_from_page(event_data, btc_price=btc_price, save_to_file=True)
                else:
                    logger.error("无法获取事件数据，稍后重试")

                # 对齐到下一个整分钟
                now = datetime.now()
                sleep_seconds = max(1, 60 - now.second)
                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                logger.info("\n监控已停止")
                break
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                sleep_seconds = max(1, 60 - datetime.now().second)
                time.sleep(sleep_seconds)
    
    def parse_market_info(self, data: Dict) -> Dict:
        """
        解析市场信息
        :param data: 原始数据
        :return: 解析后的关键信息
        """
        info = {
            'event_title': 'N/A',
            'question': 'N/A',
            'end_time': 'N/A',
            'outcomes': [],
            'volumes': {},
            'liquidity': 'N/A',
            'status': 'N/A',
            'raw_data_keys': []  # 添加原始数据的所有key
        }
        
        try:
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # 记录原始数据的所有键
            if isinstance(data, dict):
                info['raw_data_keys'] = list(data.keys())
                logger.debug(f"原始数据包含的键: {info['raw_data_keys']}")
            
            # 提取基本信息
            info['question'] = data.get('question', 'N/A')
            info['event_title'] = data.get('groupItemTitle', data.get('title', data.get('description', 'N/A')))
            
            # 提取结束时间
            end_date = data.get('endDate', data.get('end_date_iso', data.get('closesAt')))
            if end_date:
                try:
                    info['end_time'] = datetime.fromisoformat(end_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    info['end_time'] = str(end_date)
            
            # 提取结果选项和价格
            outcomes = data.get('outcomes', data.get('tokens', []))
            logger.debug(f"找到 {len(outcomes)} 个结果选项")
            
            for outcome in outcomes:
                outcome_info = {
                    'name': outcome.get('outcome', outcome.get('name', 'N/A')),
                    'price': float(outcome.get('price', outcome.get('bestAsk', 0))),
                    'probability': f"{float(outcome.get('price', outcome.get('bestAsk', 0))) * 100:.2f}%",
                    'token_id': outcome.get('token_id', 'N/A')
                }
                info['outcomes'].append(outcome_info)
            
            # 提取交易量
            info['volumes'] = {
                'total': f"${float(data.get('volume', data.get('totalVolume', 0))):,.2f}",
                '24h': f"${float(data.get('volume24hr', data.get('volume24h', 0))):,.2f}"
            }
            
            # 提取流动性
            liquidity_value = data.get('liquidity', data.get('liquidityNum', 0))
            info['liquidity'] = f"${float(liquidity_value):,.2f}"
            
            # 状态
            is_active = data.get('active', data.get('isActive', data.get('enable_order_book', False)))
            info['status'] = '活跃' if is_active else '已关闭'
            
            # 添加更多可能有用的信息
            info['market_id'] = data.get('id', data.get('condition_id', 'N/A'))
            info['created_at'] = data.get('createdAt', 'N/A')
            
        except Exception as e:
            logger.error(f"解析市场信息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return info
    
    def scrape_polymarket_page(self, url: str) -> Optional[Dict]:
        """
        抓取Polymarket页面信息并自动解析
        :param url: 页面URL
        :return: 解析后的数据
        """
        try:
            logger.info(f"正在抓取页面: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取Next.js的数据
            next_data = soup.find('script', id='__NEXT_DATA__')
            if next_data:
                try:
                    json_data = json.loads(next_data.string)
                    
                    # 从 dehydratedState.queries 中查找市场数据
                    props = json_data.get('props', {}).get('pageProps', {})
                    dehydrated_state = props.get('dehydratedState', {})
                    queries = dehydrated_state.get('queries', [])
                    
                    # 查找包含市场数据的 query (通常是包含 ticker 字段的)
                    market = None
                    for query in queries:
                        query_data = query.get('state', {}).get('data', {})
                        if isinstance(query_data, dict) and query_data.get('ticker'):
                            market = query_data
                            logger.info(f"找到市场数据: ticker={market.get('ticker')}, title={market.get('title')}")
                            break
                    
                    if market:
                        return market
                    
                    # 如果上面的方法失败，尝试旧方法
                    logger.warning("未在 dehydratedState.queries 中找到市场数据，尝试其他路径...")
                    market = props.get('market', {})
                    
                    if market:
                        return market
                    
                    logger.error("所有解析方法都失败了")
                    # 打印可用的数据结构以便调试
                    logger.debug(f"Props keys: {list(props.keys())}")
                    logger.debug(f"Queries count: {len(queries)}")
                    
                except Exception as e:
                    logger.error(f"解析__NEXT_DATA__失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning("未找到__NEXT_DATA__标签")
            
            return None
            
        except Exception as e:
            logger.error(f"抓取页面失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def parse_time_range_from_title(self, title: str) -> tuple:
        """
        从标题中解析时间范围（如 "2:45AM-3:00AM"）
        :param title: 标题字符串
        :return: (开始时间字符串, 结束时间字符串)
        """
        try:
            # 匹配时间范围模式，如 "2:45AM-3:00AM" 或 "14:45-15:00"
            import re
            pattern = r'(\d{1,2}:\d{2}\s?[AP]M)\s*-\s*(\d{1,2}:\d{2}\s?[AP]M)'
            match = re.search(pattern, title, re.IGNORECASE)
            
            if match:
                start_time = match.group(1)
                end_time = match.group(2)
                return (start_time, end_time)
            
            return (None, None)
            
        except Exception as e:
            logger.error(f"解析时间范围失败: {e}")
            return (None, None)
    
    def extract_prediction_data(self, market_data: Dict, btc_price: float = 0.0) -> Dict:
        """
        从市场数据中提取用于预测的关键信息
        :param market_data: 从页面获取的市场数据
        :param btc_price: 当前BTC价格
        :return: 预测数据字典
        """
        prediction_data = {
            'timestamp': datetime.now().isoformat(),
            'btc_current_price': btc_price,
            'event_info': {},
            'markets': [],
            'series_info': {},
            'raw_data': market_data
        }
        
        try:
            # 提取事件基本信息
            prediction_data['event_info'] = {
                'id': market_data.get('id'),
                'ticker': market_data.get('ticker'),
                'slug': market_data.get('slug'),
                'title': market_data.get('title'),
                'description': market_data.get('description'),
                'start_date': market_data.get('startDate'),
                'end_date': market_data.get('endDate'),
                'start_time': market_data.get('startTime'),
                'active': market_data.get('active'),
                'closed': market_data.get('closed'),
                'volume': float(market_data.get('volume', 0)),
                'liquidity': float(market_data.get('liquidity', 0)),
                'enable_order_book': market_data.get('enableOrderBook'),
                # 从 HTML 中提取 trigger price 和 current price
                'trigger_price': market_data.get('triggerPrice'),
                'current_price': market_data.get('currentPrice')
            }

            # 通过 tracker 从 slug/ticker 推断 symbol（如 BTCUSDT），若 tracker 无该方法则使用本地回退
            slug_or_ticker = market_data.get('slug') or market_data.get('ticker') or market_data.get('title', '')
            symbol = None
            if slug_or_ticker:
                if hasattr(self.price_tracker, 'extract_symbol_from_slug'):
                    try:
                        symbol = self.price_tracker.extract_symbol_from_slug(slug_or_ticker)
                    except Exception:
                        symbol = None
                if symbol is None:
                    symbol = self._extract_symbol_from_slug_local(slug_or_ticker)
            if symbol:
                prediction_data['event_info']['symbol'] = symbol
            
            # 解析时间范围（如 2:45AM-3:00AM）
            title = market_data.get('title', '')
            time_range = self.parse_time_range_from_title(title)
            prediction_data['event_info']['time_range'] = {
                'start': time_range[0],
                'end': time_range[1],
                'full_range': f"{time_range[0]}-{time_range[1]}" if time_range[0] and time_range[1] else None
            }
            
            # 从Markets数据中提取剩余时间（Polymarket已经计算好的）
            markets = market_data.get('markets', [])
            if markets and len(markets) > 0:
                first_market = markets[0]
                # Polymarket可能在市场数据中提供剩余时间
                # 检查常见的剩余时间字段
                for time_field in ['timeRemaining', 'secondsRemaining', 'remainingTime']:
                    if time_field in first_market:
                        remaining_seconds = first_market[time_field]
                        prediction_data['event_info']['remaining_seconds'] = remaining_seconds
                        prediction_data['event_info']['remaining_minutes'] = remaining_seconds / 60
                        prediction_data['event_info']['time_until_end'] = str(timedelta(seconds=int(remaining_seconds)))
                        break
            
            # 如果Polymarket数据中没有剩余时间，则从endDate计算
            if 'remaining_seconds' not in prediction_data['event_info'] and market_data.get('endDate'):
                try:
                    end_time = datetime.fromisoformat(market_data['endDate'].replace('Z', '+00:00'))
                    now = datetime.now(end_time.tzinfo)
                    remaining_seconds = (end_time - now).total_seconds()
                    prediction_data['event_info']['remaining_seconds'] = remaining_seconds
                    prediction_data['event_info']['remaining_minutes'] = remaining_seconds / 60
                    prediction_data['event_info']['time_until_end'] = str(timedelta(seconds=int(remaining_seconds)))
                except Exception as e:
                    logger.warning(f"计算剩余时间失败: {e}")
                    prediction_data['event_info']['remaining_seconds'] = None

            # tracker 方式的剩余时间字符串（冗余展示）
            if market_data.get('endDate'):
                prediction_data['event_info']['time_remaining_tracker'] = self.calc_time_remaining_with_tracker(market_data['endDate'])
            
            # 设置市场起始时间（eventStartTime）
            start_date = (
                (market_data.get('markets') or [{}])[0].get('eventStartTime')
                if market_data.get('markets') else None
            ) or market_data.get('startDate') or market_data.get('startTime')
            
            # 优先从 HTML 获取 trigger price，否则通过 API
            trigger_price = market_data.get('triggerPrice')
            if not trigger_price:
                # 回退到 tracker API
                if symbol and start_date:
                    trigger_price = self.get_trigger_price_with_tracker(symbol, start_date)
            
            if trigger_price:
                try:
                    trigger_price = float(trigger_price)
                    prediction_data['event_info']['trigger_price'] = trigger_price
                except (ValueError, TypeError):
                    trigger_price = None
            
            # 优先从 HTML 获取 current price，否则使用传入的 btc_price
            current_price = market_data.get('currentPrice')
            if not current_price:
                current_price = btc_price
            else:
                try:
                    current_price = float(current_price)
                except (ValueError, TypeError):
                    current_price = btc_price
            
            # 计算BTC价格变化（使用 HTML 中的 trigger price 和 current price）
            if trigger_price and current_price > 0:
                price_change = current_price - trigger_price
                percent_change = (price_change / trigger_price) * 100
                direction = 'UP ⬆️' if price_change > 0 else ('DOWN ⬇️' if price_change < 0 else 'FLAT ➡️')
                
                prediction_data['btc_price_analysis'] = {
                    'price_to_beat': trigger_price,
                    'current_price': current_price,
                    'price_change': price_change,
                    'percent_change': percent_change,
                    'direction': direction
                }
            
            # 提取Markets信息（包含outcomes和outcomePrices）
            markets = market_data.get('markets', [])
            for i, mkt in enumerate(markets):
                outcomes = mkt.get('outcomes', [])
                outcome_prices = mkt.get('outcomePrices', [])

                market_info = {
                    'market_index': i,
                    'question': mkt.get('question'),
                    'condition_id': mkt.get('conditionId'),
                    'outcomes': outcomes,  # ['Up', 'Down']
                    'outcome_prices': outcome_prices,  # 前端HTML中的赔率
                    'clob_token_ids': mkt.get('clobTokenIds', []),
                    'best_bid': mkt.get('bestBid'),
                    'best_ask': mkt.get('bestAsk'),
                    'last_trade_price': mkt.get('lastTradePrice'),
                    'spread': mkt.get('spread'),
                    'volume': mkt.get('volume'),
                    'liquidity': mkt.get('liquidity')
                }
                
                # 从 outcomePrices 直接解析 Up/Down（按outcomes名称映射）
                market_info['outcome_analysis'] = {}
                up_price = None
                down_price = None
                
                if len(outcomes) == len(outcome_prices):
                    for outcome, price in zip(outcomes, outcome_prices):
                        try:
                            price_float = float(price)
                            probability = price_float * 100
                            outcome_name = str(outcome).strip()
                            
                            # 识别 Up 和 Down
                            if outcome_name.lower() == 'up':
                                up_price = price_float
                            elif outcome_name.lower() == 'down':
                                down_price = price_float
                            
                            market_info['outcome_analysis'][outcome_name] = {
                                'price': price_float,
                                'probability_percent': f"{probability:.2f}%",
                                'implied_odds': f"1:{1/price_float:.2f}" if price_float > 0 else "N/A"
                            }
                        except Exception:
                            continue
                
                # 保存 Up/Down 价格供后续使用
                market_info['up_odds'] = up_price
                market_info['down_odds'] = down_price
                
                # 获取订单簿买入价格（实际交易价格）
                clob_token_ids = mkt.get('clobTokenIds', [])
                if clob_token_ids:
                    try:
                        # 解析token IDs
                        if isinstance(clob_token_ids, str):
                            token_ids = json.loads(clob_token_ids)
                        else:
                            token_ids = clob_token_ids
                        
                        # 获取订单簿价格
                        order_book_prices = self.get_order_book_prices(token_ids)
                        market_info['up_buy_price'] = order_book_prices.get('up_buy_price')
                        market_info['down_buy_price'] = order_book_prices.get('down_buy_price')
                    except Exception as e:
                        logger.error(f"获取订单簿价格失败: {e}")
                        market_info['up_buy_price'] = None
                        market_info['down_buy_price'] = None
                
                prediction_data['markets'].append(market_info)
            
            # 提取Series信息
            series = market_data.get('series', [])
            if series:
                prediction_data['series_info'] = {
                    'title': series[0].get('title') if len(series) > 0 else None,
                    'ticker': series[0].get('ticker') if len(series) > 0 else None,
                    'recurrence': series[0].get('recurrence') if len(series) > 0 else None,
                    'volume': float(series[0].get('volume', 0)) if len(series) > 0 else 0,
                    'liquidity': float(series[0].get('liquidity', 0)) if len(series) > 0 else 0
                }
            
            # 提取标签
            tags = market_data.get('tags', [])
            prediction_data['event_info']['tags'] = [tag.get('label') for tag in tags]
            
        except Exception as e:
            logger.error(f"提取预测数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return prediction_data
    
    def save_prediction_data(self, prediction_data: Dict, filename: str = None) -> str:
        """保存预测数据到JSON文件（覆盖写入）"""
        try:
            import os

            if filename is None:
                # 固定文件名为 latest.json，覆盖写入
                filename = "latest.json"

            filepath = os.path.join(self.log_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(prediction_data, indent=2, ensure_ascii=False, fp=f)

            logger.info(f"预测数据已保存到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存预测数据失败: {e}")
            return ""
    
    def get_order_book_prices(self, token_ids: List[str]) -> Dict:
        """获取订单簿数据，返回UP和DOWN的买入价格
        :param token_ids: CLOB Token IDs列表 [token_id_up, token_id_down]
        :return: {'up_buy_price': float, 'down_buy_price': float}
        """
        try:
            if not token_ids or len(token_ids) < 2:
                logger.warning("Token IDs不足，无法获取订单簿")
                return {}
            
            # 构建订单簿请求参数
            params = [{"token_id": tid} for tid in token_ids[:2]]
            
            url = "https://clob.polymarket.com/books"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.post(url, json=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            books = response.json()
            prices = {}
            
            # 处理两个订单簿（UP和DOWN）
            for i, book in enumerate(books[:2]):
                asks = book.get('asks', [])
                if asks:
                    # 获取最低卖价（买入价格）
                    asks_sorted = sorted(asks, key=lambda x: float(x.get('price', 0)))
                    best_ask = float(asks_sorted[0].get('price', 0))
                    
                    if i == 0:
                        prices['up_buy_price'] = best_ask
                        logger.debug(f"UP买入价格: {best_ask:.4f}")
                    else:
                        prices['down_buy_price'] = best_ask
                        logger.debug(f"DOWN买入价格: {best_ask:.4f}")
            
            return prices
            
        except Exception as e:
            logger.error(f"获取订单簿价格失败: {e}")
            return {}
    
    def get_btc_price(self) -> float:
        """获取当前BTC价格"""
        try:
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "BTCUSDT"},
                timeout=5
            )
            return float(response.json()['price'])
        except Exception as e:
            logger.error(f"获取BTC价格失败: {e}")
            return 0.0
    
    def print_market_info_from_page(self, market_data: Dict, btc_price: float = 0.0, save_to_file: bool = True):
        """
        打印从页面获取的市场信息（dehydratedState格式）
        :param market_data: 从页面获取的市场数据
        :param btc_price: 当前BTC价格
        :param save_to_file: 是否保存到JSON文件
        """
        logger.info("="*100)
        logger.info("【从Polymarket页面获取的完整市场信息】")
        logger.info("="*100)
        
        # 打印完整市场数据（从 dehydratedState 获取的格式）
        logger.info(f"\n【基本信息】")
        logger.info(f"ID: {market_data.get('id', 'N/A')}")
        logger.info(f"Ticker: {market_data.get('ticker', 'N/A')}")
        logger.info(f"Slug: {market_data.get('slug', 'N/A')}")
        logger.info(f"Title: {market_data.get('title', 'N/A')}")
        logger.info(f"Description: {market_data.get('description', 'N/A')[:200]}...")
        logger.info(f"Start Date: {market_data.get('startDate', 'N/A')}")
        logger.info(f"End Date: {market_data.get('endDate', 'N/A')}")
        logger.info(f"Start Time: {market_data.get('startTime', 'N/A')}")
        logger.info(f"Active: {market_data.get('active', 'N/A')}")
        logger.info(f"Closed: {market_data.get('closed', 'N/A')}")
        logger.info(f"Volume: ${float(market_data.get('volume', 0)):,.2f}")
        logger.info(f"Liquidity: ${float(market_data.get('liquidity', 0)):,.2f}")
        logger.info(f"Enable Order Book: {market_data.get('enableOrderBook', 'N/A')}")
        
        # 打印 Markets 数组信息
        markets = market_data.get('markets', [])
        if markets:
            logger.info(f"\n【Markets 信息】(共 {len(markets)} 个)")
            for i, mkt in enumerate(markets, 1):
                logger.info(f"\n  === Market {i} ===")
                logger.info(f"  Question: {mkt.get('question', 'N/A')}")
                logger.info(f"  Condition ID: {mkt.get('conditionId', 'N/A')}")
                logger.info(f"  Outcomes: {mkt.get('outcomes', [])}")
                logger.info(f"  Outcome Prices: {mkt.get('outcomePrices', [])}")
                logger.info(f"  CLOB Token IDs: {mkt.get('clobTokenIds', [])}")
                logger.info(f"  Best Bid: {mkt.get('bestBid', 'N/A')}")
                logger.info(f"  Best Ask: {mkt.get('bestAsk', 'N/A')}")
                logger.info(f"  Last Trade Price: {mkt.get('lastTradePrice', 'N/A')}")
                logger.info(f"  Spread: {mkt.get('spread', 'N/A')}")
        
        # 打印 Series 信息
        series = market_data.get('series', [])
        if series:
            logger.info(f"\n【Series 信息】(共 {len(series)} 个)")
            for i, s in enumerate(series, 1):
                logger.info(f"\n  === Series {i} ===")
                logger.info(f"  Title: {s.get('title', 'N/A')}")
                logger.info(f"  Ticker: {s.get('ticker', 'N/A')}")
                logger.info(f"  Recurrence: {s.get('recurrence', 'N/A')}")
                logger.info(f"  Volume: ${float(s.get('volume', 0)):,.2f}")
                logger.info(f"  Liquidity: ${float(s.get('liquidity', 0)):,.2f}")
        
        # 打印 Tags 信息
        tags = market_data.get('tags', [])
        if tags:
            tag_labels = [t.get('label', 'N/A') for t in tags]
            logger.info(f"\n【Tags】{', '.join(tag_labels)}")
        
        # 打印完整 JSON
        logger.info(f"\n【完整JSON数据】")
        logger.info(json.dumps(market_data, indent=2, ensure_ascii=False))
        
        # 提取预测数据
        logger.info("\n" + "="*100)
        logger.info("【提取预测关键数据】")
        logger.info("="*100)
        
        prediction_data = self.extract_prediction_data(market_data, btc_price)
        
        # 打印预测摘要
        logger.info(f"\n事件: {prediction_data['event_info'].get('title')}")
        logger.info(f"Ticker: {prediction_data['event_info'].get('ticker')}")
        
        # 打印时间范围
        time_range = prediction_data['event_info'].get('time_range', {})
        if time_range.get('full_range'):
            logger.info(f"⏰ 时间范围: {time_range['full_range']}")
            logger.info(f"   开始时间: {time_range.get('start')}")
            logger.info(f"   结束时间: {time_range.get('end')}")
        
        logger.info(f"开始日期: {prediction_data['event_info'].get('start_date')}")
        logger.info(f"结束日期: {prediction_data['event_info'].get('end_date')}")
        if prediction_data['event_info'].get('trigger_price') is not None:
            logger.info(f"Price to beat (openPrice): ${prediction_data['event_info']['trigger_price']:,.2f}")
        
        # 打印剩余时间
        remaining_time = prediction_data['event_info'].get('time_until_end')
        remaining_minutes = prediction_data['event_info'].get('remaining_minutes')
        if remaining_time:
            logger.info(f"⏱️  距离结束剩余时间: {remaining_time}")
            if remaining_minutes is not None:
                logger.info(f"   (约 {remaining_minutes:.2f} 分钟)")
        
        # 打印当前BTC价格和价格变化分析
        logger.info(f"\n💰 BTC价格信息:")
        
        # 优先使用 HTML 中的 current_price
        btc_analysis = prediction_data.get('btc_price_analysis', {})
        display_price = btc_analysis.get('current_price', btc_price)
        
        logger.info(f"  【Current Price】当前价格: ${display_price:,.2f} (来源: HTML)")
        
        if btc_analysis.get('price_to_beat'):
            logger.info(f"  【Price to Beat】起始价格: ${btc_analysis['price_to_beat']:,.2f} (来源: HTML)")
            logger.info(f"  价格变化: ${btc_analysis['price_change']:+,.2f}")
            logger.info(f"  变化百分比: {btc_analysis['percent_change']:+.4f}%")
            logger.info(f"  方向: {btc_analysis['direction']}")
        
        logger.info(f"\n交易量: ${prediction_data['event_info'].get('volume', 0):,.2f}")
        logger.info(f"流动性: ${prediction_data['event_info'].get('liquidity', 0):,.2f}")
        
        # 打印市场预测数据
        for i, market in enumerate(prediction_data['markets'], 1):
            logger.info(f"\n市场 {i}: {market.get('question')}")
            logger.info(f"  结果选项: {market.get('outcomes')}")
            
            # 显示 UP/DOWN 赔率
            up_odds = market.get('up_odds')
            down_odds = market.get('down_odds')
            if up_odds is not None and down_odds is not None:
                logger.info(f"  【UP赔率】{up_odds:.4f} ({up_odds*100:.2f}%)")
                logger.info(f"  【DOWN赔率】{down_odds:.4f} ({down_odds*100:.2f}%)")
            else:
                logger.info(f"  赔率 (HTML): {market.get('outcome_prices')}")
            
            # 显示买入价格（从订单簿获取的实际交易价格）
            up_buy = market.get('up_buy_price')
            down_buy = market.get('down_buy_price')
            if up_buy is not None:
                logger.info(f"  【UP买入价格 (API)】{up_buy:.4f} ({up_buy*100:.2f}%)")
            if down_buy is not None:
                logger.info(f"  【DOWN买入价格 (API)】{down_buy:.4f} ({down_buy*100:.2f}%)")
        
        # 保存到文件
        if save_to_file:
            filepath = self.save_prediction_data(prediction_data)
            if filepath:
                logger.info(f"\n✓ 数据已保存到文件: {filepath}")
        
        logger.info("="*100 + "\n")
    
    def print_market_info(self, url: str):
        """
        打印市场信息
        :param url: Polymarket事件URL
        """
        logger.info("="*80)
        logger.info(f"抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        # 获取BTC当前价格
        btc_price = self.get_btc_price()
        logger.info(f"\n【BTC当前价格】${btc_price:,.2f}\n")
        
        # 抓取并解析市场信息
        market_data = self.scrape_polymarket_page(url)
        
        if market_data:
            self.print_market_info_from_page(market_data)
        else:
            logger.warning("未能获取市场信息")
        
        logger.info("="*80 + "\n")
    
    def monitor_page(self, url: str, interval: int = 60):
        """
        每分钟监控并打印页面信息
        :param url: 页面URL
        :param interval: 检查间隔(秒)
        """
        logger.info(f"开始监控BTC updown 15m市场，检查间隔: {interval}秒\n")
        
        while True:
            try:
                self.print_market_info(url)
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("\n监控已停止")
                break
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                time.sleep(interval)


def main():
    """主函数"""
    # 初始化策略
    strategy = PolymarketStrategy()
    
    # 监控 BTC updown 15m 市场
    # 不指定URL -> 自动获取最新的15分钟场次
    strategy.monitor_btc_updown_15m(url=None, interval=60)


if __name__ == "__main__":
    main()
