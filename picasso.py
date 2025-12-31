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

import ccxt
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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

# Risk Management
RISK_AMOUNT_USD = float(os.environ.get("PICASSO_RISK_USD", "1000"))  # $1000 per trade (user's proven amount)
PAPER_MODE = (os.environ.get("PICASSO_PAPER", "1") == "1")  # Default paper mode

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

    # Tolerance for level detection
    entry_tolerance = entry_level * 0.02  # 2% tolerance
    golden_tolerance = golden_zone * 0.02

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

    # ALL CONDITIONS for entry:
    # 1. Double bottom at gold zone confirmed ✓
    # 2. Price recently was at gold zone ✓
    # 3. Price now at entry level (0.382) ✓
    # 4. Price bouncing up ✓
    # 5. Volume spike ✓
    # 6. Above stop loss ✓
    if (double_bottom_confirmed and recent_was_at_golden and at_entry_level and
        below_swing_high and bouncing_up and volume_ok and above_stop):
        console.print("[bold yellow]🎯 DOUBLE BOTTOM at GOLD ZONE (0.5) confirmed![/bold yellow]")
        console.print(f"[bold green]🚀 ENTRY at 0.382 level (${close_price:.2f})![/bold green]")
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

            console.print(f"[bold green]🎉 CUSTOMER BREAKEVEN ACHIEVED! Vendor earnings start now.[/bold green]")
        else:
            # All share goes to customer refund
            license_data["refund_progress"] += share_amount
            console.print(f"[cyan]Refund progress: ${license_data['refund_progress']:.2f} / $100.00[/cyan]")
    else:
        # Customer already recouped, all share goes to vendor
        license_data["vendor_earnings"] += share_amount
        console.print(f"[bold green]💰 Vendor earnings: +${share_amount:.2f} (Total: ${license_data['vendor_earnings']:.2f})[/bold green]")

    save_json(LICENSE_FILE, license_data)
    return license_data

# ========== DISPLAY ==========

def display_header():
    """Display PICASSO header"""
    console.clear()
    console.print(Panel.fit(
        f"[bold cyan]{APP}[/bold cyan]\n"
        f"[white]Fibonacci Pullback Strategy - Automated Trading System[/white]\n"
        f"[yellow]Mode: {'PAPER TRADING' if PAPER_MODE else 'LIVE TRADING'}[/yellow]",
        border_style="cyan"
    ))

def display_fib_levels(fib_levels):
    """Display current Fibonacci levels"""
    table = Table(title="📐 Fibonacci Levels", box=box.ROUNDED, style="cyan")
    table.add_column("Level", style="yellow")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Description", style="white")

    table.add_row("Swing High", f"${fib_levels['swing_high']:.2f}", "Recent high")
    table.add_row("Swing Low", f"${fib_levels['swing_low']:.2f}", "Recent low")
    table.add_row("", "", "")
    table.add_row("Entry Level", f"${fib_levels['entry']:.2f}", f"{FIB_RETRACEMENT_ENTRY} retracement (ENTRY)")
    table.add_row("Gold Zone", f"${fib_levels['golden_zone']:.2f}", f"{FIB_RETRACEMENT_GOLDEN_ZONE} retracement (double bounce)")
    table.add_row("Stop Loss", f"${fib_levels['stop_loss']:.2f}", f"{FIB_RETRACEMENT_STOP_LOSS} retracement")
    table.add_row("", "", "")
    table.add_row("TP1 (GREEN)", f"${fib_levels['tp1']:.2f}", f"{FIB_EXTENSION_TP1} ext (swing high)")
    table.add_row("TP2 (GREEN)", f"${fib_levels['tp2']:.2f}", f"{FIB_EXTENSION_TP2} ext (70% in 1hr)")
    table.add_row("TP3", f"${fib_levels['tp3']:.2f}", f"{FIB_EXTENSION_TP3} ext (golden ratio)")
    table.add_row("TP4", f"${fib_levels['tp4']:.2f}", f"{FIB_EXTENSION_TP4} ext (max extension)")

    console.print(table)

# ========== EXCHANGE CONNECTION ==========

def read_keys():
    if KEYS_FILE.exists():
        return load_json(KEYS_FILE, {})

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

# ========== MAIN LOOP ==========

