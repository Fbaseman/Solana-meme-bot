import requests
import time
from datetime import datetime, timezone

BOT_TOKEN = '8046316024:AAHwz99rN-VZ3FDpnaYqTDught0kJ25DoBw'
CHAT_ID = '7142054583'
BIRDEYE_API_KEY = 'aa172e30a793483ca9ddc1559b400c74'

def get_dexscreener_coins():
    url = 'https://api.dexscreener.com/latest/dex/pairs/solana'
    r = requests.get(url)
    return r.json().get('pairs', [])

def get_birdeye_token_info(token_address):
    url = f'https://public-api.birdeye.so/public/token/{token_address}'
    headers = {'X-API-KEY': BIRDEYE_API_KEY}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Birdeye API error for {token_address}: {r.status_code}")
        return None

def token_age_hours(created_at_unix):
    now = datetime.now(timezone.utc).timestamp()
    return (now - created_at_unix) / 3600  # seconds to hours

def send_alert(pair):
    name = pair['baseToken']['name']
    symbol = pair['baseToken']['symbol']
    fdv = pair['fdvUsd']
    price = pair['priceUsd']
    url = pair['url']
    volume_24h = pair.get('volume', {}).get('h24', 'N/A')
    liquidity = pair.get('liquidityUsd', 'N/A')

    msg = f"🚀 *New High-Potential Solana Token!*\n\n" \
          f"*Name:* {name} ({symbol})\n" \
          f"*Market Cap:* ${fdv}\n" \
          f"*Price:* ${price}\n" \
          f"*24h Volume:* ${volume_24h}\n" \
          f"*Liquidity:* ${liquidity}\n" \
          f"[View on DexScreener]({url})"
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        'chat_id': CHAT_ID,
        'text': msg,
        'parse_mode': 'Markdown'
    })

sent = set()

while True:
    try:
        pairs = get_dexscreener_coins()
        for pair in pairs:
            pair_address = pair['pairAddress']
            if pair_address in sent:
                continue

            fdv = float(pair.get('fdvUsd') or 0)
            liquidity = float(pair.get('liquidityUsd') or 0)
            volume_24h = float(pair.get('volume', {}).get('h24') or 0)
            buys = pair.get('buyCount', 0)
            sells = pair.get('sellCount', 0)

            # Basic Dexscreener filters
            if not (fdv < 100_000 and liquidity > 2000 and volume_24h > 1000):
                continue
            if sells == 0 or buys / sells < 2:
                continue

            token_address = pair['baseToken']['address']
            token_info = get_birdeye_token_info(token_address)
            if token_info is None:
                continue

            # Holders filter
            holders = token_info.get('holders')
            if holders is None or holders < 50:
                continue

            # Age filter
            created_at = token_info.get('createdAt')
            if created_at is None or token_age_hours(created_at) > 24:
                continue

            # Liquidity lock filter
            liquidity_locked_percent = token_info.get('liquidity', {}).get('lockedPercent', 0)
            if liquidity_locked_percent < 80:
                continue

            # Passed all filters — send alert
            send_alert(pair)
            sent.add(pair_address)

        time.sleep(300)  # check every 5 minutes

    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(60)
