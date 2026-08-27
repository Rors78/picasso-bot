#!/usr/bin/env python3
"""
PICASSO Fibonacci Trader - Professional Edition
===============================================
Automated Fibonacci pullback trading system

🇺🇸 USA EXCHANGE ONLY - BINANCE US - DO NOT CHANGE! 🇺🇸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  USER IS IN THE UNITED STATES!

  ONLY USE: Binance US (binanceus)
  NEVER USE: Binance.com, testnet, or international exchanges

  COMPLIANCE: Spot only, Long only, No leverage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Strategy:
- 1h BTC/USDT timeframe (bullish trends only)
- Double bottom confirmation at golden zone (0.5 retracement)
- Entry at 0.382 retracement after confirmation
- Stop loss at 0.618 retracement
- Take-profit targets: TP1 (1.0), TP2 (1.382), TP3 (1.618), TP4 (2.618)

Compliance:
- Spot trading only (no futures/derivatives)
- Long positions only (no shorting)
- No leverage
- US exchange compatible

Features:
- Automated position sizing ($1000 risk per trade default)
- Dynamic Fibonacci level calculation
- Volume confirmation (1.5x average)
- Profit tracking with lease model support
"""

import os, sys, time, json, csv
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean
from collections import deque

import ccxt
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich import box

APP = "PICASSO Fibonacci Trader v1.0"
BASE = Path(__file__).resolve().parent

# Files
KEYS_FILE = BASE / ".picasso_keys.json"
POS_FILE = BASE / "positions.json"
TRADES_CSV = BASE / "trades.csv"
STATS_FILE = BASE / "stats.json"
LICENSE_FILE = BASE / "license.json"  # For lease model

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🇺🇸 USA EXCHANGE ONLY - BINANCE US - HARDCODED 🇺🇸
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   USER IS IN THE UNITED STATES!
#
#   ONLY USE: ccxt.binanceus()
#   NEVER USE: ccxt.binance(), testnet, or international exchanges
#
#   COMPLIANCE: Spot only, Long only, No leverage, No shorting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PICASSO Configuration
# =======================================================

# Fibonacci Retracement Levels (for pullback/golden zone detection)
# ✅ CONFIGURED FROM USER'S VOICE EXPLANATION (December 31, 2025)
FIB_RETRACEMENT_ENTRY = float(os.environ.get("PICASSO_ENTRY", "0.382"))           # ✅ 0.382 - ENTRY LEVEL
FIB_RETRACEMENT_GOLDEN_ZONE = float(os.environ.get("PICASSO_GOLDEN_ZONE", "0.5")) # ✅ 0.5 - GOLD ZONE (double bounce)
FIB_RETRACEMENT_STOP_LOSS = float(os.environ.get("PICASSO_STOP_LOSS", "0.618"))   # ✅ 0.618 - STOP LOSS

# Fibonacci Extension Levels (for take-profit targets)
# ✅ CONFIGURED FROM USER'S SCREENSHOTS (December 31, 2025)
# User's TradingView shows negative extensions: -0.382, -0.618, -1.618
# These translate to standard extensions: 1.382, 1.618, 2.618
FIB_EXTENSION_TP1 = float(os.environ.get("PICASSO_TP1", "1.0"))      # ✅ 1.0 (swing high) - 100% winner
FIB_EXTENSION_TP2 = float(os.environ.get("PICASSO_TP2", "1.382"))    # ✅ 1.382 (-0.382 in TV) - 70% within hour
FIB_EXTENSION_TP3 = float(os.environ.get("PICASSO_TP3", "1.618"))    # ✅ 1.618 (-0.618 in TV) - Golden ratio
FIB_EXTENSION_TP4 = float(os.environ.get("PICASSO_TP4", "2.618"))    # ✅ 2.618 (-1.618 in TV) - Maximum extension

# Entry Settings
MAX_DIP_PERCENT = float(os.environ.get("PICASSO_MAX_DIP", "2.0"))    # Max 2% dip into golden zone
VOLUME_CONFIRMATION = float(os.environ.get("PICASSO_VOL_MULT", "1.5"))  # Volume spike on bounce
TOUCH_TOL_PCT = float(os.environ.get("PICASSO_TOUCH_TOL", "0.02"))   # Level-touch tolerance, fraction of swing range
TREND_SMA = int(os.environ.get("PICASSO_TREND_SMA", "200"))          # Bullish-only filter: close > SMA(n); 0 disables
SOUND_ON = (os.environ.get("PICASSO_SOUND", "1") == "1")             # Audible alerts on trade events

# Risk Management
RISK_AMOUNT_USD = float(os.environ.get("PICASSO_RISK_USD", "1000"))  # $1000 per trade (user's proven amount)
PAPER_MODE = (os.environ.get("PICASSO_PAPER", "1") == "1")  # Default paper mode

# Leverage - PAPER/BACKTEST SIMULATION ONLY.
# Binance US is spot-only: no venue this bot may use can execute leverage,
# so live mode is forced to 1x regardless of this setting.
# Multiplies position size; a liquidation price (entry * (1 - 1/lev)) is
# simulated and wipes the remaining margin if touched - checked before the stop.
LEVERAGE = max(1.0, float(os.environ.get("PICASSO_LEVERAGE", "1")))
if not PAPER_MODE and LEVERAGE > 1:
    LEVERAGE = 1.0  # live = spot = 1x, always

# Trading Pair
SYMBOL = os.environ.get("PICASSO_SYMBOL", "BTC/USDT")  # BTC only
TIMEFRAME = "1h"  # 1h charts only

# Scan interval
SCAN_INTERVAL = int(os.environ.get("PICASSO_SCAN_INTERVAL", "300"))  # 5 minutes

console = Console()

# ========== UTILITIES ==========

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def save_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def play_alert(kind):
    """Audible cue for trade events (Windows beeps, non-blocking). PICASSO_SOUND=0 disables."""
    if not SOUND_ON:
        return
    try:
        import winsound, threading
        seq = {
            "entry": ((880, 120), (1175, 160)),
            "tp": ((1319, 90), (1568, 140)),
            "stop": ((330, 350),),
            "liq": ((494, 120), (392, 120), (294, 300)),
        }.get(kind)
        if seq:
            threading.Thread(target=lambda: [winsound.Beep(f, d) for f, d in seq], daemon=True).start()
    except Exception:
        pass

# ========== FIBONACCI CALCULATIONS ==========

