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

import os, sys, time, json, csv, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
BALANCE_FILE = BASE / "balance.json"
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
RISK_AMOUNT_USD = float(os.environ.get("PICASSO_RISK_USD", "1000"))  # nominal sizing for raw backtest tables
PAPER_MODE = (os.environ.get("PICASSO_PAPER", "1") == "1")  # Default paper mode

# Account balance (paper bankroll) — operator reset to $80.56 on 2026-08-27.
# balance.json is the authority once it exists; PICASSO_BALANCE only seeds it.
# Sizing risks RISK_PCT% of the CURRENT balance per trade, then caps the posted
# margin at whatever balance is still free — you can never post margin you
# don't have. Realized P/L compounds the balance when a trade closes.
STARTING_BALANCE = float(os.environ.get("PICASSO_BALANCE", "80.56"))
RISK_PCT = float(os.environ.get("PICASSO_RISK_PCT", "20"))  # % of balance risked per trade (pre margin cap)

# Leverage - PAPER/BACKTEST SIMULATION ONLY.
# Binance US is spot-only: no venue this bot may use can execute leverage,
# so live mode is forced to 1x regardless of this setting.
# Multiplies position size; a liquidation price (entry * (1 - 1/lev)) is
# simulated and wipes the remaining margin if touched - checked before the stop.
LEVERAGE = max(1.0, float(os.environ.get("PICASSO_LEVERAGE", "1")))
if not PAPER_MODE and LEVERAGE > 1:
    LEVERAGE = 1.0  # live = spot = 1x, always

# Trading Pairs
# SYMBOL is the backtest/tune/walkforward target; the live TUI scans SYMBOLS.
SYMBOL = os.environ.get("PICASSO_SYMBOL", "BTC/USD")
TIMEFRAME = "1h"  # 1h charts only

# Live roster: symbol -> max leverage for the paper sim (None = global LEVERAGE).
# Leverage caps mirror Kraken's margin listing per pair; live mode is 1x always.
# All pairs verified listed on Kraken 2026-08-27.
SYMBOLS = {
    "BTC/USD": None,
    "AVAX/USD": 10, "LTC/USD": 10, "USDC/USD": 10,
    "UNI/USD": 5, "CRV/USD": 5, "AAVE/USD": 5, "NEAR/USD": 5,
    "RENDER/USD": 5, "PEPE/USD": 5, "HBAR/USD": 5, "DOT/USD": 5,
    "SHIB/USD": 5, "TRX/USD": 5, "BCH/USD": 5, "ALGO/USD": 5,
    "WLD/USD": 3,
}

def sym_leverage(sym):
    lev = SYMBOLS.get(sym)
    return LEVERAGE if lev is None else (1.0 if not PAPER_MODE else float(lev))

# Flat markets (stablecoins, dead chop) have no pullback structure - skip
# entries when the swing range is under this % of price. Keeps USDC/USD from
# generating absurd position sizes off a $0.0002 "swing".
MIN_RANGE_PCT = float(os.environ.get("PICASSO_MIN_RANGE", "0.5"))

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

def fmt_price(v):
    """Price formatting that survives both BTC and PEPE magnitudes."""
    if v is None:
        return "—"
    v = float(v)
    if v >= 1000:
        return f"${v:,.2f}"
    if v >= 1:
        return f"${v:,.4f}"
    if v >= 0.001:
        return f"${v:.6f}"
    return f"${v:.10f}".rstrip("0")

def fmt_price_short(v):
    """Compact price for dense tables."""
    if v is None:
        return "—"
    v = float(v)
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    if v >= 0.001:
        return f"${v:.4f}"
    return f"${v:.2e}"

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

    # STEP -1: A flat market has no pullback structure. Without this, a
    # stablecoin's $0.0002 "swing" sizes an absurd position whose stop is
    # microscopically close - at 10x that was -$10,000 per USDC trade.
    if fib_levels["range"] < float(df.iloc[-1]["close"]) * (MIN_RANGE_PCT / 100.0):
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

def record_trade(symbol, event, price, size, pnl):
    """Append one row to trades.csv - every event, wins AND losses."""
    is_new = not TRADES_CSV.exists()
    if not is_new:
        try:
            with open(TRADES_CSV) as f:
                legacy = "symbol" not in f.readline()
            if legacy:  # rename AFTER the handle closes - Windows can't rename open files
                TRADES_CSV.rename(BASE / "trades_legacy.csv")  # pre-multi-symbol format
                is_new = True
        except Exception:
            pass
    with open(TRADES_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["time", "symbol", "event", "price", "size", "pnl"])
        w.writerow([now_str(), symbol, event, f"{price:.10f}", f"{size:.6f}", f"{pnl:.2f}"])

def update_stats(realized):
    """Book one closed trade into stats.json. Gross P/L; losses count."""
    stats = load_json(STATS_FILE, {"trades": 0, "wins": 0, "losses": 0, "gross_pl": 0.0})
    stats["trades"] += 1
    stats["wins" if realized > 0 else "losses"] += 1
    stats["gross_pl"] += realized
    save_json(STATS_FILE, stats)
    return stats

def get_balance():
    """Current paper bankroll. balance.json is the authority; seeded from env."""
    return float(load_json(BALANCE_FILE, {"balance": STARTING_BALANCE}).get("balance", STARTING_BALANCE))

def update_balance(delta):
    """Compound realized P/L into the bankroll. Called only at live trade close."""
    bal = get_balance() + delta
    save_json(BALANCE_FILE, {"balance": bal, "updated": now_str()})
    return bal

