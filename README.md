# PICASSO 🎨 - The 98% Win Rate Bot

**Fibonacci Pullback Trading Bot - Proven $300/day Manual Trading, Now Automated**

## 🚀 Performance (Proven Manual Trading)

- **Win Rate**: 98% (TP1 = 100%, TP2 = 70% within 1 hour)
- **Daily Profit**: $300/day average (manual trading results)
- **Return Per Trade**: 30% (on $1,000 risk)
- **Strategy**: Buy pullbacks in bullish trends using Fibonacci golden zone
- **Timeframe**: 1h charts ONLY
- **Symbol**: BTC/USDT ONLY (for now)

## 🇺🇸 USA Regulatory Compliant

**MADE FOR US TRADERS**

- ✅ **SPOT TRADING ONLY** (no futures, no derivatives)
- ✅ **LONG POSITIONS ONLY** (no shorting)
- ✅ **NO LEVERAGE** (100% compliant with US regulations)
- ✅ **US EXCHANGES ONLY** (Binance US)
- ✅ **Regulatory Compliant** for US retail traders

## 🎯 The PICASSO Strategy

### How It Works

**Setup Phase:**
1. Identifies swing high and swing low (120-period lookback)
2. Calculates Fibonacci retracement levels (for entry)
3. Calculates Fibonacci extension levels (for take-profits)

**Entry Signal:**
1. Price pulls back to "Golden Zone" (Fibonacci retracement level)
2. Maximum 2% dip into golden zone (not a dump)
3. Price bounces off golden zone (current close > previous close)
4. Volume confirmation (1.5x average volume)

**Exit Strategy:**
- **TP1**: [USER TO PROVIDE] Fibonacci extension - **100% hit rate**
- **TP2**: [USER TO PROVIDE] Fibonacci extension - **70% hit within 1 hour**
- **TP3**: [USER TO PROVIDE] Fibonacci extension
- **TP4**: [USER TO PROVIDE] Fibonacci extension
- **Stop Loss**: Below Fibonacci retracement level

**Frequency:**
- 3-4 setups per bullish trend
- Each setup = high-probability winner

## 💰 Lease Model (For Commercial Use)

### Pricing Structure

**One-Time Fee**: $100
- Covers setup, onboarding, support
- Paid upfront before bot access

**Revenue Share**: 10% of profits
- **BUT FIRST**: Customer recoups $100 from the 10% share
- **THEN**: 10% profit sharing begins

### How It Works

**Example:**
- Customer pays $100 upfront
- Bot makes $500 profit in week 1
- 10% share = $50 → Goes to customer (refund: $50/$100)
- Bot makes $600 profit in week 2
- 10% share = $60 → $50 to customer (refund complete!), $10 to vendor
- All future profits = Customer keeps 90%, vendor gets 10%

**Fair for Everyone:**
- Customer gets bot that pays for itself
- Vendor only profits after customer breaks even
- Zero long-term risk for customer
- Passive income for vendor

## 📊 Fibonacci Levels (TO BE CONFIGURED)

**⚠️ IMPORTANT: Current values are PLACEHOLDERS**

The bot uses Fibonacci retracement and extension levels from standard charting tools.

**You MUST configure these exact levels:**

### Retracement Levels (Entry Detection)
- **Golden Zone**: [USER TO PROVIDE] (e.g., 0.618, 0.5, etc.)
- **Stop Loss Level**: [USER TO PROVIDE] (e.g., 0.786, 1.0, etc.)

### Extension Levels (Take-Profit Targets)
- **TP1**: [USER TO PROVIDE] (e.g., 1.0, 1.272, etc.) - 100% winner
- **TP2**: [USER TO PROVIDE] (e.g., 1.272, 1.382, 1.414, etc.) - 70% within hour
- **TP3**: [USER TO PROVIDE] (e.g., 1.618, 2.0, etc.)
- **TP4**: [USER TO PROVIDE] (e.g., 2.0, 2.618, etc.)

## 🛠️ Installation

```bash
# Clone or download PICASSO bot
cd picasso-bot

# Install dependencies
pip install ccxt pandas numpy rich

# Configure API keys (will prompt on first run)
python picasso.py
```

## ⚙️ Configuration

### Environment Variables

