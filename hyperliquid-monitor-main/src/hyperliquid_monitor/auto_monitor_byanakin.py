from datetime import datetime
import time
from typing import List, Optional
import os
import signal
import sys
import threading
import json

from hyperliquid.info import Info
from hyperliquid.utils import constants

from hyperliquid_monitor.types import Trade
from hyperliquid_monitor.database import TradeDatabase

# ============================================================================
# 配置：监控地址和标签
# ============================================================================
# 如何新增地址和标签：
# 1. 在下面的 LABELS 字典中添加新条目，格式为：
#    "钱包地址": "标签"
# 2. 例如新增一个地址：
#    "0x1234567890abcdef1234567890abcdef12345678": "新地址标签"
# 3. 保存文件后，监视器会自动加载所有地址（无需修改其他代码）
# 
# 移除地址只需从字典中删除对应条目即可。
# ============================================================================
LABELS = {
    "0xdAe4DF7207feB3B350e4284C8eFe5f7DAc37f637": "魏神",
    "0x4aab8988462923ca3cbaa7e94df0cc523817cd64": "hype聪明钱"
}

# Log file path
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def log_to_file(address: str, message: str):
    """Log message to file for the given address"""
    log_file = os.path.join(LOG_DIR, f"trades_{address}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def overwrite_log(address: str, lines: list):
    """Overwrite the log file for address with the provided lines (list of strings)."""
    log_file = os.path.join(LOG_DIR, f"trades_{address}.log")
    with open(log_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def get_position_type(direction: str) -> str:
    """
    判断开仓或平仓
    "Open Long" / "Open Short" -> 开仓
    "Close Long" / "Close Short" -> 平仓
    """
    if direction and isinstance(direction, str):
        if "Open" in direction:
            return "开仓"
        elif "Close" in direction:
            return "平仓"
    return "未知"

def print_order(order: dict, address: str, console_only: bool = False):
    """Print open order information to console with colors"""
    timestamp = datetime.fromtimestamp(int(order.get("timestamp", 0)) / 1000).strftime('%Y-%m-%d %H:%M:%S')

    # Color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    # Format and either print to console or log to file
    output = f"\n{BLUE}[{timestamp}]{RESET} Open Order:" 
    if console_only:
        log_to_file(address, f"[{timestamp}] Open Order:")
    else:
        print(output)
        log_to_file(address, f"[{timestamp}] Open Order:")

    output = f"Address: {address}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

    label = LABELS.get(address)
    if label:
        output = f"Label: {label}"
        if console_only:
            log_to_file(address, output)
        else:
            print(output)
            log_to_file(address, output)

    output = f"Coin: {order.get('coin', order.get('symbol', 'Unknown'))}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

    output = f"Side: {order.get('side', order.get('sideStr', 'UNKNOWN'))}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

    output = f"Price: {order.get('px', order.get('price', ''))}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

    output = f"Size: {order.get('sz', order.get('size', ''))}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

    output = f"OrderID: {order.get('oid', order.get('id', ''))}"
    if console_only:
        log_to_file(address, output)
    else:
        print(output)
        log_to_file(address, output)

def print_trade(trade: Trade, console_only: bool = False, leverage: Optional[str] = None):
    """Print trade information to console with colors"""
    timestamp = trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    # Color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    # Choose color based on trade type and side
    color = GREEN if trade.side == "BUY" else RED

    output = f"\n{BLUE}[{timestamp}]{RESET} New {trade.trade_type}:"
    if console_only:
        log_to_file(trade.address, f"[{timestamp}] New {trade.trade_type}:")
    else:
        print(output)
        log_to_file(trade.address, f"[{timestamp}] New {trade.trade_type}:")
    
    output = f"Address: {trade.address}"
    if console_only:
        log_to_file(trade.address, output)
    else:
        print(output)
        log_to_file(trade.address, output)
    
    # Print human-friendly label if available
    label = LABELS.get(trade.address)
    if label:
        output = f"Label: {label}"
        if console_only:
            log_to_file(trade.address, output)
        else:
            print(output)
            log_to_file(trade.address, output)
    
    output = f"Coin: {trade.coin}"
    if console_only:
        log_to_file(trade.address, output)
    else:
        print(output)
        log_to_file(trade.address, output)
    
    output = f"{color}Side: {trade.side}{RESET}"
    if console_only:
        log_to_file(trade.address, f"Side: {trade.side}")
    else:
        print(output)
        log_to_file(trade.address, f"Side: {trade.side}")
    
    output = f"Size: {trade.size}"
    if console_only:
        log_to_file(trade.address, output)
    else:
        print(output)
        log_to_file(trade.address, output)
    
    output = f"Price: {trade.price}"
    if console_only:
        log_to_file(trade.address, output)
    else:
        print(output)
        log_to_file(trade.address, output)

    if trade.trade_type == "FILL":
        output = f"Direction: {trade.direction}"
        if console_only:
            log_to_file(trade.address, output)
        else:
            print(output)
            log_to_file(trade.address, output)
        
        position_type = get_position_type(trade.direction)
        position_color = GREEN if position_type == "开仓" else RED
        output = f"{position_color}Position: {position_type}{RESET}"
        if console_only:
            log_to_file(trade.address, f"Position: {position_type}")
        else:
            print(output)
            log_to_file(trade.address, f"Position: {position_type}")
        
        if trade.closed_pnl:
            pnl_color = GREEN if trade.closed_pnl > 0 else RED
            output = f"{pnl_color}PnL: {trade.closed_pnl:.2f}{RESET}"
            if console_only:
                log_to_file(trade.address, f"PnL: {trade.closed_pnl:.2f}")
            else:
                print(output)
                log_to_file(trade.address, f"PnL: {trade.closed_pnl:.2f}")
        
        output = f"Hash: {trade.tx_hash}"
        if console_only:
            log_to_file(trade.address, output)
        else:
            print(output)
            log_to_file(trade.address, output)

    # Print leverage if provided
    if leverage is not None:
        output = f"Leverage: {leverage}"
        if console_only:
            log_to_file(trade.address, output)
        else:
            print(output)
            log_to_file(trade.address, output)





class TradeMonitor:
    """监控交易历史的类"""
    def __init__(self, addresses: List[str], db_path: str = None, interval: int = 180):
        self.addresses = addresses
        self.interval = interval
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.db = TradeDatabase(db_path) if db_path else None
        self._stop_event = False
        
        # track per-address last seen fill time (milliseconds since epoch)
        self.last_seen = {addr: 0 for addr in addresses}
    def handle_shutdown(self, signum=None, frame=None):
        """处理关闭信号"""
        if self._stop_event:
            sys.exit(0)
            
        print("\n⏹ Shutting down gracefully...")
        self._stop_event = True
        self.cleanup()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        sys.exit(0)
    
    def cleanup(self):
        """清理资源"""
        if self.db:
            self.db.close()
            print("✓ Database connection closed.")
    
    def start(self):
        """启动监控"""
        # 设置信号处理（仅在主线程中设置，线程内设置会失败）
        try:
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self.handle_shutdown)
                signal.signal(signal.SIGTERM, self.handle_shutdown)
        except Exception:
            # ignore if signals cannot be set (e.g., running in a non-main thread)
            pass
        
        print(f"Fetching full history for addresses, then refreshing every {self.interval} seconds. Press Ctrl+C to stop.")

        # Initial full history fetch & save to file
        try:
            all_initial_fills = []
            for address in self.addresses:
                try:
                    # Fetch and save filled trades to file
                    # Write a tiny per-address debug marker so we can see which addresses are processed
                    try:
                        dbg_file = os.path.join(LOG_DIR, f".processed_{address}.dbg")
                        with open(dbg_file, "w", encoding="utf-8") as _df:
                            _df.write(f"processed {address} at {datetime.now().isoformat()}\n")
                    except Exception:
                        pass
                    if hasattr(self.info, "user_fills"):
                        all_fills = self.info.user_fills(address)
                    else:
                        all_fills = []

                    fills_sorted = sorted(all_fills, key=lambda f: int(f.get("time", 0))) if all_fills else []
                    label = LABELS.get(address)
                    header_label = f" ({label})" if label else ""
                    
                    # Save all fills and open orders to log file (overwrite per-address log)
                    lines = []
                    header = f"\n{'='*60}\nFill History for {address}{header_label}: {len(fills_sorted)} entries\n{'='*60}"
                    lines.append(header)

                    # Fetch user_state once per address (not per fill) to avoid excessive API calls
                    user_state_cache = None
                    try:
                        user_state_cache = self.info.user_state(address)
                    except Exception:
                        user_state_cache = {}

                    for fill in fills_sorted:
                        lines.append(str(fill))
                        trade = _fill_to_trade(fill, address)
                        # Use cached user_state to get leverage for this coin (avoid repeated API calls)
                        try:
                            lev = None
                            if user_state_cache:
                                for ap in user_state_cache.get("assetPositions", []):
                                    pos = ap.get("position") or {}
                                    if pos.get("coin") == trade.coin:
                                        l = pos.get("leverage")
                                        if l:
                                            lev = f"{l.get('type')} {l.get('value')}x"
                                        break
                        except Exception:
                            lev = None

                        # collect for combined display
                        all_initial_fills.append((fill, address))
                        if self.db:
                            try:
                                self.db.store_fill(fill)
                            except Exception as e:
                                print(f"Error storing fill to DB: {e}")

                    # Fetch open orders and include in snapshot
                    if hasattr(self.info, "open_orders"):
                        open_orders = self.info.open_orders(address)
                    else:
                        open_orders = []

                    # Always dump raw API responses for debugging when requested
                    if os.environ.get("DEBUG_MONITOR"):
                        try:
                            raw_file = os.path.join(LOG_DIR, f"raw_{address}.json")
                            with open(raw_file, "w", encoding="utf-8") as rf:
                                json.dump({"fills": all_fills, "open_orders": open_orders}, rf, ensure_ascii=False, default=str)
                        except Exception:
                            pass

                    # Optional debug: print counts returned for this address
                    if os.environ.get("DEBUG_MONITOR"):
                        try:
                            print(f"DEBUG_INITIAL: {address} fills={len(all_fills)} open_orders={len(open_orders)}")
                        except Exception:
                            pass

                    order_header = f"\n{'='*60}\nOpen Orders for {address}{header_label}: {len(open_orders)} orders\n{'='*60}"
                    lines.append(order_header)
                    for order in open_orders:
                        lines.append(str(order))
                        # also include leverage info if available
                        try:
                            lev = None
                            state = self.info.user_state(address)
                            for ap in state.get("assetPositions", []):
                                pos = ap.get("position") or {}
                                if pos.get("coin") == order.get("coin"):
                                    l = pos.get("leverage")
                                    if l:
                                        lev = f"{l.get('type')} {l.get('value')}x"
                                    break
                            if lev:
                                lines.append(f"Leverage: {lev}")
                        except Exception:
                            pass

                    try:
                        overwrite_log(address, lines)
                        if os.environ.get("DEBUG_MONITOR"):
                            print(f"DEBUG: Wrote initial log for {address} with {len(lines)} lines")
                    except Exception as e:
                        print(f"ERROR: Failed to write initial log for {address}: {e}")
                        import traceback
                        traceback.print_exc()
                    # initialize last_seen for this address to the most recent fill time
                    try:
                        if fills_sorted:
                            self.last_seen[address] = int(fills_sorted[-1].get("time", 0))
                        else:
                            self.last_seen[address] = int(time.time() * 1000)
                    except Exception:
                        self.last_seen[address] = int(time.time() * 1000)
                    
                    # (per-address full logs regenerated above; concise console summary printed after initialization)
                except Exception as e:
                    print(f"Error fetching initial data for {address}: {e}")
            # After initial fetch for all addresses, print a concise combined latest-5 timeline
            try:
                if all_initial_fills:
                    combined_sorted = sorted(all_initial_fills, key=lambda fa: int(fa[0].get("time", 0)))
                    latest_5 = combined_sorted[-5:]
                    print(f"\n[OK] Initialized combined timeline: Latest {len(latest_5)} fills across labels:\n{'='*60}")
                    for f, addr in latest_5:
                        t = _fill_to_trade(f, addr)
                        print_trade(t)
                else:
                    print("\n[OK] Initialized: no fills found for monitored addresses.")
            except Exception as e:
                print(f"Error printing combined initial timeline: {e}")

            # If INITIAL_ONLY is set, stop after initial fetch (useful for debugging)
            if os.environ.get("INITIAL_ONLY"):
                print("INITIAL_ONLY set — exiting after initial fetch.")
                self.cleanup()
                return

        except KeyboardInterrupt:
            print("\nStopping polling before initial fetch.")
            self.cleanup()
            return

        # Periodic refresh - detect new fills and print updates or '未新开仓'
        try:
            while not self._stop_event:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_fills_all = []
                for address in self.addresses:
                    try:
                        # Refresh filled trades
                        if hasattr(self.info, "user_fills"):
                            all_fills = self.info.user_fills(address)
                        else:
                            all_fills = []

                        fills_sorted = sorted(all_fills, key=lambda f: int(f.get("time", 0))) if all_fills else []
                        label = LABELS.get(address)
                        header_label = f" ({label})" if label else ""

                        # Regenerate per-address log file with the latest snapshot
                        snapshot_lines = []
                        header = f"\n[{now_str}] Refreshed Fill History for {address}{header_label}: {len(fills_sorted)} entries"
                        snapshot_lines.append(header)
                        for fill in fills_sorted:
                            snapshot_lines.append(str(fill))
                            if self.db:
                                try:
                                    self.db.store_fill(fill)
                                except Exception as e:
                                    print(f"Error storing fill to DB: {e}")

                        # Include open orders in the regenerated snapshot
                        if hasattr(self.info, "open_orders"):
                            open_orders = self.info.open_orders(address)
                        else:
                            open_orders = []
                        order_header = f"\n[{now_str}] Open Orders for {address}{header_label}: {len(open_orders)} orders"
                        snapshot_lines.append(order_header)
                        for order in open_orders:
                            snapshot_lines.append(f"[{now_str}] {order}")

                        # Optional debug: print counts returned during refresh
                        if os.environ.get("DEBUG_MONITOR"):
                            try:
                                print(f"DEBUG_REFRESH: {address} fills={len(fills_sorted)} open_orders={len(open_orders)}")
                            except Exception:
                                pass

                        try:
                            overwrite_log(address, snapshot_lines)
                            if os.environ.get("DEBUG_MONITOR"):
                                print(f"DEBUG: Rewrote log for {address} with {len(snapshot_lines)} lines")
                        except Exception as e:
                            print(f"ERROR: Failed to write refreshed log for {address}: {e}")
                            import traceback
                            traceback.print_exc()

                        # Detect new fills since last_seen timestamp and collect them
                        last_seen_ms = self.last_seen.get(address, 0)
                        new_fills = [f for f in fills_sorted if int(f.get("time", 0)) > last_seen_ms]
                        if new_fills:
                            for f in new_fills:
                                new_fills_all.append((f, address))

                        # Do not print per-address updates here; we'll aggregate after scanning all addresses
                    except Exception as e:
                        print(f"Error fetching refreshed data for {address}: {e}")
                        import traceback
                        traceback.print_exc()

                # After scanning all addresses, aggregate and display combined updates
                try:
                    if new_fills_all:
                        combined_sorted = sorted(new_fills_all, key=lambda fa: int(fa[0].get("time", 0)))
                        latest_5 = combined_sorted[-5:]
                        print(f"\n[{now_str}] 新开仓更新 (合并): {len(new_fills_all)} 条 | 显示最新 {len(latest_5)} 条\n{'='*60}")
                        for f, addr in latest_5:
                            trade = _fill_to_trade(f, addr)
                            # fetch leverage for this address and coin
                            lev = None
                            try:
                                state = self.info.user_state(addr)
                                for ap in state.get("assetPositions", []):
                                    pos = ap.get("position") or {}
                                    if pos.get("coin") == trade.coin:
                                        l = pos.get("leverage")
                                        if l:
                                            lev = f"{l.get('type')} {l.get('value')}x"
                                        break
                            except Exception:
                                lev = None

                            print_trade(trade, leverage=lev)

                        # Update last_seen per address based on new fills seen
                        for addr in self.addresses:
                            times = [int(f.get("time", 0)) for f, a in new_fills_all if a == addr]
                            if times:
                                try:
                                    self.last_seen[addr] = max(times)
                                except Exception:
                                    self.last_seen[addr] = int(time.time() * 1000)
                    else:
                        print(f"\n[{now_str}] 未新开仓 (all labels)")

                    # Print a concise positions summary for all labels
                    print('\n持仓汇总:')
                    for addr in self.addresses:
                        label = LABELS.get(addr)
                        try:
                            state = self.info.user_state(addr)
                            aps = state.get('assetPositions', [])
                            if not aps:
                                print(f"- {addr} {f'({label})' if label else ''}: 无持仓")
                                continue
                            for ap in aps:
                                pos = ap.get('position') or {}
                                coin = pos.get('coin')
                                size = pos.get('szi') or 0  # Hyperliquid SDK uses 'szi' for size
                                entry = pos.get('entryPx')   # Hyperliquid SDK uses 'entryPx' for entry price
                                liq = pos.get('liquidationPx')  # Hyperliquid SDK uses 'liquidationPx'
                                lev = pos.get('leverage')
                                lev_str = f"{lev.get('type')} {lev.get('value')}x" if isinstance(lev, dict) and lev.get('value') else str(lev) if lev else ''
                                print(f"- {addr} {f'({label})' if label else ''}: {coin} Size={size} Entry={entry} Liq={liq} Leverage={lev_str}")
                        except Exception as e:
                            print(f"- {addr} {f'({label})' if label else ''}: 无法获取持仓 ({e})")

                    # Always print latest update time as the last line
                    print(f"最后更新时间: {now_str}\n")
                except Exception as e:
                    print(f"Error aggregating/printing updates: {e}")

                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.handle_shutdown()


def _fill_to_trade(fill: dict, address: str) -> Trade:
    ts = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000)
    return Trade(
        timestamp=ts,
        address=address,
        coin=fill.get("coin", "Unknown"),
        side="BUY" if fill.get("side", "B") == "B" else "SELL",
        size=float(fill.get("sz", 0)),
        price=float(fill.get("px", 0)),
        trade_type="FILL",
        direction=fill.get("dir"),
        tx_hash=fill.get("hash"),
        fee=float(fill.get("fee", 0)) if fill.get("fee") is not None else None,
        fee_token=fill.get("feeToken"),
        start_position=float(fill.get("startPosition", 0)) if fill.get("startPosition") is not None else None,
        closed_pnl=float(fill.get("closedPnl", 0)) if fill.get("closedPnl") is not None else None,
    )


