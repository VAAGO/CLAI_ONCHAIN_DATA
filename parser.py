# ═══════════════════════════════════════════════════════════════
# CLAI ONCHAIN — PARSER v1.2 (GitHub Auto-Push Token Edition)
# Парсит алерты Arkham → пишет в tx_output.txt → пушит на GitHub
# Формат: YYYY-MM-DD HH:MM,VALUE,SOURCE
# ═══════════════════════════════════════════════════════════════

import re
import os
import subprocess
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ───────────────────────────────────────────────────────────────
# ЗАГРУЗКА ПЕРЕМЕННЫХ (.env)
# ───────────────────────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в файле .env!")
if not GITHUB_TOKEN:
    print("⚠️ GITHUB_TOKEN не найден! Автопуш работать не будет.")

# ───────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ───────────────────────────────────────────────────────────────
WALLET_MAP = {
    "0xEae": "W",    # Wintermute Officiant
    "0xa9C": "B1",   # Binance Deposit #1
    "0x27B": "B2",   # Binance Deposit #2
    "0x06F": "B3",   # Binance Deposit #3
}
IGNORE_WALLETS = {"0x51C"}
TARGET_WALLET = "0x28C"
OUTPUT_FILE = "tx_output.txt"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))

# ───────────────────────────────────────────────────────────────
# АВТОПУШ НА GITHUB ЧЕРЕЗ TOKEN
# ───────────────────────────────────────────────────────────────
def git_push():
    if not GITHUB_TOKEN:
        return

    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", OUTPUT_FILE], check=True, capture_output=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if not status.stdout.strip():
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"TX Update: {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
        
        # Безопасный пуш с токеном
        repo_url = f"https://{GITHUB_TOKEN}@github.com/VAAGO/CLAI_ONCHAIN_DATA.git"
        result = subprocess.run(["git", "push", repo_url, "main"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   🚀 УСПЕШНО ОТПРАВЛЕНО НА GITHUB → {commit_msg}")
        else:
            print(f"   ❌ Ошибка при пуше:\n{result.stderr.strip()}")
            
    except Exception as e:
        print(f"   ❌ Ошибка Git: {e}")

# ───────────────────────────────────────────────────────────────
# ПАРСЕР АЛЕРТА
# ───────────────────────────────────────────────────────────────
def parse_alert(text: str):
    if not text: return None
    
    from_match = re.search(r"From:\s*([^\n]+)", text)
    if not from_match: return None
    from_line = from_match.group(1)
    
    for ignore_addr in IGNORE_WALLETS:
        if ignore_addr in from_line: return None
    
    source_code = None
    for addr, code in WALLET_MAP.items():
        if addr in from_line:
            source_code = code
            break
    if source_code is None: return None
    
    to_match = re.search(r"To:\s*([^\n]+)", text)
    if not to_match: return None
    if TARGET_WALLET not in to_match.group(1): return None
    
    value_match = re.search(r"\$([\d,]+\.?\d*)", text)
    if not value_match: return None
    
    try:
        value_int = int(float(value_match.group(1).replace(",", "")))
    except ValueError:
        return None
    
    time_match = re.search(r"Time:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text)
    if not time_match: return None
    
    return (time_match.group(1), value_int, source_code)

def append_to_file(datetime_str, value, source):
    line = f"{datetime_str},{value}" if source == "W" else f"{datetime_str},{value},{source}"
    
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            if line in f.read(): return False
            
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return True

# ───────────────────────────────────────────────────────────────
# ОБРАБОТЧИК СООБЩЕНИЙ (Был случайно удалён - ВЕРНУЛИ!)
# ───────────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    
    result = parse_alert(msg.text)
    if result is None:
        print(f"⏭  Пропущен: {msg.text[:60]}...")
        return
    
    datetime_str, value, source = result
    if append_to_file(datetime_str, value, source):
        print("─" * 60)
        print(f"✅ ДОБАВЛЕНО: {datetime_str} | ${value:,} | {source}")
        git_push()  # <--- АВТОПУШ ВЫЗЫВАЕТСЯ ЗДЕСЬ
        print("─" * 60)
    else:
        print(f"⏭  Дубль: {datetime_str} ${value:,} {source}")

# ───────────────────────────────────────────────────────────────
# ЗАПУСК
# ───────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🚀 CLAI ONCHAIN PARSER v1.2 (GitHub Token Auto-Push)")
    print("=" * 60)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