def balance_sized(entry, stop, lev, balance, avail_margin):
    """Size a trade from the bankroll: risk RISK_PCT% of balance, then cap the
    posted margin at what's actually free. Returns (size, margin) — (0, 0) if
    there's no meaningful margin left to post."""
    if avail_margin < 0.50 or entry <= stop:
        return 0.0, 0.0
    risk = balance * RISK_PCT / 100.0
    size = calculate_position_size(entry, stop, risk) * lev
    margin = entry * size / lev
    if margin > avail_margin:
        margin = avail_margin
        size = avail_margin * lev / entry
    return size, margin

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
    lev = f"   [bold white on red] LEV SIM [/]" if PAPER_MODE else ""
    return Panel(
        Align.center(
            f"[bold cyan]🎨 {APP}[/]   [white]KRAKEN · {len(SYMBOLS)} pairs · {TIMEFRAME} · "
            f"bal [bold gold1]${get_balance():,.2f}[/] · risk {RISK_PCT:.0f}%/trade[/]   {mode}{lev}"
        ),
        border_style="cyan", box=box.HEAVY,
    )

def hot_symbol(state):
    """The symbol the detail panels follow: open position first, else the
    bullish symbol nearest its entry level, else the first in the roster."""
    syms = state["syms"]
    for s, d in syms.items():
        if d.get("position"):
            return s
    best, best_dist = None, None
    for s, d in syms.items():
        f, p, m = d.get("fib"), d.get("price"), d.get("metrics") or {}
        if not f or not p or not m.get("bullish"):
            continue
        if f["range"] < p * (MIN_RANGE_PCT / 100.0):
            continue  # flat market (USDC) - can never enter, never interesting
        dist = abs(p - f["entry"]) / p
        if best_dist is None or dist < best_dist:
            best, best_dist = s, dist
    return best or next(iter(syms))

def build_symbols_table(state, hot):
    t = Table(box=box.SIMPLE_HEAD, expand=True, padding=(0, 1),
              title="🛰  SYMBOLS", title_style="bold cyan", border_style="cyan")
    for col, j in (("", "left"), ("Sym", "left"), ("Price", "right"), ("→Ent", "right"),
                   ("T", "right"), ("Vol", "right"), ("Trd", "center"), ("Lev", "right"),
                   ("P/L", "right")):
        t.add_column(col, justify=j, no_wrap=True)
    for sym, d in state["syms"].items():
        base = sym.split("/")[0]
        p, f, m = d.get("price"), d.get("fib"), d.get("metrics") or {}
        pos = d.get("position")
        mark = "[bold magenta]▶[/]" if sym == hot else ""
        flat = bool(f and p and f["range"] < p * (MIN_RANGE_PCT / 100.0))
        dist = "[dim]flat[/]" if flat else (f"{(p - f['entry']) / p * 100:+.1f}%" if (p and f) else "—")
        touches = str(m.get("touches", "—"))
        vol = f"{m.get('vol_ratio', 0):.1f}" if m else "—"
        trend = "[dim]·[/]" if flat else ("[green]B[/]" if m.get("bullish") else "[dim red]·[/]")
        lev = f"{sym_leverage(sym):.0f}x"
        if pos:
            upnl = (p - pos["entry"]) * pos.get("remaining", pos["size"]) + pos.get("realized", 0.0) if p else 0.0
            pl = f"[{'bold green' if upnl >= 0 else 'bold red'}]{upnl:+,.0f}[/]"
            name = f"[bold magenta]{base}[/]"
        else:
            pl = "[dim]—[/]"
            name = f"[bold]{base}[/]" if m.get("bullish") else f"[dim]{base}[/]"
        t.add_row(mark, name, fmt_price_short(p), dist, touches, vol, trend, f"[dim]{lev}[/]", pl)
    return t

def build_fib_table(sym, fib, price):
    table = Table(box=box.ROUNDED, expand=True, border_style="cyan",
                  title=f"📐 {sym} Ladder", title_style="bold cyan")
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
        table.add_row(f"[{style}]{name}[/]", fmt_price(val), marker, role)
    return table

def build_chart(sym, ss):
    """Bar chart of recent 1h closes with the fib levels overlaid as lines."""
    closes = ss.get("closes") or []
    fib = ss.get("fib")
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

    title = f"📈 {sym} · last {len(data)}h"
    sub = (f"[dim]hi[/] [green]{fmt_price(hi)}[/] · [dim]lo[/] [red]{fmt_price(lo)}[/] · "
           f"[dim]now[/] [bold white]{fmt_price(data[-1])}[/]")
    body = Text.from_markup("\n".join(lines))
    body.no_wrap = True
    body.overflow = "crop"
    return Panel(body, title=title, subtitle=sub, border_style="cyan", box=box.ROUNDED)

def build_status(sym, ss):
    fib = ss.get("fib")
    price = ss.get("price")
    metrics = ss.get("metrics") or {}
    position = ss.get("position")
    base = sym.split("/")[0]

    grid = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    grid.add_column(style="white", no_wrap=True)
    grid.add_column(justify="right")

    src = "[green]● live[/]" if ss.get("price_live") else "[yellow]● candle[/]"
    grid.add_row(f"[bold]{base} Price[/]", f"[bold white]{fmt_price(price)}[/] {src}" if price else "—")
    if TREND_SMA:
        if metrics.get("bullish"):
            grid.add_row(f"Trend (SMA{TREND_SMA})", "[bold green]BULL[/]")
        else:
            grid.add_row(f"Trend (SMA{TREND_SMA})", f"[bold red]BEAR — entries off[/] [dim]${metrics.get('sma', 0):,.0f}[/]")

    # Entry-condition detail only while hunting; an open position needs the room
    if not position:
        if fib and price:
            for label, key in (("→ Entry", "entry"), ("→ Gold Zone", "golden_zone"), ("→ Stop", "stop_loss")):
                delta = price - fib[key]
                pct = delta / price * 100
                color = "green" if delta >= 0 else "red"
                d_txt = f"{delta:+,.2f}" if price >= 1 else f"{delta:+.8f}"
                grid.add_row(label, f"[{color}]{d_txt}  ({pct:+.2f}%)[/]")

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
        grid.add_row("Entry", fmt_price(position["entry"]))
        grid.add_row("Size left", f"{rem:,.4f} / {position['size']:,.4f} {base}")
        at_be = position["stop_loss"] >= position["entry"]
        grid.add_row("Stop", fmt_price(position["stop_loss"]) + (" [cyan](breakeven)[/]" if at_be else ""))
        if position.get("leverage", 1.0) > 1:
            grid.add_row("Leverage", f"[bold red]{position['leverage']:.0f}x · liq {fmt_price(position.get('liq', 0))}[/]")
        grid.add_row("Banked", f"[green]{banked:+,.2f} USD[/]" if banked else "[dim]0.00 USD[/]")
        grid.add_row("Unrealized P/L", f"[{u_style}]{upnl:+,.2f} USD[/]")
        tps = "  ".join(
            f"[green]TP{i}✓[/]" if position.get(f"tp{i}_hit") else f"[dim]TP{i}·[/]"
            for i in (1, 2, 3, 4)
        )
        grid.add_row("Targets", tps)
        title, style = f"📊 {sym} — POSITION OPEN", "magenta"
    else:
        title, style = f"📊 {sym} — waiting for setup", "cyan"

    return Panel(grid, title=title, border_style=style, box=box.ROUNDED)

