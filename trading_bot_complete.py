import requests
import json
import time
from datetime import datetime
import os

# ============= CONFIGURATION =============
TELEGRAM_BOT_TOKEN = "8812880794:AAE4-bFbmCGzTIsQrLydg1MW3TjM1rjBeY4"
TELEGRAM_CHAT_ID = "-1004317050644"

# Paper trading settings
PAPER_BALANCE = 2000.00      # Starting paper money
BUY_AMOUNT = 50.00           # $50 per trade
TAKE_PROFIT = 20             # 20% profit target
STOP_LOSS = 10               # 10% stop loss
MAX_POSITIONS = 10           # Max positions at once
SCAN_INTERVAL = 180          # Seconds between scans (3 minutes)

# ============= COINS TO TRACK =============
COINS = {
    "bitcoin": {"symbol": "BTC", "chain": "ethereum"},
    "ethereum": {"symbol": "ETH", "chain": "ethereum"},
    "solana": {"symbol": "SOL", "chain": "solana"},
    "binancecoin": {"symbol": "BNB", "chain": "bsc"},
    "matic-network": {"symbol": "MATIC", "chain": "polygon"},
    "avalanche-2": {"symbol": "AVAX", "chain": "avalanche"},
    "arbitrum": {"symbol": "ARB", "chain": "arbitrum"},
    "optimism": {"symbol": "OP", "chain": "optimism"},
    "cardano": {"symbol": "ADA", "chain": "cardano"},
    "chainlink": {"symbol": "LINK", "chain": "ethereum"}
}

# ============= CHAINS TO SCAN FOR TOKENS =============
CHAINS_TO_SCAN = ["solana", "ethereum", "bsc", "polygon", "avalanche", "arbitrum", "optimism"]

# ============= STATE MANAGEMENT =============
SAVE_FILE = "bot_state.json"

def load_state():
    """Load saved state from file"""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_state(state):
    """Save state to file"""
    with open(SAVE_FILE, 'w') as f:
        json.dump(state, f)

# Load or initialize state
saved_state = load_state()
if saved_state:
    balance = saved_state.get("balance", PAPER_BALANCE)
    positions = saved_state.get("positions", [])
    total_trades = saved_state.get("total_trades", 0)
    winning_trades = saved_state.get("winning_trades", 0)
    total_profit = saved_state.get("total_profit", 0)
    print(f"✅ Loaded saved state: {len(positions)} positions, ${balance:.2f} balance")
else:
    balance = PAPER_BALANCE
    positions = []
    total_trades = 0
    winning_trades = 0
    total_profit = 0
    print("📊 Starting fresh with $2000 paper money")

# ============= TELEGRAM FUNCTIONS =============
def send_telegram(message):
    """Send message to Telegram channel"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, json=data)
        print("✅ Telegram sent")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# ============= PRICE FUNCTIONS =============
def get_coin_prices():
    """Get prices for all tracked coins"""
    try:
        ids = ",".join(COINS.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        data = requests.get(url).json()
        
        prices = {}
        for coin_id, info in COINS.items():
            price = data.get(coin_id, {}).get("usd", 0)
            prices[info["symbol"]] = price
        return prices
    except Exception as e:
        print(f"❌ Price error: {e}")
        return {}

def get_token_price(address):
    """Get current price of a token by address"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        data = requests.get(url).json()
        pairs = data.get("pairs", [])
        if pairs:
            return float(pairs[0].get("priceUsd", 0))
    except:
        pass
    return None