def main():
    """Main PICASSO trading loop"""

    display_header()

    console.print("\n[bold cyan]🎨 PICASSO Bot Starting...[/bold cyan]")
    console.print(f"[yellow]Symbol: {SYMBOL}[/yellow]")
    console.print(f"[yellow]Timeframe: {TIMEFRAME}[/yellow]")
    console.print(f"[yellow]Risk per trade: ${RISK_AMOUNT_USD}[/yellow]")
    console.print(f"[yellow]Mode: {'PAPER' if PAPER_MODE else 'LIVE'}[/yellow]\n")

    # Connect to exchange
    try:
        ex = connect_exchange(live=not PAPER_MODE)
        console.print("[green]✅ Connected to Binance US[/green]\n")
    except Exception as e:
        console.print(f"[red]❌ Exchange connection failed: {e}[/red]")
        return

    # Load existing position if any
    position = load_json(POS_FILE, None)

    console.print("[cyan]⏳ Monitoring for PICASSO setup...[/cyan]")
    console.print("[dim]Waiting for pullback to gold zone (0.5), double bottom, then entry at 0.382...[/dim]\n")

    cycle = 0

    while True:
        try:
            cycle += 1

            # Fetch 1h candles
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

            # Find swing high/low
            swing_low, swing_high = find_swing_high_low(df)

            if swing_low is None or swing_high is None:
                console.print("[yellow]⚠ Not enough data for swing detection[/yellow]")
                time.sleep(SCAN_INTERVAL)
                continue

            # Calculate Fibonacci levels
            fib_levels = calculate_fibonacci_levels(swing_low, swing_high)

            # Display levels periodically
            if cycle % 5 == 1:
                display_fib_levels(fib_levels)

            current_price = float(df.iloc[-1]["close"])

            # Check if we have an open position
            if position:
                console.print(f"[cyan]📊 Position active | Current: ${current_price:.2f}[/cyan]")

                # Check take-profit levels
                entry = position["entry"]
                tp1 = position["tp1"]
                tp2 = position["tp2"]
                tp3 = position["tp3"]
                tp4 = position["tp4"]
                stop = position["stop_loss"]

                # TP logic
                if current_price >= tp1 and not position.get("tp1_hit"):
                    profit = (current_price - entry) * position["size"]
                    console.print(f"[bold green]🎯 TP1 HIT! Profit: ${profit:.2f}[/bold green]")
                    position["tp1_hit"] = True
                    track_trade_profit(profit)
                    save_json(POS_FILE, position)

                if current_price >= tp2 and not position.get("tp2_hit"):
                    profit = (current_price - entry) * position["size"]
                    console.print(f"[bold green]🎯🎯 TP2 HIT! Profit: ${profit:.2f}[/bold green]")
                    position["tp2_hit"] = True
                    track_trade_profit(profit)
                    save_json(POS_FILE, position)

                if current_price >= tp3 and not position.get("tp3_hit"):
                    profit = (current_price - entry) * position["size"]
                    console.print(f"[bold green]🎯🎯🎯 TP3 HIT! Profit: ${profit:.2f}[/bold green]")
                    position["tp3_hit"] = True
                    track_trade_profit(profit)
                    save_json(POS_FILE, position)

                if current_price >= tp4 and not position.get("tp4_hit"):
                    profit = (current_price - entry) * position["size"]
                    console.print(f"[bold green]🎯🎯🎯🎯 TP4 HIT! MAXIMUM EXTENSION! Profit: ${profit:.2f}[/bold green]")
                    position["tp4_hit"] = True
                    track_trade_profit(profit)
                    save_json(POS_FILE, position)
                    # Close position after TP4
                    console.print(f"[bold magenta]🎨 PICASSO COMPLETE! All TPs hit, closing position.[/bold magenta]")
                    position = None
                    save_json(POS_FILE, None)

                # Stop loss check
                if current_price <= stop and position:
                    loss = (entry - current_price) * position["size"]
                    console.print(f"[bold red]🛑 STOP LOSS HIT! Loss: -${loss:.2f}[/bold red]")
                    position = None
                    save_json(POS_FILE, None)

            else:
                # No position - check for entry
                if check_pullback_entry(df, fib_levels):
                    # Entry at 0.382 level (NOT current price!)
                    entry_price = fib_levels["entry"]
                    stop_loss = fib_levels["stop_loss"]
                    position_size = calculate_position_size(entry_price, stop_loss, RISK_AMOUNT_USD)

                    position = {
                        "entry": entry_price,
                        "size": position_size,
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

                    console.print(Panel.fit(
                        f"[bold green]🚀 PICASSO ENTRY![/bold green]\n"
                        f"[cyan]Entry: ${entry_price:.2f}[/cyan]\n"
                        f"[cyan]Size: {position_size:.4f} BTC (${entry_price * position_size:.2f})[/cyan]\n"
                        f"[red]Stop Loss: ${stop_loss:.2f}[/red]\n"
                        f"[green]TP1: ${fib_levels['tp1']:.2f} (100% winner)[/green]\n"
                        f"[green]TP2: ${fib_levels['tp2']:.2f} (70% in 1hr)[/green]\n"
                        f"[green]TP3: ${fib_levels['tp3']:.2f} (golden ratio)[/green]\n"
                        f"[green]TP4: ${fib_levels['tp4']:.2f} (maximum)[/green]",
                        border_style="green"
                    ))
                else:
                    console.print(f"[dim]{now_str()} | Price: ${current_price:.2f} | Waiting for double bottom at gold zone (0.5), then entry at 0.382...[/dim]")

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 PICASSO Bot stopped by user[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
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