def calculate_fibonacci_levels(swing_low, swing_high):
    """
    Calculate all Fibonacci levels from swing low to swing high

    PICASSO FORMULA:
    - Retracement from swing high (pullback levels)
    - Entry at 0.382 (when bouncing up from gold zone)
    - Gold zone at 0.5 (double bounce confirmation)
    - Stop loss at 0.618 (below gold zone)
    - Extensions above swing high (take-profit targets)
    """
    range_size = swing_high - swing_low

    # Retracement levels (pullback from swing high)
    entry_price = swing_high - (FIB_RETRACEMENT_ENTRY * range_size)        # 0.382
    golden_zone_price = swing_high - (FIB_RETRACEMENT_GOLDEN_ZONE * range_size)  # 0.5
    stop_loss_price = swing_high - (FIB_RETRACEMENT_STOP_LOSS * range_size)      # 0.618

    # Extension levels (targets above swing high)
    tp1_price = swing_low + (FIB_EXTENSION_TP1 * range_size)
    tp2_price = swing_low + (FIB_EXTENSION_TP2 * range_size)
    tp3_price = swing_low + (FIB_EXTENSION_TP3 * range_size)
    tp4_price = swing_low + (FIB_EXTENSION_TP4 * range_size)

    return {
        "swing_low": swing_low,
        "swing_high": swing_high,
        "range": range_size,
        "entry": entry_price,           # 0.382 - ENTRY LEVEL
        "golden_zone": golden_zone_price,  # 0.5 - GOLD ZONE (double bounce)
        "stop_loss": stop_loss_price,      # 0.618 - STOP LOSS
        "tp1": tp1_price,                  # 1.0 ext (swing high) - TP1
        "tp2": tp2_price,                  # 1.382 ext - TP2
        "tp3": tp3_price,                  # 1.618 ext - TP3
        "tp4": tp4_price                   # 2.618 ext - TP4
    }

def find_swing_high_low(df, lookback=120):
    """Find swing high and swing low from recent price action"""
    if len(df) < lookback:
        return None, None

    recent = df.tail(lookback)
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())

    return swing_low, swing_high

# ========== PICASSO ENTRY LOGIC ==========

def check_pullback_entry(df, fib_levels):
    """
    Check if price has pulled back into golden zone and is bouncing back to entry

    PICASSO DOUBLE BOTTOM Logic (FROM USER'S VOICE EXPLANATION):
    1. Price pulls back to GOLD ZONE (0.5 retracement)
    2. FIRST TOUCH: Price touches gold zone (first bottom)
    3. SLIGHT BOUNCE: Price bounces up
    4. SECOND TOUCH: Price returns to gold zone (second bottom - DOUBLE BOTTOM!)
    5. BOUNCE UP: Price bounces from gold zone moving back toward swing high
    6. ENTRY TRIGGER: Price reaches 0.382 (entry level) after double bottom
    7. Volume confirmation required

    Entry is at 0.382, NOT at gold zone!
    Gold zone (0.5) is for double bottom CONFIRMATION only.

    Returns: True if entry signal, False otherwise
    """
    if len(df) < 25:  # Need more data for double bottom detection
        return False

    # STEP 0: Bullish regime only (promised by the docs since day one, now enforced)
    if TREND_SMA:
        sma = float(df["close"].tail(TREND_SMA).astype(float).mean())
        if float(df.iloc[-1]["close"]) <= sma:
            return False

    current = df.iloc[-1]
    previous = df.iloc[-2]

    close_price = float(current["close"])
    prev_close = float(previous["close"])
    current_vol = float(current["volume"])

    # Calculate average volume
    vol_series = df["volume"].tail(20).astype(float)
    avg_vol = float(vol_series.mean())

    entry_level = fib_levels["entry"]        # 0.382
    golden_zone = fib_levels["golden_zone"]  # 0.5
    stop_loss = fib_levels["stop_loss"]      # 0.618

    # Tolerance for level detection: a fraction of the SWING RANGE, not of price.
    # (2% of price at BTC levels is wider than the gap between fib levels,
    # which made every candle low count as a gold-zone "touch".)
    entry_tolerance = fib_levels["range"] * TOUCH_TOL_PCT
    golden_tolerance = fib_levels["range"] * TOUCH_TOL_PCT

    # STEP 1: Check for DOUBLE BOTTOM at gold zone (0.5) in recent history
    recent_lows = df["low"].tail(15).astype(float)
    touches_at_golden = 0
    for low in recent_lows:
        if abs(low - golden_zone) <= golden_tolerance:
            touches_at_golden += 1

    # Need at least 2 touches for double bottom confirmation
    double_bottom_confirmed = touches_at_golden >= 2

    # STEP 2: Price should now be AT or ABOVE entry level (0.382)
    # This means price has bounced UP from gold zone and reached entry
    at_entry_level = close_price >= (entry_level - entry_tolerance)
    below_swing_high = close_price <= fib_levels["swing_high"]

    # STEP 3: Price is bouncing UP (bullish momentum)
    bouncing_up = close_price > prev_close

    # STEP 4: Volume confirmation (spike on the move)
    volume_ok = current_vol >= avg_vol * VOLUME_CONFIRMATION

    # STEP 5: Price hasn't fallen below stop loss
    above_stop = close_price > stop_loss

    # STEP 6: Check that price was recently AT gold zone (in last 5-10 candles)
    # This ensures we're entering on the bounce from double bottom, not random price
    recent_was_at_golden = False
    for i in range(-10, 0):  # Last 10 candles
        if i >= -len(df):
            candle_low = float(df.iloc[i]["low"])
            if abs(candle_low - golden_zone) <= golden_tolerance:
                recent_was_at_golden = True
                break

    # STEP 7: Max-dip guard (documented since day one, previously never enforced):
    # a plunge more than MAX_DIP_PERCENT below the gold zone is a breakdown, not a pullback
    dip_floor = golden_zone * (1 - MAX_DIP_PERCENT / 100.0)
    dip_ok = float(df["low"].tail(10).astype(float).min()) >= dip_floor

    # ALL CONDITIONS for entry:
    # 1. Double bottom at gold zone confirmed ✓
    # 2. Price recently was at gold zone ✓
    # 3. Price now at entry level (0.382) ✓
    # 4. Price bouncing up ✓
    # 5. Volume spike ✓
    # 6. Above stop loss ✓
    # 7. No breakdown below the gold zone (max dip) ✓
    if (double_bottom_confirmed and recent_was_at_golden and at_entry_level and
        below_swing_high and bouncing_up and volume_ok and above_stop and dip_ok):
        log_event("[bold yellow]🎯 DOUBLE BOTTOM at GOLD ZONE confirmed![/bold yellow]")
        log_event(f"[bold green]🚀 ENTRY signal at {FIB_RETRACEMENT_ENTRY} level (${close_price:,.2f})![/bold green]")
        return True

    return False