def main():
    # ========================================================================
    # 地址监控配置说明
    # ========================================================================
    # addresses 变量自动从 LABELS 字典中获取所有地址。
    # 如果需要监控新的地址，只需按照注释中的说明在 LABELS 字典中添加即可。
    # 无需修改这里的代码，因为 list(LABELS.keys()) 会自动读取所有地址。
    # 
    # 示例：新增地址后，LABELS 字典会变成：
    #   LABELS = {
    #       "0xdAe4DF7207feB3B350e4284C8eFe5f7DAc37f637": "魏神",
    #       "0x4aab8988462923ca3cbaa7e94df0cc523817cd64": "hype聪明钱",
    #       "0x新增地址": "新增标签"
    #   }
    # 然后这里会自动包含所有三个地址。
    # ========================================================================
    addresses: List[str] = list(LABELS.keys())

    # Polling interval in seconds (default 3 minutes). Can be overridden by env TEST_INTERVAL for quick tests.
    interval = int(os.environ.get("TEST_INTERVAL", "180"))
    
    # Optional: Enable database storage
    # db_path = "trades.db"
    db_path = None  # Set to "trades.db" to enable database storage

    # Create and start monitor
    monitor = TradeMonitor(addresses=addresses, db_path=db_path, interval=interval)

    # If TEST_SECONDS env var is set, run monitor in a thread for that many seconds then stop (useful for quick tests)
    test_secs = os.environ.get("TEST_SECONDS")
    if test_secs:
        try:
            secs = int(test_secs)
        except Exception:
            secs = 20
        t = threading.Thread(target=monitor.start, daemon=True)
        t.start()
        time.sleep(secs)
        # signal the monitor to stop and wait a bit
        monitor._stop_event = True
        monitor.cleanup()
        t.join(timeout=5)
        print(f"Test run complete ({secs}s)")
    else:
        monitor.start()


if __name__ == "__main__":
    main()