# ============= SCANNING FUNCTIONS =============
def scan_tokens(chain="solana"):
    """Scan for tokens on a specific chain"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={chain}"
        data = requests.get(url).json()
        
        tokens = []
        for pair in data.get("pairs", []):
            try:
                symbol = pair.get("baseToken", {}).get("symbol", "")
                price = float(pair.get("priceUsd", 0))
                volume = float(pair.get("volume", {}).get("h24", 0))
                liquidity = float(pair.get("liquidity", {}).get("usd", 0))
                address = pair.get("baseToken", {}).get("address", "")
                chain_id = pair.get("chainId", "")
                
                # Volume threshold lowered to 50k
                if (symbol and price > 0 and volume > 50000 and liquidity > 20000):
                    tokens.append({
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "liquidity": liquidity,
                        "address": address,
                        "chain": chain_id
                    })
            except:
                continue
        return tokens
    except Exception as e:
        print(f"❌ Scan error for {chain}: {e}")
        return []

# ============= TRADING FUNCTIONS =============
def paper_buy(token, price):
    """Execute a paper buy order"""
    global balance, positions, total_trades
    
    if balance < BUY_AMOUNT:
        send_telegram(f"⚠️ Not enough balance! Need ${BUY_AMOUNT}, have ${balance:.2f}")
        return False
    
    if len(positions) >= MAX_POSITIONS:
        send_telegram(f"⚠️ Max positions ({MAX_POSITIONS}) reached")
        return False
    
    amount_to_spend = min(BUY_AMOUNT, balance)
    token_amount = amount_to_spend / price if price > 0 else 0
    
    position = {
        "token": token['symbol'],
        "address": token['address'],
        "chain": token.get('chain', 'unknown'),
        "buy_price": price,
        "amount": token_amount,
        "spent": amount_to_spend,
        "entry_time": datetime.now().isoformat()
    }
    positions.append(position)
    balance -= amount_to_spend
    total_trades += 1
    
    # Save state
    save_state({
        "balance": balance,
        "positions": positions,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "total_profit": total_profit
    })
    
    message = f"""
🟢 **PAPER BUY EXECUTED**

💰 Token: {token['symbol']}
🔗 Chain: {token.get('chain', 'unknown')}
📊 Buy Price: ${price:.6f}
📦 Amount: {token_amount:.4f} tokens
💵 Spent: ${amount_to_spend:.2f}
💳 Balance: ${balance:.2f}
📈 Trade #{total_trades}
"""
    send_telegram(message)
    print(f"✅ Paper buy: {token['symbol']} @ ${price:.6f}")
    return True

def paper_sell(position, current_price):
    """Execute a paper sell order"""
    global balance, positions, total_trades, winning_trades, total_profit
    
    sell_value = position['amount'] * current_price
    profit = sell_value - position['spent']
    profit_pct = (profit / position['spent']) * 100 if position['spent'] > 0 else 0
    
    balance += sell_value
    total_profit += profit
    if profit > 0:
        winning_trades += 1
    
    positions.remove(position)
    
    # Save state
    save_state({
        "balance": balance,
        "positions": positions,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "total_profit": total_profit
    })
    
    emoji = "🟢" if profit > 0 else "🔴"
    message = f"""
{emoji} **PAPER SELL EXECUTED**

