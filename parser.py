# ═══════════════════════════════════════════════════════════════
# CLAI ONCHAIN — PARSER v1.1 (GitHub Auto-Push Edition)
# Парсит алерты Arkham → пишет в tx_output.txt → пушит на GitHub
# Формат для TradingView: YYYY-MM-DD HH:MM,VALUE,SOURCE
# ═══════════════════════════════════════════════════════════════

import re
import os
import subprocess
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ───────────────────────────────────────────────────────────────
# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (.env)
# ───────────────────────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в файле .env!")

# ───────────────────────────────────────────────────────────────
# КАРТА КОШЕЛЬКОВ
# ───────────────────────────────────────────────────────────────
WALLET_MAP = {
    "0xEae": "W",    # Wintermute Officiant
    "0xa9C": "B1",   # Binance Deposit #1
    "0x27B": "B2",   # Binance Deposit #2
    "0x06F": "B3",   # Binance Deposit #3
}

IGNORE_WALLETS = {
    "0x51C",   # Wintermute Market Maker
}

TARGET_WALLET = "0x28C"
OUTPUT_FILE = "tx_output.txt"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))  # Папка со скриптом

# ───────────────────────────────────────────────────────────────
# АВТОКОММИТ + АВТОПУШ (G2.6)
# ───────────────────────────────────────────────────────────────
def git_push():
    """
    Делает git add, commit и push при новой транзакции.
    """
    try:
        # Переходим в папку репозитория
        os.chdir(REPO_PATH)
        
        # Git add
        subprocess.run(["git", "add", OUTPUT_FILE], check=True, capture_output=True)
        
        # Проверяем, есть ли что коммитить
        status = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        
        if not status.stdout.strip():
            return  # Нет изменений, выходим
        
        # Git commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"TX: {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_msg], 
                      check=True, capture_output=True)
        
        # Git push
        subprocess.run(["git", "push", "origin", "main"], 
                      check=True, capture_output=True)
        
        print(f"   🚀 Отправлено на GitHub: {commit_msg}")
        
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️ Git ошибка: {e}")
    except Exception as e:
        print(f"   ⚠️ Ошибка пуша: {e}")

# ───────────────────────────────────────────────────────────────
# ПАРСЕР АЛЕРТА (без изменений)
# ───────────────────────────────────────────────────────────────
def parse_alert(text: str):
    if not text:
        return None
    
    from_match = re.search(r"From:\s*([^\n]+)", text)
    if not from_match:
        return None
    from_line = from_match.group(1)
    
    for ignore_addr in IGNORE_WALLETS:
        if ignore_addr in from_line:
            return None
    
    source_code = None
    for addr, code in WALLET_MAP.items():
        if addr in from_line:
            source_code = code
            break
    
    if source_code is None:
        return None
    
    to_match = re.search(r"To:\s*([^\n]+)", text)
    if not to_match:
        return None
    to_line = to_match.group(1)
    
    if TARGET_WALLET not in to_line:
        return None
    
    value_match = re.search(r"\$([\d,]+\.?\d*)", text)
    if not value_match:
        return None
    
    value_str = value_match.group(1).replace(",", "")
    try:
        value_int = int(float(value_str))
    except ValueError:
        return None
    
    time_match = re.search(r"Time:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text)
    if not time_match:
        return None
    
    datetime_str = time_match.group(1)
    return (datetime_str, value_int, source_code)

# ───────────────────────────────────────────────────────────────
# ЗАПИСЬ В ФАЙЛ (с защитой от дублей)
# ───────────────────────────────────────────────────────────────
def append_to_file(datetime_str, value, source):
    if source == "W":
        line = f"{datetime_str},{value}"
    else:
        line = f"{datetime_str},{value},{source}"
    
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = f.read()
        if line in existing:
            return False
    
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    
    return True

# ───────────────────────────────────────────────────────────────
# ОБРАБОТЧИК СООБЩЕНИЙ (добавлен git_push)
# ───────────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg is None or msg.text is None:
        return
    
    text = msg.text
    result = parse_alert(text)
    
    if result is None:
        print(f"⏭  Пропущен: {text[:60]}...")
        return
    
    datetime_str, value, source = result
    added = append_to_file(datetime_str, value, source)
    
    if added:
        print("─" * 60)
        print(f"✅ ДОБАВЛЕНО:")
        print(f"   📅 Время:    {datetime_str}")
        print(f"   💰 Сумма:    ${value:,}")
        print(f"   📍 Источник: {source}")
        
        # ⭐ АВТОПУШ ПРИ НОВОЙ ТРАНЗАКЦИИ (G2.7)
        git_push()
        
        print("─" * 60)
    else:
        print(f"⏭  Дубль: {datetime_str} ${value:,} {source}")

# ───────────────────────────────────────────────────────────────
# ЗАПУСК
# ───────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🚀 CLAI ONCHAIN PARSER v1.1 (GitHub Auto-Push)")
    print("=" * 60)
    print(f"📄 Файл вывода: {OUTPUT_FILE}")
    print(f"🎯 Binance HW: {TARGET_WALLET}")
    print(f"📍 Источники: {list(WALLET_MAP.values())}")
    print("=" * 60)
    print("⏳ Жду алерты...")
    print("   Ctrl+C для остановки")
    print()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()

