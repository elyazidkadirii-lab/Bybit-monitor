"""
Bybit P2P USDT/TRY spread check - ONE run (for GitHub Actions).
Reads TG_TOKEN and TG_CHAT_ID from environment (GitHub Secrets).
Only reads prices and sends a Telegram message. Never moves money.
"""
import os, sys, requests

TRADE_USD      = 500
MIN_PROFIT_PCT = 1.5
FEE_PCT        = 0.0
PAYMENT_IDS    = []
MIN_COMPLETION = 90

URL = "https://api2.bybit.com/fiat/otc/item/online"
TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_CHAT = os.getenv("TG_CHAT_ID", "")
ALWAYS = os.getenv("ALWAYS_NOTIFY", "") == "true"   # manual test run


def fetch(side):
    # side "1" = ads you BUY USDT from, "0" = ads you SELL USDT to
    # (if prices look reversed on first run, swap the two values below)
    body = {
        "userId": "", "tokenId": "USDT", "currencyId": "TRY",
        "payment": PAYMENT_IDS, "side": side, "size": "20", "page": "1",
        "amount": str(TRADE_USD * 50), "authMaker": False, "canTrade": False,
    }
    r = requests.post(URL, json=body, timeout=20)
    r.raise_for_status()
    items = r.json()["result"]["items"]
    good = []
    for it in items:
        try:
            if float(it.get("recentExecuteRate", 100)) < MIN_COMPLETION:
                continue
            if float(it["quantity"]) < TRADE_USD:
                continue
            good.append((float(it["price"]), it["nickName"]))
        except (KeyError, ValueError):
            continue
    return good


def tg(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[telegram not configured]\n" + text)
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text}, timeout=15,
    )


def main():
    try:
        buy_ads = fetch("1")
        sell_ads = fetch("0")
    except Exception as e:
        print("error:", e)
        if ALWAYS:
            tg(f"⚠️ تعذّر الوصول إلى Bybit من GitHub:\n{e}")
        sys.exit(0)

    if not buy_ads or not sell_ads:
        print("no ads matched filters")
        if ALWAYS:
            tg("⚠️ لم أجد إعلانات مطابقة للفلاتر")
        return

    buy_price, buy_who = min(buy_ads)
    sell_price, sell_who = max(sell_ads)
    spread = (sell_price - buy_price) / buy_price * 100 - FEE_PCT
    profit_try = (sell_price - buy_price) * TRADE_USD
    print(f"buy {buy_price} | sell {sell_price} | spread {spread:.2f}%")

    if spread >= MIN_PROFIT_PCT or ALWAYS:
        tg(
            f"{'🔔 فرصة' if spread >= MIN_PROFIT_PCT else 'ℹ️ فحص يدوي'} USDT/TRY\n"
            f"اشترِ من {buy_who} بسعر {buy_price}\n"
            f"بِع إلى {sell_who} بسعر {sell_price}\n"
            f"الفارق: {spread:.2f}%\n"
            f"الربح المتوقع لـ {TRADE_USD}$: {profit_try:,.0f} ليرة "
            f"(≈ {profit_try / sell_price:.1f}$)"
        )


if __name__ == "__main__":
    main()