def portfolio_risk(state):
    """Aggregate live risk across open positions: what one bad candle costs."""
    r = {"open": 0, "notional": 0.0, "margin": 0.0, "upnl": 0.0,
         "all_stops": 0.0, "all_liqs": 0.0}
    for sym, d in state["syms"].items():
        pos = d.get("position")
        if not pos:
            continue
        p = d.get("price") or pos["entry"]
        rem = pos.get("remaining", pos["size"])
        lev = pos.get("leverage", 1.0)
        r["open"] += 1
        r["notional"] += p * rem
        r["margin"] += pos["entry"] * rem / lev
        r["upnl"] += (p - pos["entry"]) * rem
        r["all_stops"] += (pos["stop_loss"] - pos["entry"]) * rem
        r["all_liqs"] += (-pos["entry"] * rem / lev) if lev > 1 else (pos["stop_loss"] - pos["entry"]) * rem
    return r

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

    risk = portfolio_risk(state)
    if risk["open"]:
        grid.add_row("[bold red]— Open Risk —[/]", "")
        grid.add_row("Positions", f"{risk['open']}  [dim](${risk['notional']:,.0f} notional)[/]")
        grid.add_row("Margin posted", f"${risk['margin']:,.0f}")
        grid.add_row("If all stops hit", f"[bold red]{risk['all_stops']:+,.0f} USD[/]")
        grid.add_row("If all liqs hit", f"[bold red]{risk['all_liqs']:+,.0f} USD[/]")

    grid.add_row("[bold cyan]— Lifetime —[/]", "")
    grid.add_row("Closed trades", str(stats["trades"]))
    wr = (stats["wins"] / stats["trades"] * 100) if stats["trades"] else None
    grid.add_row("Win rate", f"{wr:.1f}%  ({stats['wins']}W/{stats['losses']}L)" if wr is not None else "[dim]no trades yet[/]")
    gpl = stats["gross_pl"]
    grid.add_row("Gross P/L", f"[{'bold green' if gpl >= 0 else 'bold red'}]{gpl:+,.2f} USD[/]")

    # Risk block replaces last-closes when positions are open (web shows both)
    closed = list(state.get("closed") or [])
    if closed and not risk["open"]:
        grid.add_row("[bold cyan]— Last closes —[/]", "")
        for c in closed[-3:][::-1]:
            style = "green" if c["pnl"] > 0 else "red"
            grid.add_row(f"[dim]{c['when']}[/] {c.get('sym', '')} {c['exit']}", f"[{style}]{c['pnl']:+,.0f}[/]")

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
    hot = hot_symbol(state)
    ss = state["syms"][hot]
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    sym_rows = len(SYMBOLS) + 4
    layout["left"].split_column(
        Layout(build_symbols_table(state, hot), name="symbols", size=sym_rows),
        Layout(build_chart(hot, ss), name="chart"),
    )
    if ss.get("fib"):
        # Priority on short windows: ladder > status > stats (stats shrinks, then drops)
        body_h = console.size.height - 13  # minus header + footer + borders
        right = [Layout(build_fib_table(hot, ss["fib"], ss.get("price")), name="fib", size=14),
                 Layout(build_status(hot, ss), name="status")]
        if body_h >= 30:
            cap = 20 if portfolio_risk(state)["open"] else 15  # room for the risk block
            right.append(Layout(build_stats(state), name="stats",
                                size=max(7, min(cap, body_h - 27))))
        layout["right"].split_column(*right)
    else:
        layout["right"].update(Panel(Align.center("[cyan]⏳ Fetching first candles from Kraken...[/]"),
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
        "[bold]Enter Kraken API Keys[/bold]\n(saved to .picasso_keys.json)",
        style="cyan"
    ))
    api_key = console.input("API Key: ").strip()
    api_secret = console.input("API Secret: ").strip()

    keys = {"apiKey": api_key, "secret": api_secret}
    save_json(KEYS_FILE, keys)
    return keys

def public_exchange():
    """Kraken public client - the live data venue."""
    return ccxt.kraken({"enableRateLimit": True, "timeout": 20000})

# Kraken's public OHLC endpoint returns at most ~720 candles (~30 days of 1h)
# no matter what `since` you pass. Deep history for backtest/tune/walkforward
# falls back to Binance US candles (same assets, near-identical prices) with
# the source labeled in the report. PICASSO_STRICT_KRAKEN=1 disables the
# fallback and caps analysis depth instead.
KRAKEN_MAX_BARS = 700
STRICT_KRAKEN = (os.environ.get("PICASSO_STRICT_KRAKEN", "0") == "1")

def history_exchange(days):
    if days * 24 + 130 <= KRAKEN_MAX_BARS or STRICT_KRAKEN:
        return public_exchange(), "kraken"
    return (ccxt.binanceus({"enableRateLimit": True, "timeout": 20000}),
            "binanceus mirror (Kraken public OHLC caps at ~720 bars)")