💰 Token: {position['token']}
🔗 Chain: {position.get('chain', 'unknown')}
📊 Sell Price: ${current_price:.6f}
📦 Amount: {position['amount']:.4f} tokens
💵 Received: ${sell_value:.2f}
📈 Profit: ${profit:.2f} ({profit_pct:+.2f}%)
💳 New Balance: ${balance:.2f}
"""
    send_telegram(message)
    print(f"✅ Paper sell: {position['token']} | Profit: ${profit:.2f}")
    return True

def check_positions(tokens):
    """Check existing positions for profit/loss targets"""
    if not positions or not tokens:
        return
    
    # Create price map
    price_map = {}
    for token in tokens:
        price_map[token['address']] = token['price']
    
    for position in positions[:]:
        current_price = price_map.get(position['address'])
        if not current_price:
            # Try to get price directly
            current_price = get_token_price(position['address'])
            if not current_price:
                continue
        
        profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
        
        if profit_pct >= TAKE_PROFIT:
            paper_sell(position, current_price)
            send_telegram(f"🎯 Take profit for {position['token']} at {profit_pct:.1f}%")
        elif profit_pct <= -STOP_LOSS:
            paper_sell(position, current_price)
            send_telegram(f"🛑 Stop loss for {position['token']} at {profit_pct:.1f}%")

# ============= MAIN LOOP =============
def main_loop():
    global balance, positions, total_trades, winning_trades, total_profit
    
    # Startup message
    send_telegram("🚀 **COMPLETE MULTI-CHAIN PAPER TRADING BOT**")
    send_telegram(f"💰 Starting Balance: ${balance:.2f}")
    send_telegram(f"📊 Tracking: {', '.join(COINS.keys())}")
    send_telegram(f"🔗 Scanning: {', '.join(CHAINS_TO_SCAN)}")
    send_telegram(f"🎯 Take Profit: {TAKE_PROFIT}% | Stop Loss: {STOP_LOSS}%")
    send_telegram(f"📈 Max Positions: {MAX_POSITIONS}\n")
    
    last_prices = {}
    last_save = time.time()
    
    while True:
        try:
            # ---------- 1. Get prices ----------
            prices = get_coin_prices()
            
            if prices:
                price_msg = "💰 **Prices:**\n"
                for symbol, price in prices.items():
                    change = ""
                    if symbol in last_prices and last_prices[symbol]:
                        pct = ((price - last_prices[symbol]) / last_prices[symbol]) * 100
                        change = f" ({pct:+.2f}%)"
                    price_msg += f"  • {symbol}: ${price:.2f}{change}\n"
                    last_prices[symbol] = price
                send_telegram(price_msg)
            
            # ---------- 2. Scan chains ----------
            all_tokens = []
            for chain in CHAINS_TO_SCAN:
                tokens = scan_tokens(chain)
                if tokens:
                    print(f"🔍 Found {len(tokens)} tokens on {chain}")
                    all_tokens.extend(tokens)
            
            # ---------- 3. Check positions ----------
            if all_tokens:
                check_positions(all_tokens)
            
            # ---------- 4. Look for new entries ----------
            if len(positions) < MAX_POSITIONS and all_tokens:
                for token in all_tokens[:5]:
                    # Lowered volume threshold to 50k
                    if token['volume'] > 50000 and token['liquidity'] > 20000:
                        existing = any(p['address'] == token['address'] for p in positions)
                        if not existing:
                            paper_buy(token, token['price'])
                            time.sleep(2)
                            break
            
            # ---------- 5. Portfolio summary ----------
            if positions:
                msg = f"📊 **Open Positions:** {len(positions)}/{MAX_POSITIONS}\n"
                msg += f"💰 Balance: ${balance:.2f}\n"
                total_value = balance
                for p in positions:
                    msg += f"  • {p['token']} ({p.get('chain', 'unknown')}): {p['amount']:.4f} tokens @ ${p['buy_price']:.6f}\n"
                send_telegram(msg)
            else:
                send_telegram(f"💰 Balance: ${balance:.2f} | No open positions")
            
            # ---------- 6. Save state periodically ----------
            if time.time() - last_save > 300:  # Save every 5 minutes
                save_state({
                    "balance": balance,
                    "positions": positions,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "total_profit": total_profit
                })
                last_save = time.time()
                print("💾 State saved")
            
            # ---------- 7. Wait ----------
            print(f"⏰ Next scan in {SCAN_INTERVAL} seconds...")
            time.sleep(SCAN_INTERVAL)
            
        except KeyboardInterrupt:
            # Final summary
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            summary = f"""
🛑 **BOT STOPPED**

📊 **Final Stats:**
💰 Balance: ${balance:.2f}
📈 Total Trades: {total_trades}
✅ Winning: {winning_trades}
🏆 Win Rate: {win_rate:.1f}%
💵 Total Profit: ${total_profit:.2f}
"""
            send_telegram(summary)
            
            # Save final state
            save_state({
                "balance": balance,
                "positions": positions,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "total_profit": total_profit
            })
            print("\n✅ Bot stopped. State saved.")
            break
            
        except Exception as e:
            error_msg = f"❌ Bot error: {str(e)}"
            print(error_msg)
            send_telegram(error_msg)
            time.sleep(60)

# ============= RUN =============
if __name__ == "__main__":
    print("🚀 COMPLETE MULTI-CHAIN PAPER TRADING BOT")
    print(f"💰 Starting with ${balance:.2f} paper money")
    print(f"📊 Tracking: {len(COINS)} coins")
    print(f"🔗 Scanning: {len(CHAINS_TO_SCAN)} chains")
    print(f"📈 Max Positions: {MAX_POSITIONS}")
    print("📱 Press Ctrl+C to stop\n")
    
    main_loop()
