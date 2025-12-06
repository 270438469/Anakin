from datetime import datetime
import time
from typing import List, Optional
import os
import signal
import sys

from hyperliquid.info import Info
from hyperliquid.utils import constants

from hyperliquid_monitor.types import Trade
from hyperliquid_monitor.database import TradeDatabase

# Human-friendly labels for addresses
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

    # Choose color based on side
    color = GREEN if order.get("side", "B") == "B" else RED

    output = f"\n{YELLOW}[{timestamp}]{RESET} Open Order:"
    if not console_only:
        print(output)
        log_to_file(address, f"[{timestamp}] Open Order:")
    
    output = f"Address: {address}"
    if not console_only:
        print(output)
        log_to_file(address, output)
    
    label = LABELS.get(address)
    if label:
        output = f"Label: {label}"
        if not console_only:
            print(output)
            log_to_file(address, output)
    
    output = f"Coin: {order.get('coin', 'Unknown')}"
    if not console_only:
        print(output)
        log_to_file(address, output)
    
    output = f"{color}Side: {'BUY' if order.get('side', 'B') == 'B' else 'SELL'}{RESET}"
    if not console_only:
        print(output)
        log_to_file(address, f"Side: {'BUY' if order.get('side', 'B') == 'B' else 'SELL'}")
    
    output = f"Size: {order.get('sz', 0)}"
    if not console_only:
        print(output)
        log_to_file(address, output)
    
    output = f"Limit Price: {order.get('limitPx', 0)}"
    if not console_only:
        print(output)
        log_to_file(address, output)
    
    output = f"Order ID: {order.get('oid', 'Unknown')}"
    if not console_only:
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
    if not console_only:
        print(output)
        log_to_file(trade.address, f"[{timestamp}] New {trade.trade_type}:")
    
    output = f"Address: {trade.address}"
    if not console_only:
        print(output)
        log_to_file(trade.address, output)
    
    # Print human-friendly label if available
    label = LABELS.get(trade.address)
    if label:
        output = f"Label: {label}"
        if not console_only:
            print(output)
            log_to_file(trade.address, output)
    
    output = f"Coin: {trade.coin}"
    if not console_only:
        print(output)
        log_to_file(trade.address, output)
    
    output = f"{color}Side: {trade.side}{RESET}"
    if not console_only:
        print(output)
        log_to_file(trade.address, f"Side: {trade.side}")
    
    output = f"Size: {trade.size}"
    if not console_only:
        print(output)
        log_to_file(trade.address, output)
    
    output = f"Price: {trade.price}"
    if not console_only:
        print(output)
        log_to_file(trade.address, output)

    if trade.trade_type == "FILL":
        output = f"Direction: {trade.direction}"
        if not console_only:
            print(output)
            log_to_file(trade.address, output)
        
        position_type = get_position_type(trade.direction)
        position_color = GREEN if position_type == "开仓" else RED
        output = f"{position_color}Position: {position_type}{RESET}"
        if not console_only:
            print(output)
            log_to_file(trade.address, f"Position: {position_type}")
        
        if trade.closed_pnl:
            pnl_color = GREEN if trade.closed_pnl > 0 else RED
            output = f"{pnl_color}PnL: {trade.closed_pnl:.2f}{RESET}"
            if not console_only:
                print(output)
                log_to_file(trade.address, f"PnL: {trade.closed_pnl:.2f}")
        
        output = f"Hash: {trade.tx_hash}"
        if not console_only:
            print(output)
            log_to_file(trade.address, output)

    # Print leverage if provided
    if leverage is not None:
        output = f"Leverage: {leverage}"
        if not console_only:
            print(output)
            log_to_file(trade.address, output)


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
        # 设置信号处理
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        print(f"Fetching full history for addresses, then refreshing every {self.interval} seconds. Press Ctrl+C to stop.")

        # Initial full history fetch & save to file
        try:
            for address in self.addresses:
                try:
                    # Fetch and save filled trades to file
                    if hasattr(self.info, "user_fills"):
                        all_fills = self.info.user_fills(address)
                    else:
                        all_fills = []

                    fills_sorted = sorted(all_fills, key=lambda f: int(f.get("time", 0))) if all_fills else []
                    label = LABELS.get(address)
                    header_label = f" ({label})" if label else ""
                    
                    # Save all fills to log file
                    header = f"\n{'='*60}\nFill History for {address}{header_label}: {len(fills_sorted)} entries\n{'='*60}"
                    log_to_file(address, header)
                    
                    for fill in fills_sorted:
                        trade = _fill_to_trade(fill, address)
                        # attempt to fetch leverage for this coin & address
                        try:
                            lev = None
                            state = self.info.user_state(address)
                            for ap in state.get("assetPositions", []):
                                pos = ap.get("position") or {}
                                if pos.get("coin") == trade.coin:
                                    l = pos.get("leverage")
                                    if l:
                                        lev = f"{l.get('type')} {l.get('value')}x"
                                    break
                        except Exception:
                            lev = None

                        print_trade(trade, console_only=True, leverage=lev)  # Save to file
                        if self.db:
                            try:
                                self.db.store_fill(fill)
                            except Exception as e:
                                print(f"Error storing fill to DB: {e}")
                    
                    # Fetch and save open orders to log file
                    if hasattr(self.info, "open_orders"):
                        open_orders = self.info.open_orders(address)
                    else:
                        open_orders = []

                    order_header = f"\n{'='*60}\nOpen Orders for {address}{header_label}: {len(open_orders)} orders\n{'='*60}"
                    log_to_file(address, order_header)
                    
                    for order in open_orders:
                        # log order
                        print_order(order, address, console_only=True)  # Save to file only
                        # also log leverage if available
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
                                log_to_file(address, f"Leverage: {lev}")
                        except Exception:
                            pass
                    
                    # Show latest 10 fills in console
                    latest_10_fills = fills_sorted[-10:] if len(fills_sorted) > 10 else fills_sorted
                    print(f"\n✓ Initialized ({address}{header_label}): {len(fills_sorted)} total fills | Latest 10 fills:")
                    print(f"{'='*60}")
                    for fill in latest_10_fills:
                        trade = _fill_to_trade(fill, address)
                        # fetch leverage for consistency
                        lev = None
                        try:
                            state = self.info.user_state(address)
                            for ap in state.get("assetPositions", []):
                                pos = ap.get("position") or {}
                                if pos.get("coin") == trade.coin:
                                    l = pos.get("leverage")
                                    if l:
                                        lev = f"{l.get('type')} {l.get('value')}x"
                                    break
                        except Exception:
                            lev = None
                        print_trade(trade, leverage=lev)  # Show in console
                except Exception as e:
                    print(f"Error fetching initial data for {address}: {e}")
        except KeyboardInterrupt:
            print("\nStopping polling before initial fetch.")
            self.cleanup()
            return

        # Periodic refresh - detect new fills and print updates or '未新开仓'
        try:
            while not self._stop_event:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

                        # Save full snapshot to log file for record
                        header = f"\n[{now_str}] Refreshed Fill History for {address}{header_label}: {len(fills_sorted)} entries"
                        log_to_file(address, header)
                        for fill in fills_sorted:
                            log_to_file(address, str(fill))
                            if self.db:
                                try:
                                    self.db.store_fill(fill)
                                except Exception as e:
                                    print(f"Error storing fill to DB: {e}")

                        # Save open orders to log file (do not print on console)
                        if hasattr(self.info, "open_orders"):
                            open_orders = self.info.open_orders(address)
                        else:
                            open_orders = []
                        order_header = f"\n[{now_str}] Open Orders for {address}{header_label}: {len(open_orders)} orders"
                        log_to_file(address, order_header)
                        for order in open_orders:
                            log_to_file(address, f"[{now_str}] {order}")

                        # Detect new fills since last_seen timestamp
                        last_seen_ms = self.last_seen.get(address, 0)
                        new_fills = [f for f in fills_sorted if int(f.get("time", 0)) > last_seen_ms]

                        if new_fills:
                            print(f"\n[{now_str}] 新开仓更新 ({address}{header_label}): {len(new_fills)} 条")
                            for fill in new_fills:
                                trade = _fill_to_trade(fill, address)
                                # fetch leverage for this address and coin
                                lev = None
                                try:
                                    state = self.info.user_state(address)
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
                            # update last_seen for this address
                            try:
                                self.last_seen[address] = max(int(f.get("time", 0)) for f in new_fills)
                            except Exception:
                                self.last_seen[address] = int(time.time() * 1000)
                        else:
                            print(f"\n[{now_str}] 未新开仓 ({address}{header_label})")

                        # Always print latest update time as the last line for this address
                        print(f"最后更新时间: {now_str}\n")
                    except Exception as e:
                        print(f"Error fetching refreshed data for {address}: {e}")
                        import traceback
                        traceback.print_exc()

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
    # List of addresses to monitor
    addresses: List[str] = [
        "0xdAe4DF7207feB3B350e4284C8eFe5f7DAc37f637",
        "0x4aab8988462923ca3cbaa7e94df0cc523817cd64"
    ]

    # Polling interval in seconds (3 minutes)
    interval = 180
    
    # Optional: Enable database storage
    # db_path = "trades.db"
    db_path = None  # Set to "trades.db" to enable database storage

    # Create and start monitor
    monitor = TradeMonitor(addresses=addresses, db_path=db_path, interval=interval)
    monitor.start()


if __name__ == "__main__":
    main()