def connect_exchange(live=True):
    """
    Connect to Kraken.

    🇺🇸 USA-COMPLIANT EXCHANGE: KRAKEN 🇺🇸
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Switched from Binance US to Kraken 2026-08-27 by operator instruction
    ("switch back to kraken only") - the leverage roster in SYMBOLS mirrors
    Kraken's margin listing. Do not change venues without operator approval.

    PAPER MODE: public API only - no keys, no sandbox, no orders placed.
    LIVE MODE: not leverage-capable in this bot; forced 1x, spot orders only.
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    keys = read_keys()
    return ccxt.kraken({
        "apiKey": keys.get("apiKey", ""),
        "secret": keys.get("secret", ""),
        "enableRateLimit": True,
        "timeout": 20000,
    })

# ========== BACKTEST ==========

def fetch_history(ex, days, symbol=None):
    """Fetch `days` of 1h candles plus lookback, paginated. Falls back to the
    other USD/USDT quote if the venue lists the asset under a different one."""
    symbol = symbol or SYMBOL
    ms_per = 3600 * 1000
    need = days * 24 + 130
    since = ex.milliseconds() - need * ms_per
    if symbol not in (getattr(ex, "markets", None) or {}):
        try:
            ex.load_markets()
        except Exception:
            pass
    if getattr(ex, "markets", None) and symbol not in ex.markets:
        base, quote = symbol.split("/")
        alt = f"{base}/{'USDT' if quote == 'USD' else 'USD'}"
        if alt in ex.markets:
            symbol = alt
    rows = {}
    while True:
        batch = ex.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=1000)
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
            "entry_ts": float(df.iloc[position["entry_i"]]["timestamp"]),
            "exit_ts": float(df.iloc[i]["timestamp"]),
            "margin": position["entry"] * position["size"] / position["leverage"],
            "size": position["size"], "stop0": position["stop0"],
            "lev": position["leverage"],
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
                    "entry": entry, "stop_loss": stop, "stop0": stop, "size": size,
                    "remaining": size, "realized": 0.0, "leverage": LEVERAGE,
                    "liq": entry * (1 - 1 / LEVERAGE) if LEVERAGE > 1 else 0.0,
                    "tp1": fib["tp1"], "tp2": fib["tp2"], "tp3": fib["tp3"], "tp4": fib["tp4"],
                    "tp1_hit": False, "tp2_hit": False, "tp3_hit": False, "tp4_hit": False,
                    "entry_i": i,
                }

    if position:
        close_out("EOD", float(df.iloc[-1]["close"]), len(df) - 1)
    return trades, max_dd

def replay_balance(trades_in, starting=None):
    """Replay simulated trades against ONE shared compounding bankroll.

    Valid because entries/exits in simulate() are size-independent: prices and
    timing never change with position size, only P/L scales (linearly, since
    the exit schedule is fixed 25% fractions). At each entry, size = RISK_PCT%
    of the current balance, margin-capped by what's free after margin already
    posted on still-open trades. Trades that can't post $0.50 margin are
    skipped. Realized P/L lands on the balance at exit time.
    """
    starting = STARTING_BALANCE if starting is None else starting
    trades = sorted(trades_in, key=lambda t: t["entry_ts"])
    open_tr = []                      # [exit_ts, scaled_pnl, margin]
    bal, posted = starting, 0.0
    taken = skipped = 0
    peak, max_dd = starting, 0.0
    curve = [starting]

    def settle(upto):
        nonlocal bal, posted, peak, max_dd
        for o in sorted([o for o in open_tr if o[0] <= upto]):
            bal += o[1]
            posted -= o[2]
            open_tr.remove(o)
            peak = max(peak, bal)
            max_dd = max(max_dd, peak - bal)
            curve.append(bal)

    for tr in trades:
        settle(tr["entry_ts"])
        avail = max(0.0, bal - posted)
        size, margin = balance_sized(tr["entry"], tr["stop0"], tr["lev"], bal, avail)
        if size <= 0 or tr["size"] <= 0:
            skipped += 1
            continue
        scale = size / tr["size"]
        open_tr.append([tr["exit_ts"], tr["pnl"] * scale, margin])
        posted += margin
        taken += 1
    settle(float("inf"))
    return {"start": starting, "final": bal, "taken": taken, "skipped": skipped,
            "peak": peak, "max_dd": max_dd, "curve": curve,
            "ret_pct": (bal - starting) / starting * 100 if starting else 0.0,
            "busted": bal < 1.0}

def print_balance_verdict(rp, label):
    """Render one bankroll replay as a panel."""
    f_style = "bold green" if rp["final"] >= rp["start"] else "bold red"
    blocks = "▁▂▃▄▅▆▇█"
    cv = rp["curve"]
    lo_c, hi_c = min(cv), max(cv)
    span = (hi_c - lo_c) or 1.0
    spark = "".join(blocks[min(7, int((v - lo_c) / span * 7.999))] for v in cv[-60:])
    bust = "\n[bold white on red] 💀 ACCOUNT BUSTED [/bold white on red]" if rp["busted"] else ""
    console.print(Panel.fit(
        f"[bold]${rp['start']:,.2f} → [{f_style}]${rp['final']:,.2f}[/] "
        f"([{f_style}]{rp['ret_pct']:+,.1f}%[/])[/bold]   "
        f"peak ${rp['peak']:,.2f} · max DD ${rp['max_dd']:,.2f}\n"
        f"[bold]Trades:[/] {rp['taken']} taken · {rp['skipped']} skipped (no free margin)\n"
        f"[bold]Balance:[/] [cyan]{spark}[/]\n"
        f"[dim]Risk {RISK_PCT:.0f}% of current balance per trade, margin capped at what's "
        f"free — sizes compound with the account, signals unchanged.[/dim]{bust}",
        title=f"💰 {label}", border_style="gold1"))

def run_backtest(days=60):
    """Replay the exact live entry/exit logic over historical candles."""
    lev_note = f" · {LEVERAGE:.0f}x SIM" if LEVERAGE > 1 else ""
    console.print(f"\n[bold cyan]🎨 PICASSO BACKTEST — {SYMBOL} {TIMEFRAME}, last {days} days{lev_note}[/bold cyan]")
    ex, src = history_exchange(days)
    console.print(f"[dim]history source: {src}[/dim]")
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

    # Equity curve sparkline (cumulative P/L after each trade)
    cum, run = [], 0.0
    for tr in trades:
        run += tr["pnl"]
        cum.append(run)
    lo_c, hi_c = min(cum + [0.0]), max(cum + [0.0])
    span_c = (hi_c - lo_c) or 1.0
    blocks = "▁▂▃▄▅▆▇█"
    spark = "".join(blocks[min(7, int((v - lo_c) / span_c * 7.999))] for v in cum)
    console.print(f"[bold]Equity:[/] [cyan]{spark}[/]  [dim]${lo_c:,.0f} → ${hi_c:,.0f} span[/]\n")

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
        f"(liq, then stop, then TPs). Nominal ${RISK_AMOUNT_USD:.0f} risk/trade at {LEVERAGE:.0f}x, "
        f"gross P/L, no fees.[/dim]",
        title="📜 Backtest Summary", border_style="cyan",
    ))

    # The honest small-account view: same signals replayed on the real bankroll
    print_balance_verdict(replay_balance(trades),
                          f"${STARTING_BALANCE:,.2f} account · {SYMBOL} · {days}d")

def run_backtest_all(days=60):
    """Backtest the whole SYMBOLS roster, each pair at its own max leverage."""
    global LEVERAGE
    console.print(f"\n[bold cyan]🎨 PICASSO FLEET BACKTEST — {len(SYMBOLS)} pairs · last {days} days[/bold cyan]")
    ex, src = history_exchange(days)
    console.print(f"[dim]history source: {src}[/dim]\n")
    saved_lev = LEVERAGE
    rows, all_trades = [], []
    for sym in SYMBOLS:
        try:
            lev = sym_leverage(sym)
            df = fetch_history(ex, days, symbol=sym)
            if len(df) < 150:
                rows.append({"sym": sym, "err": f"only {len(df)} candles"})
                continue
            LEVERAGE = lev
            trades, max_dd = simulate(df)
            wins = sum(1 for t in trades if t["pnl"] > 0)
            gross = sum(t["pnl"] for t in trades)
            rows.append({"sym": sym, "lev": lev, "n": len(trades), "wins": wins,
                         "gross": gross, "dd": max_dd})
            for t in trades:
                t["sym"] = sym
            all_trades.extend(trades)
        except Exception as e:
            rows.append({"sym": sym, "err": str(e)[:60]})
        finally:
            LEVERAGE = saved_lev

    t = Table(box=box.ROUNDED, border_style="cyan", title="Fleet Backtest (per pair)")
    for col, j in (("Pair", "left"), ("Lev", "right"), ("Trades", "right"),
                   ("Win rate", "right"), ("Gross P/L", "right"), ("Max DD", "right")):
        t.add_column(col, justify=j)
    for r in sorted(rows, key=lambda r: r.get("gross", -1e18), reverse=True):
        if "err" in r:
            t.add_row(r["sym"], "—", "—", "—", f"[yellow]{r['err']}[/]", "—")
            continue
        wr = f"{r['wins']/r['n']*100:.0f}%" if r["n"] else "—"
        style = "green" if r["gross"] > 0 else ("red" if r["gross"] < 0 else "dim")
        t.add_row(r["sym"], f"{r['lev']:.0f}x", str(r["n"]), wr,
                  f"[{style}]{r['gross']:+,.0f}[/]", f"${r['dd']:,.0f}")
    console.print(t)

    if all_trades:
        # Equity ordered by EXIT time - P/L books when trades close, not open
        all_trades.sort(key=lambda x: x.get("exit_ts", 0))
        cum, run, peak, dd = [], 0.0, 0.0, 0.0
        for tr in all_trades:
            run += tr["pnl"]
            cum.append(run)
            peak = max(peak, run)
            dd = max(dd, peak - run)

        # Overlap analysis: how simultaneous was the fleet, really?
        events = []
        for tr in all_trades:
            events.append((tr["entry_ts"], 1, tr.get("margin", 0.0)))
            events.append((tr["exit_ts"], -1, -tr.get("margin", 0.0)))
        events.sort()  # exits (-1) before entries (+1) on ties
        cur_n = peak_n = 0
        cur_m = peak_m = 0.0
        for _, delta, m in events:
            cur_n += delta
            cur_m += m
            peak_n = max(peak_n, cur_n)
            peak_m = max(peak_m, cur_m)
        lo_c, hi_c = min(cum + [0.0]), max(cum + [0.0])
        span = (hi_c - lo_c) or 1.0
        blocks = "▁▂▃▄▅▆▇█"
        spark = "".join(blocks[min(7, int((v - lo_c) / span * 7.999))] for v in cum)
        n = len(all_trades)
        wins = sum(1 for x in all_trades if x["pnl"] > 0)
        gross = sum(x["pnl"] for x in all_trades)
        g_style = "bold green" if gross >= 0 else "bold red"
        console.print(f"[bold]Fleet equity:[/] [cyan]{spark}[/]")
        console.print(Panel.fit(
            f"[bold]Fleet total:[/] {n} trades · WR {wins/n*100:.1f}% ({wins}W/{n-wins}L) · "
            f"gross [{g_style}]{gross:+,.2f} USD[/] · combined max DD ${dd:,.2f}\n"
            f"[bold]Overlap:[/] peak {peak_n} positions open at once · "
            f"peak margin posted ${peak_m:,.0f}\n"
            f"[dim]Each pair simulated independently at its own leverage; overlap shows how "
            f"much capital that would actually take. Scaled exits, gross P/L, no fees.[/dim]",
            title="🚁 Fleet Verdict", border_style="cyan"))

        # Shared-bankroll replay: all pairs compete chronologically for the
        # same $80.56 of margin — the number the operator actually has
        print_balance_verdict(replay_balance(all_trades),
                              f"${STARTING_BALANCE:,.2f} account · all pairs · {days}d")

# ========== TUNER ==========

def sweep_grid(df):
    """Sweep the volume x tolerance grid over one DataFrame at 1x leverage.
    Returns result rows; restores module params afterward."""
    global VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE
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
    return results

def run_tune(days=90):
    """Grid-search entry filters over one fetched history. 1h timeframe is
    fixed by design - only volume confirmation and touch tolerance vary.
    Tuned at 1x leverage so results measure signal quality, not sizing."""
    console.print(f"\n[bold cyan]🎨 PICASSO TUNE — {SYMBOL} {TIMEFRAME}, last {days} days[/bold cyan]")
    ex, src = history_exchange(days)
    console.print(f"[dim]history source: {src}[/dim]")
    df = fetch_history(ex, days)
    console.print(f"[dim]{len(df)} candles fetched — sweeping volume x tolerance grid at 1x[/dim]\n")
    results = sweep_grid(df)
    saved = (VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE)

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

# ========== WALK-FORWARD VALIDATION ==========

def run_walkforward(days=270, tune_days=90, test_days=30):
    """Anti-overfit check: tune on `tune_days`, then trade the NEXT `test_days`
    out-of-sample with the chosen params. Roll forward and aggregate.
    All at 1x leverage - this measures signal quality, not sizing."""
    global VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE
    console.print(f"\n[bold cyan]🎨 PICASSO WALK-FORWARD — {days}d history: "
                  f"tune {tune_days}d → test {test_days}d, rolling[/bold cyan]")
    ex, src = history_exchange(days)
    console.print(f"[dim]history source: {src}[/dim]")
    df = fetch_history(ex, days)
    console.print(f"[dim]{len(df)} candles fetched[/dim]\n")

    TUNE_BARS, TEST_BARS, LEAD = tune_days * 24, test_days * 24, 200
    saved = (VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE)
    folds, oos_all = [], []
    start = 0
    while start + TUNE_BARS + TEST_BARS <= len(df):
        tune_df = df.iloc[start: start + TUNE_BARS].reset_index(drop=True)
        test_lead = max(0, start + TUNE_BARS - LEAD)
        test_df = df.iloc[test_lead: start + TUNE_BARS + TEST_BARS].reset_index(drop=True)
        test_start_ts = df.iloc[start + TUNE_BARS]["timestamp"]
        test_start_dt = datetime.fromtimestamp(test_start_ts / 1000, tz=timezone.utc)

        grid = [r for r in sweep_grid(tune_df) if r["n"] >= 5]
        grid.sort(key=lambda r: r["gross"], reverse=True)
        if grid:
            vol, tol, is_gross = grid[0]["vol"], grid[0]["tol"], grid[0]["gross"]
        else:
            vol, tol, is_gross = saved[0], saved[1], None  # nothing tunable: keep current params

        try:
            VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE = vol, tol, 1.0
            trades, _ = simulate(test_df)
        finally:
            VOLUME_CONFIRMATION, TOUCH_TOL_PCT, LEVERAGE = saved
        oos = [t for t in trades if t["when"] >= test_start_dt]
        oos_all.extend(oos)
        folds.append({"start": test_start_dt, "vol": vol, "tol": tol, "is_gross": is_gross,
                      "n": len(oos), "wins": sum(1 for t in oos if t["pnl"] > 0),
                      "gross": sum(t["pnl"] for t in oos)})
        log_msg = f"fold {len(folds)}: tuned ({vol:.1f}x, {tol:.2f}) → OOS {len(oos)} trades, {folds[-1]['gross']:+,.0f}"
        console.print(f"[dim]{log_msg}[/dim]")
        start += TEST_BARS

    if not folds:
        console.print("[yellow]Not enough history for a single fold.[/yellow]")
        return

    t = Table(box=box.ROUNDED, border_style="cyan", title="Walk-Forward Folds (out-of-sample)")
    for col, j in (("Test month", "left"), ("Tuned params", "left"), ("IS gross", "right"),
                   ("OOS trades", "right"), ("OOS WR", "right"), ("OOS gross", "right")):
        t.add_column(col, justify=j)
    for f in folds:
        wr = f"{f['wins']/f['n']*100:.0f}%" if f["n"] else "—"
        style = "green" if f["gross"] > 0 else ("red" if f["gross"] < 0 else "dim")
        t.add_row(f"{f['start']:%Y-%m-%d}", f"{f['vol']:.1f}x / {f['tol']:.2f}",
                  f"{f['is_gross']:+,.0f}" if f["is_gross"] is not None else "[dim]default[/]",
                  str(f["n"]), wr, f"[{style}]{f['gross']:+,.0f}[/]")
    console.print(t)

    n = len(oos_all)
    wins = sum(1 for x in oos_all if x["pnl"] > 0)
    gross = sum(x["pnl"] for x in oos_all)
    g_style = "bold green" if gross >= 0 else "bold red"
    console.print(Panel.fit(
        f"[bold]Out-of-sample total:[/] {n} trades · "
        f"WR {wins/n*100:.1f}% ({wins}W/{n-wins}L) · gross [{g_style}]{gross:+,.2f} USD[/] at 1x\n"
        f"[dim]This is the honest number: every trade here was taken on data the tuner never saw.[/dim]",
        title="🧪 Walk-Forward Verdict", border_style="cyan"))

# ========== WEB DASHBOARD ==========

HTTP_PORT = int(os.environ.get("PICASSO_HTTP_PORT", "8877"))
_WEB_STATE = {"state": None}
_TAG_RE = re.compile(r"\[/?[^\[\]]*\]")

def _strip_markup(s):
    return _TAG_RE.sub("", s)

def state_snapshot(state):
    """JSON-safe snapshot of live state for the web dashboard."""
    if not state:
        return {"ready": False}
    syms_out = {}
    for sym, d in state["syms"].items():
        syms_out[sym] = {
            "price": d.get("price"), "live": bool(d.get("price_live")),
            "fib": d.get("fib"), "metrics": d.get("metrics"),
            "closes": (d.get("closes") or [])[-96:],
            "candles": (d.get("candles") or [])[-96:],
            "leverage": sym_leverage(sym),
            "position": d.get("position"),
        }
    return {
        "ready": True, "app": APP, "paper": PAPER_MODE, "timeframe": TIMEFRAME,
        "risk_usd": RISK_AMOUNT_USD, "countdown": state.get("countdown", 0),
        "balance": get_balance(), "risk_pct": RISK_PCT,
        "scan_interval": SCAN_INTERVAL, "scans": state.get("scans", 0),
        "started": state.get("started"), "session_pl": state.get("session_pl", 0.0),
        "session_entries": state.get("session_entries", 0),
        "stats": state.get("stats"), "hot": hot_symbol(state),
        "min_range_pct": MIN_RANGE_PCT,
        "risk": portfolio_risk(state),
        "equity": (state.get("equity") or [])[-200:],
        "closed": list(state.get("closed") or []),
        "events": [_strip_markup(e) for e in list(EVENTS)[:30]],
        "now": time.time(), "syms": syms_out,
    }

class _WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the TUI console clean
        pass

    def do_GET(self):
        try:
            if self.path.startswith("/api/state"):
                body = json.dumps(state_snapshot(_WEB_STATE["state"])).encode()
                ctype = "application/json"
            elif self.path.startswith("/api/trades"):
                rows = []
                try:
                    with open(TRADES_CSV, newline="") as f:
                        rows = list(csv.DictReader(f))[-100:]
                except FileNotFoundError:
                    pass
                body = json.dumps(rows).encode()
                ctype = "application/json"
            else:
                body = (BASE / "dashboard.html").read_bytes()
                ctype = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            try:
                self.send_error(500)
            except Exception:
                pass

def start_web(state):
    """Serve the dashboard on localhost only. Port busy -> log and carry on."""
    _WEB_STATE["state"] = state
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), _WebHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log_event(f"[cyan]🌐 Web dashboard: http://localhost:{HTTP_PORT}[/cyan]")
    except OSError as e:
        log_event(f"[yellow]⚠ Web dashboard port {HTTP_PORT} unavailable: {e}[/yellow]")

# ========== MAIN LOOP ==========

def save_positions(state):
    save_json(POS_FILE, {s: d["position"] for s, d in state["syms"].items() if d.get("position")})

def scan_symbol(ex, sym, state):
    """Fetch candles for one symbol, run entry/exit logic, update its state."""
    ss = state["syms"][sym]
    base = sym.split("/")[0]
    ohlcv = ex.fetch_ohlcv(sym, TIMEFRAME, limit=200)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    swing_low, swing_high = find_swing_high_low(df)
    if swing_low is None or swing_high is None:
        return
    fib_levels = calculate_fibonacci_levels(swing_low, swing_high)
    current_price = float(df.iloc[-1]["close"])
    ss["fib"] = fib_levels
    ss["price"] = current_price
    ss["price_live"] = False
    ss["metrics"] = market_metrics(df, fib_levels)
    ss["closes"] = [float(c) for c in df["close"].tail(120)]
    # OHLC for the web dashboard's candlestick chart: [ts_ms, open, high, low, close, volume]
    ss["candles"] = [[int(r.timestamp), float(r.open), float(r.high), float(r.low),
                      float(r.close), float(r.volume)] for r in df.tail(96).itertuples()]

    position = ss.get("position")
    if position:
        entry = position["entry"]
        lev = position.get("leverage", 1.0)

        # Liquidation first (leveraged sims): past liq the margin is gone
        # before any stop order could save you
        liq = position.get("liq", 0.0)
        if lev > 1 and liq > 0 and current_price <= liq:
            margin = entry * position["remaining"] / lev
            realized = -margin
            total = position.get("realized", 0.0) + realized
            state["session_pl"] += realized
            record_trade(sym, "LIQUIDATED", liq, position["remaining"], realized)
            state["stats"] = update_stats(total)
            update_balance(total)
            state["closed"].append({"when": now_str()[5:16], "sym": base, "exit": "LIQ", "pnl": total})
            log_event(f"[bold white on red]💀 {sym} LIQUIDATED at {fmt_price(liq)} — margin wiped: ${realized:,.2f}[/bold white on red]")
            play_alert("liq")
            position = ss["position"] = None
            save_positions(state)

        if position:
            # Scaled exits: 25% of the position at each TP
            for i in (1, 2, 3, 4):
                tp = position[f"tp{i}"]
                if current_price >= tp and not position.get(f"tp{i}_hit"):
                    position[f"tp{i}_hit"] = True
                    slice_size = min(position["size"] * 0.25 if i < 4 else position["remaining"],
                                     position["remaining"])
                    realized = (tp - entry) * slice_size
                    position["remaining"] -= slice_size
                    position["realized"] = position.get("realized", 0.0) + realized
                    state["session_pl"] += realized
                    track_trade_profit(realized)
                    record_trade(sym, f"TP{i}", tp, slice_size, realized)
                    log_event(f"[bold green]{'🎯' * i} {sym} TP{i} — sold {slice_size:,.4f} {base} at {fmt_price(tp)}, banked ${realized:,.2f}[/bold green]")
                    play_alert("tp")
                    if i == 1 and position["stop_loss"] < entry:
                        position["stop_loss"] = entry
                        log_event(f"[cyan]🛡 {sym} stop moved to breakeven[/cyan]")
                    save_positions(state)
                    if i == 4 or position["remaining"] <= 1e-12:
                        total = position["realized"]
                        log_event(f"[bold magenta]🎨 {sym} COMPLETE — trade banked ${total:,.2f}[/bold magenta]")
                        state["stats"] = update_stats(total)
                        update_balance(total)
                        state["closed"].append({"when": now_str()[5:16], "sym": base, "exit": "TP4", "pnl": total})
                        position = ss["position"] = None
                        save_positions(state)
                        break

        # Stop check (may be at breakeven after TP1)
        if position and current_price <= position["stop_loss"]:
            stop_price = position["stop_loss"]
            realized = (stop_price - entry) * position["remaining"]
            total = position.get("realized", 0.0) + realized
            state["session_pl"] += realized
            record_trade(sym, "STOP", stop_price, position["remaining"], realized)
            state["stats"] = update_stats(total)
            update_balance(total)
            label = "BREAKEVEN STOP" if stop_price >= entry else "STOP LOSS"
            log_event(f"[bold red]🛑 {sym} {label} at {fmt_price(stop_price)} — trade total ${total:,.2f}[/bold red]")
            state["closed"].append({"when": now_str()[5:16], "sym": base,
                                    "exit": "BE-STOP" if stop_price >= entry else "STOP",
                                    "pnl": total})
            play_alert("stop")
            ss["position"] = None
            save_positions(state)

    else:
        # No position - check for entry
        if check_pullback_entry(df, fib_levels):
            lev = sym_leverage(sym)
            entry_price = fib_levels["entry"]
            stop_loss = fib_levels["stop_loss"]
            # Size from the bankroll: risk RISK_PCT% of balance, margin capped
            # by what's not already posted on other open positions
            balance = get_balance()
            avail = max(0.0, balance - portfolio_risk(state)["margin"])
            position_size, margin = balance_sized(entry_price, stop_loss, lev, balance, avail)
            if position_size <= 0:
                log_event(f"[yellow]⚠ {sym} setup fired but no free margin "
                          f"(balance ${balance:,.2f}, ${avail:,.2f} free) — skipped[/yellow]")
                return

            ss["position"] = {
                "entry": entry_price,
                "size": position_size,
                "remaining": position_size,
                "realized": 0.0,
                "leverage": lev,
                "liq": entry_price * (1 - 1 / lev) if lev > 1 else 0.0,
                "stop_loss": stop_loss,
                "tp1": fib_levels["tp1"],
                "tp2": fib_levels["tp2"],
                "tp3": fib_levels["tp3"],
                "tp4": fib_levels["tp4"],
                "entry_time": now_str(),
                "tp1_hit": False, "tp2_hit": False, "tp3_hit": False, "tp4_hit": False,
            }
            save_positions(state)
            record_trade(sym, "ENTRY", entry_price, position_size, 0.0)
            state["session_entries"] += 1
            log_event(
                f"[bold green]🚀 {sym} ENTRY[/bold green] {fmt_price(entry_price)} · "
                f"{position_size:,.4f} {base} at {lev:.0f}x · stop {fmt_price(stop_loss)}"
            )
            play_alert("entry")

def main():
    """Main PICASSO trading loop - full-screen auto-fit Rich TUI, multi-symbol"""

    # Connect to exchange
    try:
        ex = connect_exchange(live=not PAPER_MODE)
        ex.load_markets()
        console.print("[green]✅ Connected to Kraken[/green]")
    except Exception as e:
        console.print(f"[red]❌ Exchange connection failed: {e}[/red]")
        return

    # Load open positions (migrate legacy single-position and pre-scaled formats)
    positions = load_json(POS_FILE, {}) or {}
    if "entry" in positions:
        positions = {SYMBOL: positions}
    for sym, p in positions.items():
        p.setdefault("remaining", p["size"])
        p.setdefault("realized", 0.0)
        p.setdefault("leverage", 1.0)
        p.setdefault("liq", 0.0)
        log_event(f"[magenta]Resumed {sym} position (entry {fmt_price(p['entry'])})[/magenta]")

    state = {"syms": {sym: {"fib": None, "price": None, "price_live": False, "metrics": None,
                            "closes": None, "candles": None, "position": positions.get(sym)}
                      for sym in SYMBOLS},
             "countdown": SCAN_INTERVAL,
             "started": time.time(), "scans": 0, "session_entries": 0, "session_pl": 0.0,
             "closed": deque(maxlen=20), "equity": [],
             "stats": load_json(STATS_FILE, {"trades": 0, "wins": 0, "losses": 0, "gross_pl": 0.0})}

    if PAPER_MODE:
        log_event("[bold red]⚠ Leverage SIMULATION per Kraken margin caps — paper only; live is 1x[/bold red]")
    log_event(f"[cyan]PICASSO online — scanning {len(SYMBOLS)} Kraken pairs on {TIMEFRAME}[/cyan]")
    start_web(state)

    try:
        with Live(build_screen(state), console=console, screen=True, refresh_per_second=4) as live:
            while True:
                # ---- SCAN SWEEP: every symbol, repainting as results land ----
                for sym in SYMBOLS:
                    prev_pl = state["session_pl"]
                    try:
                        scan_symbol(ex, sym, state)
                    except Exception as e:
                        log_event(f"[red]❌ {sym} scan error: {e}[/red]")
                    if state["session_pl"] != prev_pl:
                        state["equity"].append({"t": time.time(), "pl": state["session_pl"]})
                        state["equity"] = state["equity"][-500:]
                    live.update(build_screen(state))
                state["scans"] += 1

                # ---- COUNTDOWN: repaint every second, batch tickers every 15s ----
                for remaining in range(SCAN_INTERVAL, 0, -1):
                    state["countdown"] = remaining
                    if remaining % 15 == 0:
                        try:
                            ticks = ex.fetch_tickers(list(SYMBOLS)) or {}
                            for sym, tk in ticks.items():
                                last = safe_float((tk or {}).get("last"))
                                if sym in state["syms"] and last > 0:
                                    state["syms"][sym]["price"] = last
                                    state["syms"][sym]["price_live"] = True
                        except Exception:
                            pass
                    live.update(build_screen(state))
                    time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 PICASSO Bot stopped by user[/yellow]")

if __name__ == "__main__":
    if "--backtest" in sys.argv:
        idx = sys.argv.index("--backtest")
        bt_args = sys.argv[idx + 1: idx + 3]
        if bt_args and bt_args[0].lower() == "all":
            bt_days = int(bt_args[1]) if len(bt_args) > 1 and bt_args[1].isdigit() else 60
            run_backtest_all(bt_days)
        else:
            bt_days = int(bt_args[0]) if bt_args and bt_args[0].isdigit() else 60
            run_backtest(bt_days)
        sys.exit(0)

    if "--tune" in sys.argv:
        idx = sys.argv.index("--tune")
        tn_days = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 90
        run_tune(tn_days)
        sys.exit(0)

    if "--walkforward" in sys.argv:
        idx = sys.argv.index("--walkforward")
        wf_days = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 270
        run_walkforward(wf_days)
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