# ========== POSITION MANAGEMENT ==========

def calculate_position_size(entry_price, stop_loss, risk_amount):
    """
    Calculate position size based on risk amount

    User's proven method: $1000 risk per trade
    Position size = risk_amount / (entry_price - stop_loss)
    """
    risk_per_unit = entry_price - stop_loss
    if risk_per_unit <= 0:
        return 0

    position_size = risk_amount / risk_per_unit
    return position_size

# ========== PROFIT TRACKING (for 10% lease model) ==========

def track_trade_profit(trade_profit, customer_id="default"):
    """
    Track profit for lease model

    Lease Model:
    - First $100 of 10% share = refund to customer
    - After $100 recouped = 10% to vendor
    """
    license_data = load_json(LICENSE_FILE, {
        "customer_id": customer_id,
        "initial_fee": 100.0,
        "refund_progress": 0.0,
        "total_profits": 0.0,
        "vendor_earnings": 0.0,
        "breakeven": False
    })

    # Calculate 10% share
    share_amount = trade_profit * 0.10

    # Update total profits
    license_data["total_profits"] += trade_profit

    # Determine where the share goes
    if not license_data["breakeven"]:
        # Customer still needs to recoup $100
        remaining_refund = 100.0 - license_data["refund_progress"]

        if share_amount >= remaining_refund:
            # Customer fully recoups, breakeven achieved
            license_data["refund_progress"] = 100.0
            license_data["breakeven"] = True

            # Excess goes to vendor
            vendor_portion = share_amount - remaining_refund
            license_data["vendor_earnings"] += vendor_portion

            log_event("[bold green]🎉 CUSTOMER BREAKEVEN ACHIEVED! Vendor earnings start now.[/bold green]")
        else:
            # All share goes to customer refund
            license_data["refund_progress"] += share_amount
            log_event(f"[cyan]Refund progress: ${license_data['refund_progress']:.2f} / $100.00[/cyan]")
    else:
        # Customer already recouped, all share goes to vendor
        license_data["vendor_earnings"] += share_amount
        log_event(f"[bold green]💰 Vendor earnings: +${share_amount:.2f} (Total: ${license_data['vendor_earnings']:.2f})[/bold green]")

    save_json(LICENSE_FILE, license_data)
    return license_data

# ========== TRADE RECORDING ==========

def record_trade(event, price, size, pnl):
    """Append one row to trades.csv - every event, wins AND losses."""
    is_new = not TRADES_CSV.exists()
    with open(TRADES_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["time", "event", "price", "size", "pnl"])
        w.writerow([now_str(), event, f"{price:.2f}", f"{size:.6f}", f"{pnl:.2f}"])

def update_stats(realized):
    """Book one closed trade into stats.json. Gross P/L; losses count."""
    stats = load_json(STATS_FILE, {"trades": 0, "wins": 0, "losses": 0, "gross_pl": 0.0})
    stats["trades"] += 1
    stats["wins" if realized > 0 else "losses"] += 1
    stats["gross_pl"] += realized
    save_json(STATS_FILE, stats)
    return stats

# ========== DISPLAY (full-screen Rich TUI) ==========

EVENTS = deque(maxlen=100)

def log_event(msg):
    """Append a timestamped line to the on-screen event log."""
    EVENTS.appendleft(f"[dim]{now_str()}[/dim] {msg}")

def market_metrics(df, fib_levels):
    """Display-only snapshot of the entry conditions (mirrors check_pullback_entry)."""
    try:
        vol_series = df["volume"].tail(20).astype(float)
        avg_vol = float(vol_series.mean()) or 1.0
        cur_vol = float(df.iloc[-1]["volume"])
        golden = fib_levels["golden_zone"]
        tol = fib_levels["range"] * TOUCH_TOL_PCT  # must mirror check_pullback_entry's tolerance
        lows = df["low"].tail(15).astype(float)
        touches = sum(1 for lo in lows if abs(lo - golden) <= tol)
        bouncing = float(df.iloc[-1]["close"]) > float(df.iloc[-2]["close"])
        sma = float(df["close"].tail(TREND_SMA).astype(float).mean()) if TREND_SMA else 0.0
        bullish = (not TREND_SMA) or float(df.iloc[-1]["close"]) > sma
        return {"vol_ratio": cur_vol / avg_vol, "touches": touches, "bouncing": bouncing,
                "bullish": bullish, "sma": sma}
    except Exception:
        return {"vol_ratio": 0.0, "touches": 0, "bouncing": False, "bullish": False, "sma": 0.0}

def build_header():
    mode = "[bold black on green] PAPER [/]" if PAPER_MODE else "[bold white on red] LIVE [/]"
    lev = f"   [bold white on red] {LEVERAGE:.0f}x SIM [/]" if LEVERAGE > 1 else ""
    return Panel(
        Align.center(
            f"[bold cyan]🎨 {APP}[/]   [white]{SYMBOL} · {TIMEFRAME} · ${RISK_AMOUNT_USD:.0f} risk/trade[/]   {mode}{lev}"
        ),
        border_style="cyan", box=box.HEAVY,
    )