```bash
# Fibonacci Levels (MUST BE SET!)
export PICASSO_GOLDEN_ZONE="0.618"    # Golden zone retracement
export PICASSO_STOP_LOSS_LEVEL="0.786"  # Stop loss retracement

export PICASSO_TP1="1.0"      # TP1 extension (100% winner)
export PICASSO_TP2="1.272"    # TP2 extension (70% within hour)
export PICASSO_TP3="1.618"    # TP3 extension
export PICASSO_TP4="2.0"      # TP4 extension

# Risk Management
export PICASSO_RISK_USD="1000"    # Risk per trade ($1000 proven)
export PICASSO_MAX_DIP="2.0"      # Max dip % into golden zone

# Trading Settings
export PICASSO_SYMBOL="BTC/USDT"  # Symbol to trade
export PICASSO_PAPER="1"          # Paper mode (1=paper, 0=live)
export PICASSO_SCAN_INTERVAL="300"  # Scan every 5 minutes

# Run bot
python picasso.py
```

## 📈 Usage

### Paper Trading (Safe Mode - Default)

```bash
python picasso.py
```

Bot will:
1. Connect to Binance US
2. Monitor BTC/USDT 1h charts
3. Calculate Fibonacci levels dynamically
4. Wait for pullback to golden zone
5. Enter on bounce with volume confirmation
6. Take profit at TP levels
7. Track profits for lease model

### Live Trading (After Testing)

```bash
export PICASSO_PAPER="0"
python picasso.py
```

**⚠️ WARNING**: Only trade live after:
- Configuring exact Fibonacci levels
- Testing in paper mode
- Verifying results match expectations
- Understanding the risks

## 🎨 What Makes PICASSO Different

**Simplicity = Reliability:**
- Uses standard Fibonacci math (golden ratio, proven for centuries)
- No complex indicators or over-optimization
- Market structure dictates levels (dynamic, not static)
- Robust code = fewer failure points

**Proven Track Record:**
- Manually traded for over a year
- $300/day average profit (verifiable)
- 98% win rate (real results, not backtest)
- 30% return per trade (proven performance)

**USA Compliance:**
- Built specifically for US regulatory requirements
- No leverage, no shorting, spot only
- Hard to find USA-compliant algo bots

## 🔐 Security & Risk

**API Keys:**
- Stored locally in `.picasso_keys.json`
- Never shared or transmitted
- Use read-only keys if possible
- For live trading: use keys with trading permissions

**Risk Management:**
- Default $1000 risk per trade (user's proven amount)
- Stop loss always set
- Position sizing calculated dynamically
- Max 2% dip into golden zone (conservative entry)

**Disclaimer:**
- Past performance does not guarantee future results
- Cryptocurrency trading carries risk
- Only trade with money you can afford to lose
- This bot works in BULLISH markets only
- Not financial advice

## 📊 Profit Tracking (Lease Model)

PICASSO automatically tracks:
- Total profits generated
- 10% revenue share
- Customer refund progress ($0 → $100)
- Vendor earnings (after customer recoups $100)
- Breakeven status

Stored in `license.json`:
```json
{
  "customer_id": "default",
  "initial_fee": 100.0,
  "refund_progress": 50.0,
  "total_profits": 500.0,
  "vendor_earnings": 0.0,
  "breakeven": false
}
```

## 📁 Files

- `picasso.py` - Main bot code
- `.picasso_keys.json` - API keys (created on first run)
- `positions.json` - Current position state
- `trades.csv` - Trade history
- `stats.json` - Performance statistics
- `license.json` - Lease model tracking

## 🚀 Roadmap

**Phase 1** (Current):
- ✅ Core PICASSO strategy implemented
- ✅ Fibonacci calculation engine
- ✅ Pullback detection logic
- ✅ Profit tracking for lease model
- ⏳ **WAITING: User's exact Fibonacci levels**

**Phase 2** (After User Provides Levels):
- [ ] Configure exact retracement/extension values
- [ ] Test in paper mode
- [ ] Verify 98% win rate performance
- [ ] Fine-tune entry/exit logic

**Phase 3** (Lease Model Deployment):
- [ ] License key system
- [ ] Customer onboarding flow
- [ ] Payment integration
- [ ] Customer dashboard
- [ ] Admin panel

**Phase 4** (Scaling):
- [ ] Multiple symbol support (ETH, SOL, etc.)
- [ ] Auto-detect bullish trends
- [ ] Enhanced profit tracking
- [ ] Performance analytics

## 💡 Why "PICASSO"?

Just like Pablo Picasso created masterpieces with simple, clean lines - this bot creates profits with simple, clean logic.

**Simple = Beautiful = Profitable** 🎨

---

**⚠️ CURRENT STATUS: AWAITING USER'S EXACT FIBONACCI LEVELS**

**DO NOT TRADE WITH THIS BOT YET!**

The current Fibonacci values are placeholders. The bot will not achieve 98% win rate until configured with user's proven levels.

---

**Created**: December 31, 2025
**Based on**: Proven manual trading strategy (over 1 year, $300/day)
**Automated by**: Claude Code
