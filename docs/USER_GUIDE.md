# Sentinel-X User Guide
## Complete Documentation for Traders

### 📚 Table of Contents
1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [License Activation](#license-activation)
4. [Configuration](#configuration)
5. [Connecting to MT5](#connecting-to-mt5)
6. [Trading Basics](#trading-basics)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)
10. [Support](#support)

---

## Getting Started

### What is Sentinel-X?
Sentinel-X is an AI-powered trading bridge that connects MetaTrader 5 (MT5) with advanced language models to provide intelligent trading signals and automated analysis.

### Key Features
- 🤖 **AI-Powered Analysis** - Uses LLMs to analyze market conditions
- 📊 **RAG Knowledge Base** - Retrieves proven trading strategies
- 🔄 **Auto-Trading Bridge** - Seamlessly connects to MT5
- 🔒 **License Management** - Secure hardware-locked activation
- 📈 **Risk Management** - Built-in prop firm compliance rules
- ⚡ **Fast API** - gRPC bridge for millisecond execution

### System Requirements
- **OS:** Windows 10/11 (recommended) or Linux
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 500MB free space
- **Network:** Stable internet connection
- **Broker:** MT5 account (demo or live)

---

## Installation

### Option 1: Pre-built Executable (Recommended for Windows)
1. Download `SentinelX.exe` from official website
2. Run installer
3. Follow setup wizard
4. Launch from Start Menu

### Option 2: Python Installation (Advanced Users)
```bash
# Clone repository
git clone https://github.com/sentinel-x/sentinel-x.git
cd sentinel-x

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run GUI
python gui.py
```

### Option 3: Docker (Coming Soon)
```dockerfile
# Not yet available
docker pull sentinelx/sentinel-x:latest
```

---

## License Activation

### Trial License (Free)
1. Open Sentinel-X GUI
2. Go to **License tab** (first tab)
3. Click **"Start Free Trial"**
4. Status changes to "TRIAL ACTIVE (7 days)"
5. Start using immediately

**Limitations:**
- 7 days duration
- 50 trades maximum
- Basic features only
- One trial per device

### PRO License (Lifetime)
1. Purchase from authorized reseller
2. Receive email with License Key (SNTL-X-XXXX-XXXX-XXXX-XXXX)
3. Open Sentinel-X GUI
4. Go to **License tab**
5. Paste license key in input field
6. Click **"Activate"**
7. Wait for confirmation: "PRO license activated successfully"
8. Restart application if prompted

**Features:**
- Lifetime validity (never expires)
- Unlimited trades
- Advanced AI strategies
- Email support (48h response)
- Updates for current version

### ENTERPRISE License (Lifetime)
Same activation steps as PRO, but includes:
- White-label option
- Premium support (24h response)
- Custom strategy development
- Priority feature requests

### Checking License Status
```python
# In GUI
License tab → Status card shows:
- Current tier (TRIAL/PRO/ENTERPRISE)
- Days remaining or "Lifetime"
- Trade limit status
- Features list
```

### Hardware Locking
**IMPORTANT: License is locked to FIRST device activated on.**

| Scenario | Result | Can Transfer? |
|----------|--------|---------------|
| Activate on Device A | ✓ Works on Device A | - |
| Try to use on Device B | ✗ Error: HW mismatch | ❌ No |
| Transfer to new device | ✗ Not allowed | ❌ No |
| Computer upgrade | ✗ Requires new license | Special case |

**Why?** Prevents license sharing and piracy.

### Troubleshooting Activation

**Error: "License corrupted"**
- Cause: Tampered license file
- Fix: Re-activate with valid key

**Error: "Expired"**
- Cause: Trial expired or system time changed
- Fix: Purchase PRO/ENTERPRISE license

**Error: "Hardware mismatch"**
- Cause: Trying to use on different device
- Fix: Cannot transfer. Purchase new license.

---

## Configuration

### Initial Setup

1. **API Configuration**
   - Go to **Dashboard tab**
   - Click **"Configure API"**
   - Select AI Provider (OpenAI, Anthropic, etc.)
   - Enter API key
   - Click **"Test Connection"**
   - Save configuration

2. **Broker Configuration**
   ```
   Dashboard tab → MT5 Settings:
   - Enable AutoTrading: ✅
   - Allow DLL Imports: ✅
   - Server: Your broker's server
   - Account: Your account number
   - Password: Your password
   ```

3. **Trading Rules**
   ```
   Dashboard tab → Trading Rules:
   - Max daily loss: 4% (prop firm rule)
   - Max trade size: 0.1 lots (adjust as needed)
   - SL pips: 20
   - TP pips: 40
   - Enabled symbols: EURUSD, GBPUSD, USDJPY
   ```

4. **Knowledge Base**
   ```
   Knowledge Base tab:
   - Upload trading strategy files (.txt, .md)
   - Click "Scan Knowledge"
   - Check ingestion status
   - Files will be used for AI analysis
   ```

### Saving Configuration
- Click **"Save Configuration"** button
- Config auto-saves on changes
- Backup file: `config/config.json`

---

## Connecting to MT5

### Step 1: Install Sentinel-X EAs
1. Copy EAs from `mql5/Experts/Sentinel-X/`
2. Paste to MT5: `File → Open Data Folder → MQL5 → Experts`
3. Restart MT5
4. EAs appear in Navigator panel

### Step 2: Configure MQL5 Bridge
```bash
# In MT5 EA settings:
Server URL: http://localhost:8000/api/v1/analyze
Shared Secret: (from config.json)
Symbol: EURUSD
Timeframe: H4
```

### Step 3: Enable WebRequests
```
MT5 → Tools → Options → Expert Advisors:
- Allow WebRequest: ✅
- Add URL: http://localhost:8000
```

### Step 4: Test Connection
```bash
# In MT5 terminal
SentinelX_Bridge EURUSD,H4: CONNECTED
SentinelX_Bridge Server ready on port 8000
```

### Troubleshooting Connection

**Error: "Connection refused"**
- Cause: Sentinel-X server not running
- Fix: Start server from GUI (Dashboard tab → Start Server)

**Error: "401 Unauthorized"**
- Cause: Wrong shared secret
- Fix: Check config.json → server.shared_secret

**Error: "404 Not Found"**
- Cause: Wrong endpoint
- Fix: Verify URL in MQL5 EA settings

---

## Trading Basics

### How It Works
1. **MT5 sends market data** to Sentinel-X API
2. **AI analyzes** using RAG + strategy knowledge
3. **Judge evaluates** in 3 tiers:
   - Tier 1 (50%): Market structure (MA, highs/lows)
   - Tier 2 (30%): Supply/Demand zones (from RAG)
   - Tier 3 (20%): AI narrative analysis
4. **Signal generated**: BUY, SELL, HOLD, CLOSE
5. **MT5 executes** if signal meets criteria

### Signal Format
```json
{
  "action": "BUY|SELL|HOLD|CLOSE",
  "lot_size": 0.01,
  "sl": 1.2345,
  "tp": 1.2400,
  "reason": "Bullish structure + Liquidity grab + Momentum confirmation",
  "confidence_score": 0.85
}
```

### Understanding Signals
- **High confidence (0.7-1.0)**: Strong setup
- **Medium (0.4-0.7)**: Moderate setup
- **Low (0.0-0.4)**: Weak setup, trade with caution

### Risk Management (Built-in)
- **Daily Max Loss**: 4% (prop firm compliant)
- **Max Drawdown**: Locks trading if exceeded
- **News Filter**: Stops trading 30min before/after high-impact news
- **Virtual SL/TP**: Faster execution, broker can't see your levels

### Monitoring Performance

**Stats Tab shows:**
- Total trades
- Win rate %
- PnL (Profit & Loss)
- Average win/loss
- Runup/drawdown
- Consecutive losses

**Monitoring Tab shows:**
- Reasoning logs for each trade
- AI decision transparency
- Market structure at signal time
- Confidence score history

---

## Advanced Features

### Adversarial Reasoning
Before executing, system runs two AI agents:
- **Pro Agent**: Argues why trade will succeed
- **Contra Agent**: Argues why trade will fail
- **Judge**: Only executes if Pro > Contra

This prevents false positives and overtrading.

### Knowledge Base Optimization
You can improve AI performance by:

1. **Upload proven strategies**
   ```
   Knowledge Base tab → Upload File
   Upload: supply_demand_zones.txt
   Upload: order_block_strategy.md
   ```

2. **Add structure definitions**
   ```
   Add files like:
   - market_structure_highs_lows.md
   - liquidity_zones.txt
   - fair_value_gaps.txt
   ```

3. **Scan & Ingest**
   ```
   Knowledge Base tab → Scan Knowledge
   Wait for: "Ingested X files"
   ```

**Pro Tip:** Quality > Quantity. Upload proven strategies only.

### Telegram Alerts

**Setup:**
```
Dashboard tab → Configure Telegram
- Enter bot token
- Enter chat ID
- Test notification
- Save
```

**Alerts sent for:**
- Trade signals (BUY/SELL)
- Trade reports (Open/Close/PnL)
- System errors
- License expiry warnings

### Trading Dashboard

**Charts Tab shows:**
- Live price charts
- Indicator overlays (MA, RSI, etc.)
- Signal history markers
- PnL visualization

**Customizable:**
```
Charts tab → Settings:
- Timeframe: M5, M15, H1, H4, D1
- Indicators: MA (20, 50, 200), RSI, MACD
- Colors: Dark/Light mode
- Refresh: Every candle close
```

---

## Troubleshooting

### Common Issues

**"License Invalid" Error**
```
Causes:
1. Expired trial
2. Hardware mismatch
3. Corrupted license file

Solutions:
1. Purchase PRO/ENTERPRISE
2. Cannot transfer - buy new license
3. Re-activate with valid key
```

**"Server Not Running"**
```
Check:
1. GUI Dashboard tab → Start Server (click button)
2. Firewall blocking port 8000
3. Port conflict (check with netstat -ano | findstr 8000)

Fix:
1. Click Start Server
2. Allow through firewall
3. Change port in config.json
```

**"MT5 Says 'Disconnected'"**
```
Check:
1. Sentinel-X server running
2. Shared secret matches config.json
3. Symbol enabled in config
4. AutoTrading enabled in MT5

Fix:
1. Start Sentinel-X server
2. Copy correct secret from config.json
3. Add symbol to enabled_symbols list
4. Press AutoTrading button in MT5 toolbar
```

**"Slow AI Response"**
```
Causes:
1. API rate limits (OpenAI, Anthropic)
2. Complex prompt/knowledge base
3. Internet connectivity
4. Server overload

Fix:
1. Add payment method to API account
2. Reduce knowledge base size
3. Check internet speed
4. Use faster provider (OpenAI GPT-3.5 vs GPT-4)
```

**"Too Many Trades"**
```
Cause: AI overtrading

Fix:
1. Lower sensitivity in Dashboard settings
2. Increase confidence score threshold (0.7+)
3. Filter signals with confirmation indicators
4. Use higher timeframe (H1/H4 vs M15)
```

### Performance Optimization

**Speed Up AI Analysis:**
```
1. Reduce knowledge base size (keep proven strategies only)
2. Use faster AI model (GPT-3.5 instead of GPT-4)
3. Pre-filter market data before sending
4. Use less candles in analysis (100 vs 1000)
```

**Reduce False Signals:**
```
1. Increase confidence score threshold
2. Require confirmation from multiple Tiers
3. Filter by minimum R:R ratio (1:2 minimum)
4. Avoid trading during news events
```

---

## FAQ

**Q: How do I activate my license?**
A: Open GUI → License tab → Paste key → Activate

**Q: Can I transfer license to another computer?**
A: ❌ No. License is hardware-locked permanently.

**Q: What happens if my computer breaks?**
A: Contact support with proof. May require new license purchase (exceptions for PRO+ENTERPRISE).

**Q: Is there a money-back guarantee?**
A: ✅ 30 days if NOT activated (minus 10% fee). No refunds after activation.

**Q: Does it guarantee profits?**
A: ❌ **NO.** Trading is HIGH RISK. Can lose everything. No guarantees. AI helps but markets are unpredictable.

**Q: How accurate are AI signals?**
A: Varies by market conditions. Typically 55-65% accuracy. Not foolproof. Use with risk management.

**Q: Can I use with any broker?**
A: ✅ Any MT5 broker that allows EAs. Check broker's terms.

**Q: Does it work with prop firms?**
A: ✅ Yes. Built-in 4% daily loss limit (prop firm compliant).

**Q: Can I customize strategies?**
A: ✅ Yes. Upload your strategy files to Knowledge Base. AI uses them.

**Q: How often does it trade?**
A: Depends on market conditions and config. Trades per candle close (M15 = ~4 trades/hour if conditions meet criteria).

**Q: What if internet disconnects?**
A: Trades already open remain open. New signals won't be executed until reconnected.

---

## Support

### Channels
- **Email:** support@sentinel-x.bot
- **Discord:** https://discord.gg/sentinel-x
- **Documentation:** https://sentinel-x.bot/docs

### Response Times
- **TRIAL:** Community support (Discord only)
- **PRO:** Email support within 48 hours
- **ENTERPRISE:** Priority support within 24 hours

### Before Contacting Support
1. Check this User Guide
2. Review Troubleshooting section
3. Check FAQs
4. Provide: License Key, Error screenshots, logs

### Bug Reports
```
Email: bugs@sentinel-x.bot
Include:
- Screenshot of error
- Steps to reproduce
- License Key
- Log files (config/logs/)
```

---

## Glossary

**EAs:** Expert Advisors (MT5 automation scripts)
**RAG:** Retrieval-Augmented Generation
**LLM:** Large Language Model (AI)
**PnL:** Profit and Loss
**SL:** Stop Loss
**TP:** Take Profit
**HWID:** Hardware ID (unique device fingerprint)
**API:** Application Programming Interface
**gRPC:** High-performance RPC framework
**Prop Firm:** Proprietary trading firm

---

**Document Version:** 1.0  
**Last Updated:** February 6, 2026  
**Software Version:** Sentinel-X v1.0+  
**Support Email:** support@sentinel-x.bot