def build_fib_table(fib, price):
    table = Table(box=box.ROUNDED, expand=True, border_style="cyan",
                  title="📐 Fibonacci Ladder", title_style="bold cyan")
    # Column priority: Level and Price must never truncate; Role absorbs any squeeze.
    table.add_column("Level", style="yellow", no_wrap=True, min_width=17)
    table.add_column("Price", justify="right", style="bold green", no_wrap=True, min_width=10)
    table.add_column("", no_wrap=True, width=1)
    table.add_column("Role", style="dim", no_wrap=True, overflow="ellipsis")

    # Colors mirror the operator's TradingView fib tool:
    # 0.382 white · 0.5/0.618 yellow · extensions green · -1.618 bright green
    rows = [
        (f"TP4  ({FIB_EXTENSION_TP4})", fib["tp4"], "max ext", "bold bright_green"),
        (f"TP3  ({FIB_EXTENSION_TP3})", fib["tp3"], "golden ratio", "green"),
        (f"TP2  ({FIB_EXTENSION_TP2})", fib["tp2"], "70% in 1hr", "green"),
        (f"TP1  ({FIB_EXTENSION_TP1})", fib["tp1"], "swing high", "green"),
        ("Swing High", fib["swing_high"], "0.0 retrace", "green"),
        (f"ENTRY ({FIB_RETRACEMENT_ENTRY})", fib["entry"], "🚀 entry", "bold white"),
        (f"GOLD ZONE ({FIB_RETRACEMENT_GOLDEN_ZONE})", fib["golden_zone"], "🎯 dbl bottom", "bold yellow"),
        (f"STOP ({FIB_RETRACEMENT_STOP_LOSS})", fib["stop_loss"], "🛑 stop", "bold yellow"),
        ("Swing Low", fib["swing_low"], "1.0 retrace", "white"),
    ]
    nearest = None
    if price:
        nearest = min(range(len(rows)), key=lambda i: abs(rows[i][1] - price))
    for i, (name, val, role, style) in enumerate(rows):
        marker = "[bold magenta]◀[/]" if i == nearest else ""
        table.add_row(f"[{style}]{name}[/]", f"${val:,.2f}", marker, role)
    return table

