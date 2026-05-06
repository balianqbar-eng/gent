import os, asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date
import db

QUANT_URL   = os.environ.get('QUANT_URL', 'https://balian-quant-production.up.railway.app')
TOKEN       = os.environ['TELEGRAM_TOKEN']
CHAT_ID     = os.environ['CHAT_ID']
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://reminder-bot-production-6453.up.railway.app')
PORT        = int(os.environ.get('PORT', 8080))

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '我是你的提醒機器人\n\n'
        '/add 任務  → 新增待辦\n'
        '/list      → 查看待辦\n'
        '/done 任務 → 完成任務\n'
        '/today     → 立即查看日報\n'
        '/status    → 查詢系統連線狀態\n'
        '或直接說「記住 XXX」也可以！'
    )

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith('記住'):
        todo = text.replace('記住：', '').replace('記住 ', '', 1)
        db.add_todo(todo)
        await update.message.reply_text(f'已記錄「{todo}」')

async def add_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    todo = ' '.join(ctx.args)
    if not todo:
        await update.message.reply_text('請輸入任務，例如：/add 買菜')
        return
    db.add_todo(todo)
    await update.message.reply_text(f'已記錄「{todo}」')

async def list_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    todos = db.get_todos()
    msg = '目前沒有待辦' if not todos else \
          '*待辦清單*\n' + '\n'.join(f'{i+1}. {t}' for i, t in enumerate(todos))
    await update.message.reply_text(msg, parse_mode='Markdown')

async def done_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    task = ' '.join(ctx.args)
    db.mark_done(task)
    await update.message.reply_text(f'已完成「{task}」')

async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{QUANT_URL}/health', timeout=aiohttp.ClientTimeout(total=6)) as r:
                data = await r.json()
        bot_ok = 'online'
        xq_ok  = 'online' if data.get('xq_bridge') else 'offline'
    except Exception:
        bot_ok = 'offline'
        xq_ok  = 'offline'
    await update.message.reply_text(
        f'*系統連線狀態*\n\nBalian Quant API：`{bot_ok}`\nXQ Bridge：`{xq_ok}`',
        parse_mode='Markdown'
    )

async def today_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await build_digest(), parse_mode='Markdown')

async def build_digest():
    today_str = date.today().strftime('%Y/%m/%d')
    msg = f'*早安日報 {today_str}*\n\n'
    todos = db.get_todos()
    msg += '*今日待辦*\n'
    msg += '\n'.join(f'・{t}' for t in todos) if todos else '・無待辦任務'
    return msg

async def send_daily(app):
    await app.bot.send_message(chat_id=CHAT_ID, text=await build_digest(), parse_mode='Markdown')

async def post_init(app):
    scheduler = AsyncIOScheduler(timezone='Asia/Taipei')
    scheduler.add_job(lambda: asyncio.create_task(send_daily(app)), 'cron', hour=8, minute=0)
    scheduler.start()
    print('Bot 啟動中...')

def main():
    db.init_db()
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add_cmd))
    app.add_handler(CommandHandler('list', list_cmd))
    app.add_handler(CommandHandler('done', done_cmd))
    app.add_handler(CommandHandler('today', today_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        webhook_url=f'{WEBHOOK_URL}/webhook',
    )

if __name__ == '__main__':
    main()
