# PICASSO 🎨 — Fibonacci Pullback Trader

**Live Kraken spot-margin bot. Buys fib pullbacks in bullish trends across 17 USD pairs, scaled exits at fib extensions, real leverage at the venue maximum.**

> 🔴 **LIVE since 2026-08-27.** This bot places real Kraken margin orders with real money when `PICASSO_PAPER=0`. It is the operator's personal bot — not part of the paper signal fleet.

## What it does

- Scans **17 Kraken USD pairs** on **1h candles** every 5 minutes, with a live WebSocket feed for real-time exits between scans.
- Finds the swing high/low (120-bar lookback), draws Fibonacci retracements, and waits for a **double-bottom in the golden zone (0.5)** followed by a reclaim of the **0.382 entry level** with volume confirmation.
- Enters long with a stop at the **0.618** retracement; exits are scaled — **25% at each of TP1–TP4** (fib extensions), stop moved to breakeven after TP1.
- Sizes every trade from the real bankroll: risks `PICASSO_RISK_PCT` (default 20%) of the current balance against the stop distance, with posted margin capped at what's actually free. Balance is synced from the Kraken USD cash line at startup.

## Leverage: venue max, gateway-verified

Live mode rides **Kraken's own maximum leverage on every pair** — currently BTC 20x; AVAX/LTC/USDC 10x; most pairs 5x; WLD 3x. The roster caps in `SYMBOLS` apply to the paper sim only.

One hard-won detail: Kraken's `AssetPairs` REST field `leverage_buy` **lags the real venue caps** — it reported 10x for BTC/USD while the Pro UI badged 20x and the order gateway accepted `leverage=20` (verified 2026-08-27 with validate-only orders; 21x+ rejected, proving the check is real). `VENUE_LEV_PROBES` re-probes the gateway at every live startup and falls back to the listed cap if the venue refuses — never trust the listing over the gateway.

## Running it

**Windows (the real launcher):**
```bat
launch_picasso.bat
```
The launcher kills any running Picasso first (never two processes on port 8877), sets the live environment, and opens the dashboard.

> ⚠️ **The .bat must stay CRLF.** cmd.exe silently mis-parses LF-only batch files — it once ate `set PICASSO_PAPER=0` and the bot came up in paper mode while looking live.

**Paper mode (no keys needed — public data only):**
```bash
PICASSO_PAPER=1 python picasso.py
```

**Research modes:**
```bash
python picasso.py --backtest [days] [symbol]   # replay the strategy on history
python picasso.py --tune 90                    # grid-search vol/touch-tol params
python picasso.py --walkforward 270            # out-of-sample validation
```

## Dashboard

- Full-screen Rich TUI in the terminal.
- Web dashboard at **http://localhost:8877** — live prices, fib levels per pair, positions, risk aggregate, equity curve, trade journal (`/api/state`, `/api/trades`).

## Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `PICASSO_PAPER` | `1` | `0` = live margin orders (real money) |
| `PICASSO_RISK_PCT` | `20` | % of balance risked per trade |
| `PICASSO_BALANCE` | `80.56` | Seeds `balance.json` on first run only |
| `PICASSO_LEVERAGE` | `1` | Paper-sim global leverage (live uses venue max) |
| `PICASSO_ENTRY` | `0.382` | Entry retracement level |
| `PICASSO_GOLDEN_ZONE` | `0.5` | Double-bottom zone |
| `PICASSO_STOP_LOSS` | `0.618` | Stop retracement level |
| `PICASSO_VOL_MULT` | `1.5` | Volume confirmation multiple (tuned: `1.0`) |
| `PICASSO_TOUCH_TOL` | `0.02` | Level touch tolerance (tuned: `0.03`) |
| `PICASSO_MIN_RANGE` | `0.5` | Min swing range % — skips flat/stablecoin chop |
| `PICASSO_SCAN_INTERVAL` | `300` | Seconds between scans |
| `PICASSO_HTTP_PORT` | `8877` | Dashboard port |

## Files

| File | What |
|---|---|
| `picasso.py` | The whole bot — strategy, sizing, live orders, TUI, web server, backtest |
| `launch_picasso.bat` | Live launcher (kill-then-start, env, dashboard) |
| `dashboard.html` | Web dashboard |
| `.picasso_keys.json` | Kraken API keys — **gitignored, never committed** |
| `balance.json` / `positions.json` / `trades.csv` / `stats.json` | Runtime state — gitignored |
| `history/` | Archived docs from the December 2025 paper/Binance-era design |

## Security

- Keys live only in `.picasso_keys.json` (gitignored). Paper mode needs no keys at all.
- Live order path validates margin eligibility with a `validate=True` dry-run at startup before arming.
- The balance sync is read-only (`fetch_balance`); live closes take the realized balance from Kraken, so fees are real.

## Disclaimer

Margin trading can lose more than your stake. This is the operator's personal bot running the operator's risk settings — it deliberately has **no artificial guardrails**: no 1x forcing, no paper fallbacks, no substituted risk values. Past performance guarantees nothing. Not financial advice.

---
**Born**: 2025-12-31, from a manually-traded fib pullback method · **Live on Kraken margin**: 2026-08-27 · **Automated with**: Claude Code