def build_chart(state):
    """Bar chart of recent 1h closes with the fib levels overlaid as lines."""
    closes = state.get("closes") or []
    fib = state.get("fib")
    if not closes:
        return Panel(Align.center("[dim]waiting for candles...[/]"), border_style="cyan", box=box.ROUNDED)

    # Adapt to the actual pane: left column is ~half the terminal, minus borders
    W = max(24, min(160, console.size.width // 2 - 6))
    H = 9
    data = closes[-W:]
    lo, hi = min(data), max(data)
    span = (hi - lo) or 1.0
    heights = [1 + (c - lo) / span * (H - 1) for c in data]

    # Which chart row each fib level lands on (only levels inside the window)
    level_rows = {}
    if fib:
        # TV palette: entry white, gold zone + stop yellow
        for key, color in (("entry", "white"), ("golden_zone", "yellow"), ("stop_loss", "yellow")):
            v = fib[key]
            if lo <= v <= hi:
                level_rows.setdefault(round(1 + (v - lo) / span * (H - 1)), color)

    lines = []
    for row in range(H, 0, -1):
        line_color = level_rows.get(row)
        chars = []
        for j, h in enumerate(heights):
            if h >= row:
                ch = "█"
            elif h >= row - 0.5:
                ch = "▄"
            else:
                ch = f"[dim {line_color}]┄[/]" if line_color else " "
                chars.append(ch)
                continue
            if j == len(heights) - 1:
                ch = f"[bold magenta]{ch}[/]"
            else:
                ch = f"[cyan]{ch}[/]"
            chars.append(ch)
        lines.append("".join(chars))

    title = f"📈 {SYMBOL} · last {len(data)}h"
    sub = f"[dim]hi[/] [green]${hi:,.0f}[/] · [dim]lo[/] [red]${lo:,.0f}[/] · [dim]now[/] [bold white]${data[-1]:,.0f}[/]"
    body = Text.from_markup("\n".join(lines))
    body.no_wrap = True
    body.overflow = "crop"
    return Panel(body, title=title, subtitle=sub, border_style="cyan", box=box.ROUNDED)

def build_status(state):
    fib = state.get("fib")
    price = state.get("price")
    metrics = state.get("metrics") or {}
    position = state.get("position")

    grid = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    grid.add_column(style="white", no_wrap=True)
    grid.add_column(justify="right")

    src = "[green]● live[/]" if state.get("price_live") else "[yellow]● candle[/]"
    grid.add_row("[bold]BTC Price[/]", f"[bold white]${price:,.2f}[/] {src}" if price else "—")
    if TREND_SMA:
        if metrics.get("bullish"):
            grid.add_row(f"Trend (SMA{TREND_SMA})", "[bold green]BULL[/]")
        else:
            grid.add_row(f"Trend (SMA{TREND_SMA})", f"[bold red]BEAR — entries off[/] [dim]${metrics.get('sma', 0):,.0f}[/]")

    if fib and price:
        for label, key in (("→ Entry", "entry"), ("→ Gold Zone", "golden_zone"), ("→ Stop", "stop_loss")):
            delta = price - fib[key]
            pct = delta / price * 100
            color = "green" if delta >= 0 else "red"
            grid.add_row(label, f"[{color}]{'+' if delta >= 0 else ''}{delta:,.2f}  ({pct:+.2f}%)[/]")

    grid.add_row("", "")
    touches = metrics.get("touches", 0)
    t_style = "bold green" if touches >= 2 else "yellow"
    grid.add_row("Gold-zone touches", f"[{t_style}]{touches}/2[/]")
    vol = metrics.get("vol_ratio", 0.0)
    v_style = "bold green" if vol >= VOLUME_CONFIRMATION else "yellow"
    grid.add_row("Volume vs 20-avg", f"[{v_style}]{vol:.2f}x[/] [dim](need {VOLUME_CONFIRMATION}x)[/]")
    grid.add_row("Bouncing up", "[bold green]YES[/]" if metrics.get("bouncing") else "[dim]no[/]")

    if position:
        rem = position.get("remaining", position["size"])
        banked = position.get("realized", 0.0)
        upnl = (price - position["entry"]) * rem if price else 0.0
        u_style = "bold green" if upnl >= 0 else "bold red"
        grid.add_row("", "")
        grid.add_row("[bold magenta]POSITION[/]", "")
        grid.add_row("Entry", f"${position['entry']:,.2f}")
        grid.add_row("Size left", f"{rem:.4f} / {position['size']:.4f} BTC")
        at_be = position["stop_loss"] >= position["entry"]
        grid.add_row("Stop", f"${position['stop_loss']:,.2f}" + (" [cyan](breakeven)[/]" if at_be else ""))
        if position.get("leverage", 1.0) > 1:
            grid.add_row("Leverage", f"[bold red]{position['leverage']:.0f}x · liq ${position.get('liq', 0):,.2f}[/]")
        grid.add_row("Banked", f"[green]{banked:+,.2f} USD[/]" if banked else "[dim]0.00 USD[/]")
        grid.add_row("Unrealized P/L", f"[{u_style}]{upnl:+,.2f} USD[/]")
        tps = "  ".join(
            f"[green]TP{i}✓[/]" if position.get(f"tp{i}_hit") else f"[dim]TP{i}·[/]"
            for i in (1, 2, 3, 4)
        )
        grid.add_row("Targets", tps)
        title, style = "📊 Market — POSITION OPEN", "magenta"
    else:
        title, style = "📊 Market — waiting for setup", "cyan"

    return Panel(grid, title=title, border_style=style, box=box.ROUNDED)

def build_stats(state):
    stats = state.get("stats") or {"trades": 0, "wins": 0, "losses": 0, "gross_pl": 0.0}
    up = int(time.time() - state.get("started", time.time()))
    h, m = divmod(up // 60, 60)

    grid = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    grid.add_column(style="white", no_wrap=True)
    grid.add_column(justify="right", no_wrap=True)

    grid.add_row("[bold cyan]— Session —[/]", "")
    grid.add_row("Uptime", f"{h}h {m:02d}m")
    grid.add_row("Scans", str(state.get("scans", 0)))
    grid.add_row("Entries", str(state.get("session_entries", 0)))
    spl = state.get("session_pl", 0.0)
    grid.add_row("Realized P/L", f"[{'bold green' if spl >= 0 else 'bold red'}]{spl:+,.2f} USD[/]")

    grid.add_row("[bold cyan]— Lifetime —[/]", "")
    grid.add_row("Closed trades", str(stats["trades"]))
    wr = (stats["wins"] / stats["trades"] * 100) if stats["trades"] else None
    grid.add_row("Win rate", f"{wr:.1f}%  ({stats['wins']}W/{stats['losses']}L)" if wr is not None else "[dim]no trades yet[/]")
    gpl = stats["gross_pl"]
    grid.add_row("Gross P/L", f"[{'bold green' if gpl >= 0 else 'bold red'}]{gpl:+,.2f} USD[/]")

    closed = list(state.get("closed") or [])
    if closed:
        grid.add_row("[bold cyan]— Last closes —[/]", "")
        for c in closed[-3:][::-1]:
            style = "green" if c["pnl"] > 0 else "red"
            grid.add_row(f"[dim]{c['when']}[/] {c['exit']}", f"[{style}]{c['pnl']:+,.0f}[/]")

    return Panel(grid, title="📜 Stats", border_style="cyan", box=box.ROUNDED)

def build_footer(state):
    remaining = state.get("countdown", 0)
    mm, ss = divmod(max(0, remaining), 60)
    filled = int((1 - remaining / max(1, SCAN_INTERVAL)) * 18)
    bar = "█" * filled + "░" * (18 - filled)
    body = Text.from_markup("\n".join(list(EVENTS)[:8]) or "[dim]no events yet[/]")
    return Panel(
        body,
        title="🖊  Events",
        subtitle=f"[cyan]{bar}[/] [bold cyan]next scan {mm:02d}:{ss:02d}[/]  ·  [dim]Ctrl+C to stop[/]",
        border_style="blue", box=box.ROUNDED,
    )

def build_screen(state):
    layout = Layout()
    layout.split_column(
        Layout(build_header(), name="header", size=3),
        Layout(name="body", ratio=2),
        Layout(build_footer(state), name="footer", size=10),
    )
    fib = state.get("fib")
    if fib:
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        layout["left"].split_column(
            Layout(build_fib_table(fib, state.get("price")), name="fib", size=14),
            Layout(build_chart(state), name="chart"),
        )
        # Stats shrinks before status does on short windows
        stats_size = 15 if console.size.height >= 42 else max(7, console.size.height - 25)
        layout["right"].split_column(
            Layout(build_status(state), name="status"),
            Layout(build_stats(state), name="stats", size=stats_size),
        )
    else:
        layout["body"].update(Panel(Align.center("[cyan]⏳ Fetching first candles from Binance US...[/]"),
                                    border_style="cyan"))
    return layout

# ========== EXCHANGE CONNECTION ==========

def read_keys():
    if KEYS_FILE.exists():
        return load_json(KEYS_FILE, {})

    if PAPER_MODE:
        # Paper mode only reads public market data - no account needed
        console.print("[yellow]No API keys found - paper mode, using public data only[/yellow]")
        return {"apiKey": "", "secret": ""}

    console.print(Panel.fit(
        "[bold]Enter Binance.US API Keys[/bold]\n(saved to .picasso_keys.json)",
        style="cyan"
    ))
    api_key = console.input("API Key: ").strip()
    api_secret = console.input("API Secret: ").strip()

    keys = {"apiKey": api_key, "secret": api_secret}
    save_json(KEYS_FILE, keys)
    return keys

def connect_exchange(live=True):
    """
    Connect to Binance US exchange

    🇺🇸 USA EXCHANGE ONLY - BINANCE US 🇺🇸
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    HARDCODED TO BINANCE US (binanceus)

    DO NOT CHANGE TO:
    - binance (international - BLOCKED in USA)
    - Any testnet/sandbox (Binance US has no public testnet)
    - Any other exchange without explicit user approval

    PAPER MODE: Uses real API (read-only) - NO sandbox!
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    keys = read_keys()

    # 🇺🇸 BINANCE US ONLY - DO NOT CHANGE! 🇺🇸
    ex = ccxt.binanceus({
        "apiKey": keys["apiKey"],
        "secret": keys["secret"],
        "enableRateLimit": True,
        "timeout": 20000,
        "options": {
            "defaultType": "spot",  # SPOT ONLY (USA compliant)
            "adjustForTimeDifference": True
        }
    })

    try:
        ex.load_time_difference()
    except Exception:
        pass

    # ⚠️ DO NOT USE SANDBOX MODE! ⚠️
    # Binance US does not have a public testnet
    # Paper mode is handled by the PAPER_MODE flag (no actual orders placed)
    # if not live:
    #     ex.set_sandbox_mode(True)  # ← DISABLED - Binance US has no testnet!

    return ex

# ========== BACKTEST ==========

def fetch_history(ex, days):
    """Fetch `days` of 1h candles plus lookback, paginated."""
    ms_per = 3600 * 1000
    need = days * 24 + 130
    since = ex.milliseconds() - need * ms_per
    rows = {}
    while True:
        batch = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        for r in batch:
            rows[r[0]] = r
        if len(batch) < 1000:
            break
        since = batch[-1][0] + ms_per
    df = pd.DataFrame(sorted(rows.values()), columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df

def simulate(df):
    """Run the strategy over a candle DataFrame using current module params.

    Scaled exits (25% per TP), stop to breakeven after TP1, leverage + liq.
    Only completed 1h bars exist here: TPs fill at the bar HIGH, stops at the
    bar LOW, liq checked first, then stop, then TPs (conservative ordering).
    Returns (trades, max_drawdown).
    """
    position, trades = None, []
    equity = peak = max_dd = 0.0

    def close_out(label, exit_price, i):
        nonlocal position, equity, peak, max_dd
        if label == "LIQ":
            tail = -position["entry"] * position["remaining"] / position["leverage"]
        else:
            tail = (exit_price - position["entry"]) * position["remaining"]
        total = position["realized"] + tail
        trades.append({
            "when": datetime.fromtimestamp(df.iloc[position["entry_i"]]["timestamp"] / 1000, tz=timezone.utc),
            "entry": position["entry"], "exit": label, "exit_price": exit_price,
            "tps": sum(1 for k in (1, 2, 3, 4) if position[f"tp{k}_hit"]),
            "pnl": total, "bars": i - position["entry_i"],
        })
        equity += total
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        position = None

    for i in range(120, len(df)):
        window = df.iloc[max(0, i - 199): i + 1]
        bar = df.iloc[i]

        if position:
            hi, lo = float(bar["high"]), float(bar["low"])
            if position["leverage"] > 1 and lo <= position["liq"]:
                close_out("LIQ", position["liq"], i)
                continue
            if lo <= position["stop_loss"]:
                close_out("BE-STOP" if position["stop_loss"] >= position["entry"] else "STOP",
                          position["stop_loss"], i)
                continue
            for k in (1, 2, 3, 4):
                tp = position[f"tp{k}"]
                if hi >= tp and not position[f"tp{k}_hit"]:
                    position[f"tp{k}_hit"] = True
                    s = min(position["size"] * 0.25 if k < 4 else position["remaining"],
                            position["remaining"])
                    position["remaining"] -= s
                    position["realized"] += (tp - position["entry"]) * s
                    if k == 1:
                        position["stop_loss"] = max(position["stop_loss"], position["entry"])
            if position and (position["tp4_hit"] or position["remaining"] <= 1e-12):
                close_out("TP4", position["tp4"], i)
        else:
            swing_low, swing_high = find_swing_high_low(window)
            if swing_low is None:
                continue
            fib = calculate_fibonacci_levels(swing_low, swing_high)
            if check_pullback_entry(window, fib):
                entry, stop = fib["entry"], fib["stop_loss"]
                size = calculate_position_size(entry, stop, RISK_AMOUNT_USD) * LEVERAGE
                position = {
                    "entry": entry, "stop_loss": stop, "size": size,
                    "remaining": size, "realized": 0.0, "leverage": LEVERAGE,
                    "liq": entry * (1 - 1 / LEVERAGE) if LEVERAGE > 1 else 0.0,
                    "tp1": fib["tp1"], "tp2": fib["tp2"], "tp3": fib["tp3"], "tp4": fib["tp4"],
                    "tp1_hit": False, "tp2_hit": False, "tp3_hit": False, "tp4_hit": False,
                    "entry_i": i,
                }

    if position:
        close_out("EOD", float(df.iloc[-1]["close"]), len(df) - 1)
    return trades, max_dd

def run_backtest(days=60):
    """Replay the exact live entry/exit logic over historical candles."""
    lev_note = f" · {LEVERAGE:.0f}x SIM" if LEVERAGE > 1 else ""
    console.print(f"\n[bold cyan]🎨 PICASSO BACKTEST — {SYMBOL} {TIMEFRAME}, last {days} days{lev_note}[/bold cyan]")
    ex = ccxt.binanceus({"enableRateLimit": True, "timeout": 20000})
    df = fetch_history(ex, days)
    console.print(f"[dim]{len(df)} candles · "
                  f"{datetime.fromtimestamp(df.iloc[0]['timestamp']/1000, tz=timezone.utc):%Y-%m-%d} → "
                  f"{datetime.fromtimestamp(df.iloc[-1]['timestamp']/1000, tz=timezone.utc):%Y-%m-%d}[/dim]\n")
    trades, max_dd = simulate(df)

    # ---- Report ----
    if not trades:
        console.print("[yellow]No entries triggered in this window — the setup never completed "
                      "(double bottom + volume spike + bounce to entry).[/yellow]")
        return

    t = Table(box=box.ROUNDED, border_style="cyan", title="Trades")
    for col, j in (("Entered (UTC)", "left"), ("Entry", "right"), ("Exit", "left"),
                   ("Exit $", "right"), ("TPs", "center"), ("Bars", "right"), ("P/L", "right")):
        t.add_column(col, justify=j)
    for tr in trades[-25:]:
        style = "green" if tr["pnl"] > 0 else "red"
        t.add_row(f"{tr['when']:%m-%d %H:%M}", f"${tr['entry']:,.2f}", tr["exit"],
                  f"${tr['exit_price']:,.2f}", f"{tr['tps']}/4", str(tr["bars"]),
                  f"[{style}]{tr['pnl']:+,.2f}[/]")
    console.print(t)

    wins = [tr for tr in trades if tr["pnl"] > 0]
    gross = sum(tr["pnl"] for tr in trades)
    tp_rate = lambda k: sum(1 for tr in trades if tr["tps"] >= k) / len(trades) * 100
    g_style = "bold green" if gross >= 0 else "bold red"
    console.print(Panel.fit(
        f"[bold]Trades:[/] {len(trades)}   [bold]Win rate:[/] {len(wins)/len(trades)*100:.1f}% "
        f"({len(wins)}W/{len(trades)-len(wins)}L)\n"
        f"[bold]Gross P/L:[/] [{g_style}]{gross:+,.2f} USD[/]   "
        f"[bold]Avg/trade:[/] {gross/len(trades):+,.2f}   [bold]Max drawdown:[/] ${max_dd:,.2f}\n"
        f"[bold]TP reach:[/] TP1 {tp_rate(1):.0f}% · TP2 {tp_rate(2):.0f}% · "
        f"TP3 {tp_rate(3):.0f}% · TP4 {tp_rate(4):.0f}%\n"
        f"[dim]Scaled exits 25%/TP, breakeven stop after TP1; exits via bar high/low "
        f"(liq, then stop, then TPs). Risk ${RISK_AMOUNT_USD:.0f}/trade at {LEVERAGE:.0f}x, "
        f"gross P/L, no fees.[/dim]",
        title="📜 Backtest Summary", border_style="cyan",
    ))

# ========== TUNER ==========

def run_tune(days=90):
    """Grid-search entry filters over one fetched history. 1h timeframe is
    fixed by design - only volume confirmation and touch tolerance vary.
    Tuned at 1x leverage so results measure signal quality, not sizing."""
    global VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE
    console.print(f"\n[bold cyan]🎨 PICASSO TUNE — {SYMBOL} {TIMEFRAME}, last {days} days[/bold cyan]")
    ex = ccxt.binanceus({"enableRateLimit": True, "timeout": 20000})
    df = fetch_history(ex, days)
    console.print(f"[dim]{len(df)} candles fetched — sweeping volume x tolerance grid at 1x[/dim]\n")

    saved = (VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE)
    LEVERAGE = 1.0
    results = []
    try:
        for vol in (1.0, 1.2, 1.5, 2.0):
            for tol in (0.01, 0.02, 0.03, 0.05):
                VOLUME_CONFIRMATION, TOUCH_TOL_PCT = vol, tol
                trades, max_dd = simulate(df)
                wins = sum(1 for t in trades if t["pnl"] > 0)
                gross = sum(t["pnl"] for t in trades)
                results.append({"vol": vol, "tol": tol, "n": len(trades), "wins": wins,
                                "gross": gross, "dd": max_dd})
    finally:
        VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE = saved

    results.sort(key=lambda r: r["gross"], reverse=True)
    t = Table(box=box.ROUNDED, border_style="cyan", title="Parameter Sweep (sorted by gross P/L)")
    for col, j in (("Vol mult", "right"), ("Touch tol", "right"), ("Trades", "right"),
                   ("Win rate", "right"), ("Gross P/L", "right"), ("Max DD", "right")):
        t.add_column(col, justify=j)
    for r in results:
        wr = f"{r['wins']/r['n']*100:.0f}%" if r["n"] else "—"
        style = "green" if r["gross"] > 0 else "red"
        mark = " ◀" if (r["vol"], r["tol"]) == (saved[0], saved[1]) else ""
        t.add_row(f"{r['vol']:.1f}x{mark}", f"{r['tol']:.2f}", str(r["n"]), wr,
                  f"[{style}]{r['gross']:+,.0f}[/]", f"${r['dd']:,.0f}")
    console.print(t)

    solid = [r for r in results if r["n"] >= 5]
    if solid:
        best = solid[0]
        console.print(Panel.fit(
            f"[bold]Best with ≥5 trades:[/] volume [bold cyan]{best['vol']:.1f}x[/] · "
            f"tolerance [bold cyan]{best['tol']:.2f}[/]  →  {best['n']} trades, "
            f"{best['wins']}/{best['n']} wins, gross [bold]{best['gross']:+,.0f}[/]\n"
            f"[dim]Apply via: set PICASSO_VOL_MULT={best['vol']} & set PICASSO_TOUCH_TOL={best['tol']}\n"
            f"One-window sweep — treat as a pointer, not a promise (overfit risk).[/dim]",
            title="🔧 Recommendation", border_style="green"))
    else:
        console.print("[yellow]No parameter combo produced ≥5 trades — not enough signal to tune on.[/yellow]")

# ========== MAIN LOOP ==========

def main():
    """Main PICASSO trading loop - full-screen auto-fit Rich TUI"""

    # Connect to exchange
    try:
        ex = connect_exchange(live=not PAPER_MODE)
        console.print("[green]✅ Connected to Binance US[/green]")
    except Exception as e:
        console.print(f"[red]❌ Exchange connection failed: {e}[/red]")
        return

    # Load existing position if any (migrate pre-scaled-exit positions)
    position = load_json(POS_FILE, None)
    if position:
        position.setdefault("remaining", position["size"])
        position.setdefault("realized", 0.0)
        position.setdefault("leverage", 1.0)
        position.setdefault("liq", 0.0)
        log_event(f"[magenta]Resumed open position (entry ${position['entry']:,.2f})[/magenta]")
    if LEVERAGE > 1:
        log_event(f"[bold red]⚠ {LEVERAGE:.0f}x leverage SIMULATION — paper only; live mode is always spot 1x[/bold red]")
    log_event(f"[cyan]PICASSO online — watching {SYMBOL} {TIMEFRAME} for double bottom at gold zone[/cyan]")

    state = {"fib": None, "price": None, "price_live": False, "metrics": None,
             "position": position, "countdown": SCAN_INTERVAL,
             "started": time.time(), "scans": 0, "session_entries": 0, "session_pl": 0.0,
             "closes": None, "closed": deque(maxlen=20),
             "stats": load_json(STATS_FILE, {"trades": 0, "wins": 0, "losses": 0, "gross_pl": 0.0})}

    try:
        with Live(build_screen(state), console=console, screen=True, refresh_per_second=4) as live:
            while True:
                try:
                    # ---- SCAN: fetch 1h candles, recompute levels, run trade logic ----
                    state["scans"] += 1
                    ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200)
                    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

                    swing_low, swing_high = find_swing_high_low(df)

                    if swing_low is None or swing_high is None:
                        log_event("[yellow]⚠ Not enough data for swing detection[/yellow]")
                    else:
                        fib_levels = calculate_fibonacci_levels(swing_low, swing_high)
                        current_price = float(df.iloc[-1]["close"])
                        state["fib"] = fib_levels
                        state["price"] = current_price
                        state["price_live"] = False
                        state["metrics"] = market_metrics(df, fib_levels)
                        state["closes"] = [float(c) for c in df["close"].tail(120)]

                        if position:
                            entry = position["entry"]
                            lev = position.get("leverage", 1.0)

                            # Liquidation first (leveraged sims): past liq the margin
                            # is gone before any stop order could save you
                            liq = position.get("liq", 0.0)
                            if lev > 1 and liq > 0 and current_price <= liq:
                                margin = entry * position["remaining"] / lev
                                realized = -margin
                                total = position.get("realized", 0.0) + realized
                                state["session_pl"] += realized
                                record_trade("LIQUIDATED", liq, position["remaining"], realized)
                                state["stats"] = update_stats(total)
                                state["closed"].append({"when": now_str()[5:16], "exit": "LIQ", "pnl": total})
                                log_event(f"[bold white on red]💀 LIQUIDATED at ${liq:,.2f} — margin wiped: ${realized:,.2f}[/bold white on red]")
                                play_alert("liq")
                                position = None
                                save_json(POS_FILE, None)

                            if position:
                                # Scaled exits: 25% of the position at each TP
                                for i in (1, 2, 3, 4):
                                    tp = position[f"tp{i}"]
                                    if current_price >= tp and not position.get(f"tp{i}_hit"):
                                        position[f"tp{i}_hit"] = True
                                        slice_size = position["size"] * 0.25 if i < 4 else position["remaining"]
                                        slice_size = min(slice_size, position["remaining"])
                                        realized = (tp - entry) * slice_size
                                        position["remaining"] -= slice_size
                                        position["realized"] = position.get("realized", 0.0) + realized
                                        state["session_pl"] += realized
                                        track_trade_profit(realized)
                                        record_trade(f"TP{i}", tp, slice_size, realized)
                                        log_event(f"[bold green]{'🎯' * i} TP{i} — sold {slice_size:.4f} BTC at ${tp:,.2f}, banked ${realized:,.2f}[/bold green]")
                                        play_alert("tp")
                                        if i == 1 and position["stop_loss"] < entry:
                                            position["stop_loss"] = entry
                                            log_event("[cyan]🛡 Stop moved to breakeven[/cyan]")
                                        save_json(POS_FILE, position)
                                        if i == 4 or position["remaining"] <= 1e-12:
                                            total = position["realized"]
                                            log_event(f"[bold magenta]🎨 PICASSO COMPLETE — trade banked ${total:,.2f}[/bold magenta]")
                                            state["stats"] = update_stats(total)
                                            state["closed"].append({"when": now_str()[5:16], "exit": "TP4", "pnl": total})
                                            position = None
                                            save_json(POS_FILE, None)
                                            break

                            # Stop check (may be at breakeven after TP1)
                            if position and current_price <= position["stop_loss"]:
                                stop_price = position["stop_loss"]
                                realized = (stop_price - entry) * position["remaining"]
                                total = position.get("realized", 0.0) + realized
                                state["session_pl"] += realized
                                record_trade("STOP", stop_price, position["remaining"], realized)
                                state["stats"] = update_stats(total)
                                label = "BREAKEVEN STOP" if stop_price >= entry else "STOP LOSS"
                                log_event(f"[bold red]🛑 {label} at ${stop_price:,.2f} — trade total ${total:,.2f}[/bold red]")
                                state["closed"].append({"when": now_str()[5:16],
                                                        "exit": "BE-STOP" if stop_price >= entry else "STOP",
                                                        "pnl": total})
                                play_alert("stop")
                                position = None
                                save_json(POS_FILE, None)

                        else:
                            # No position - check for entry
                            if check_pullback_entry(df, fib_levels):
                                # Entry at the fib entry level (NOT current price!)
                                entry_price = fib_levels["entry"]
                                stop_loss = fib_levels["stop_loss"]
                                position_size = calculate_position_size(entry_price, stop_loss, RISK_AMOUNT_USD) * LEVERAGE

                                position = {
                                    "entry": entry_price,
                                    "size": position_size,
                                    "remaining": position_size,
                                    "realized": 0.0,
                                    "leverage": LEVERAGE,
                                    "liq": entry_price * (1 - 1 / LEVERAGE) if LEVERAGE > 1 else 0.0,
                                    "stop_loss": stop_loss,
                                    "tp1": fib_levels["tp1"],
                                    "tp2": fib_levels["tp2"],
                                    "tp3": fib_levels["tp3"],
                                    "tp4": fib_levels["tp4"],
                                    "entry_time": now_str(),
                                    "tp1_hit": False,
                                    "tp2_hit": False,
                                    "tp3_hit": False,
                                    "tp4_hit": False
                                }
                                save_json(POS_FILE, position)
                                record_trade("ENTRY", entry_price, position_size, 0.0)
                                state["session_entries"] += 1
                                log_event(
                                    f"[bold green]🚀 PICASSO ENTRY[/bold green] "
                                    f"${entry_price:,.2f} · {position_size:.4f} BTC "
                                    f"(${entry_price * position_size:,.2f}) · stop ${stop_loss:,.2f}"
                                )
                                play_alert("entry")

                        state["position"] = position

                except Exception as e:
                    log_event(f"[red]❌ Scan error: {e}[/red]")

                # ---- COUNTDOWN: repaint every second, live ticker price every 10s ----
                for remaining in range(SCAN_INTERVAL, 0, -1):
                    state["countdown"] = remaining
                    if remaining % 10 == 0:
                        try:
                            last = safe_float((ex.fetch_ticker(SYMBOL) or {}).get("last"))
                            if last > 0:
                                state["price"] = last
                                state["price_live"] = True
                        except Exception:
                            pass
                    live.update(build_screen(state))
                    time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 PICASSO Bot stopped by user[/yellow]")

if __name__ == "__main__":
    if "--backtest" in sys.argv:
        idx = sys.argv.index("--backtest")
        bt_days = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 60
        run_backtest(bt_days)
        sys.exit(0)

    if "--tune" in sys.argv:
        idx = sys.argv.index("--tune")
        tn_days = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 90
        run_tune(tn_days)
        sys.exit(0)

    console.print("[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]  PICASSO Fibonacci Trader - Professional Edition  [/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")

    console.print("[bold green]✅ System Configured and Ready[/bold green]")
    console.print("[white]   Fibonacci pullback strategy with double bottom confirmation[/white]\n")

    console.print("[bold yellow]📊 PICASSO Formula:[/bold yellow]")
    console.print(f"[green]  ✅ Entry Level: {FIB_RETRACEMENT_ENTRY} retracement (ENTRY at 0.382)[/green]")
    console.print(f"[green]  ✅ Gold Zone: {FIB_RETRACEMENT_GOLDEN_ZONE} retracement (double bounce confirmation)[/green]")
    console.print(f"[green]  ✅ Stop Loss: {FIB_RETRACEMENT_STOP_LOSS} retracement (below entry & gold zone)[/green]")
    console.print(f"[green]  ✅ TP1: {FIB_EXTENSION_TP1} extension (swing high) - GREEN[/green]")
    console.print(f"[green]  ✅ TP2: {FIB_EXTENSION_TP2} extension (70% within hour) - GREEN[/green]")
    console.print(f"[green]  ✅ TP3: {FIB_EXTENSION_TP3} extension (golden ratio)[/green]")
    console.print(f"[green]  ✅ TP4: {FIB_EXTENSION_TP4} extension (maximum)[/green]")
    console.print(f"[green]  ✅ DOUBLE BOTTOM at gold zone (0.5), then ENTRY at 0.382[/green]\n")

    main()
