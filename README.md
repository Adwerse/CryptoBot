# 🤖 CryptoBot - Multi-Currency Price Tracker

A powerful Telegram bot for real-time cryptocurrency price tracking with multi-user support and personalized settings.

## ✨ Features

### 🪙 Multi-Cryptocurrency Support
- **Bitcoin (BTC)** - The original cryptocurrency
- **Ethereum (ETH)** - Smart contract platform
- **Solana (SOL)** - High-performance blockchain
- **XRP** - Digital payment protocol

### 📊 Real-Time Price Updates
- Live WebSocket connections to Binance API
- Real-time price updates for all supported cryptocurrencies
- EUR pricing for European users
- Automatic reconnection handling

### 👥 Multi-User Architecture
- Individual user preferences and settings
- Persistent data storage across bot restarts
- User-specific cryptocurrency selection
- Admin panel for monitoring and statistics

### 🔔 Smart Notifications
- Real-time price update messages
- Optimized update frequency to prevent spam
- Message deduplication to avoid unnecessary updates
- Automatic message positioning

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Adwerse/CryptoBot.git
   cd CryptoBot
   ```

2. **Install dependencies:**
   ```bash
   pip install aiogram websockets python-dotenv requests
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   ADMIN_ID=your_telegram_user_id_here  # Optional, for admin features
   ```

4. **Run the bot:**
   ```bash
   python main_multiuser.py
   ```

## 📋 Commands

### User Commands
- `/start` - Welcome message and bot introduction
- `/select_crypto` - Choose your preferred cryptocurrency
- `/btc` - Select Bitcoin (BTC)
- `/eth` - Select Ethereum (ETH)
- `/sol` - Select Solana (SOL)
- `/xrp` - Select XRP
- `/checkCrypto` - Get current price of your selected crypto
- `/start_updates` - Enable real-time price updates
- `/stop_updates` - Disable real-time price updates
- `/status` - View your subscription status and settings

### Admin Commands
- `/admin_stats` - Detailed bot statistics and user analytics

## 🏗️ Architecture

### WebSocket Connections
The bot maintains separate WebSocket connections for each supported cryptocurrency:
- `wss://stream.binance.com:9443/ws/btceur@ticker`
- `wss://stream.binance.com:9443/ws/etheur@ticker`
- `wss://stream.binance.com:9443/ws/soleur@ticker`
- `wss://stream.binance.com:9443/ws/xrpeur@ticker`

### Data Structure
```json
{
  "user_id": {
    "active": true,
    "crypto": "BTC",
    "message_id": 123,
    "last_text": "..."
  }
}
```

### Performance Optimizations
- **Update Frequency Limiting**: Prevents excessive API calls
- **Message Deduplication**: Avoids sending identical updates
- **Automatic Reconnection**: Handles WebSocket disconnections gracefully
- **Memory Management**: Efficient data storage and retrieval

## 🔧 Configuration

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot API token | ✅ Yes |
| `ADMIN_ID` | Telegram user ID for admin access | ❌ Optional |

### Supported Trading Pairs
| Cryptocurrency | Symbol | Binance Pair |
|----------------|--------|--------------|
| Bitcoin | BTC | BTCEUR |
| Ethereum | ETH | ETHEUR |
| Solana | SOL | SOLEUR |
| XRP | XRP | XRPEUR |

## 📊 Usage Examples

### Basic Usage
1. Start the bot with `/start`
2. Select your preferred cryptocurrency with `/select_crypto`
3. Choose a crypto (e.g., `/btc` for Bitcoin)
4. Enable real-time updates with `/start_updates`
5. Check your status with `/status`

### Real-Time Updates
Once enabled, the bot will continuously update a dedicated message with:
- Current price in EUR
- Last update timestamp
- Real-time indicator

## 🛠️ Development

### Project Structure
```
CryptoBot/
├── main_multiuser.py      # Main bot application
├── users_data.json        # User data persistence
├── .env                   # Environment configuration
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

### Key Components
- **WebSocket Manager**: Handles multiple cryptocurrency streams
- **User Manager**: Manages user preferences and data
- **Message Handler**: Optimizes Telegram message updates
- **Error Handler**: Robust error handling and logging

### Adding New Cryptocurrencies
1. Add entry to `SUPPORTED_CRYPTOS` dictionary
2. Ensure Binance supports the EUR trading pair
3. Add command handler for the new crypto
4. Update documentation

## 🔍 Monitoring & Analytics

### Admin Features
- Total user count and active subscriptions
- Cryptocurrency preference distribution
- WebSocket connection status
- Real-time price monitoring
- System performance metrics

### Logging
The bot provides comprehensive logging:
- WebSocket connection status
- User activity tracking
- Error reporting and debugging
- Performance monitoring

## 🐛 Troubleshooting

### Common Issues

**Bot not responding:**
- Check if `BOT_TOKEN` is correctly set
- Verify internet connection
- Check bot logs for errors

**WebSocket connection issues:**
- Monitor connection logs
- Check Binance API status
- Verify firewall settings

**Price not updating:**
- Check WebSocket connection status
- Verify user has active subscription
- Review error logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 🙏 Acknowledgments

- [Binance API](https://binance-docs.github.io/apidocs/) for cryptocurrency data
- [aiogram](https://aiogram.dev/) for Telegram Bot API wrapper
- [WebSockets](https://websockets.readthedocs.io/) for real-time connections

## 📈 Version History

### v0.2 (Current)
- ✅ Multi-cryptocurrency support (BTC, ETH, SOL, XRP)
- ✅ User-specific crypto selection
- ✅ Enhanced admin panel
- ✅ Improved message handling
- ✅ Better error handling

### v0.1
- ✅ Basic BTC price tracking
- ✅ Single-user support
- ✅ WebSocket integration

---

<div align="center">
  <p>Made with ❤️ for the crypto community</p>
  <p>
    <a href="Adwerse.2005@gmail.com">Report Bug</a> •
    <a href="Adwerse.2005@gmail.com">Request Feature</a>
  </p>
</div>