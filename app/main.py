import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from chain_handlers.ethereum import EthereumHandler
from chain_handlers.aptos import AptosHandler
from chain_handlers.sui import SuiHandler
from flask import Flask, jsonify

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 配置
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAIN_CONFIG = {
    'ethereum': {'rpc_url': os.getenv('ETH_RPC_URL')},
    'aptos': {'rpc_url': os.getenv('APTOS_RPC_URL')},
    'sui': {'rpc_url': os.getenv('SUI_RPC_URL')}
}

# 状态定义
CHAIN, CONTRACT_ADDRESS, MONITOR_ADDRESS = range(3)

# 健康检查
app = Flask(__name__)
@app.route('/health')
def health():
    return jsonify({"status": "ok"})

async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ethereum", callback_data='chain_ethereum')],
        [InlineKeyboardButton("Aptos", callback_data='chain_aptos')],
        [InlineKeyboardButton("Sui", callback_data='chain_sui')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('请选择要监控的公链:', reply_markup=reply_markup)
    return CHAIN

async def chain_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chain = query.data.split('_')[1]
    context.user_data['chain'] = chain
    await query.edit_message_text(f"已选择 {chain.capitalize()} 链\n\n请输入合约地址:")
    return CONTRACT_ADDRESS

async def get_contract_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contract_address'] = update.message.text
    await update.message.reply_text("请输入要监控的地址:")
    return MONITOR_ADDRESS

async def get_monitor_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    await update.message.reply_text(
        f"监控任务已创建!\n"
        f"链: {user_data['chain']}\n"
        f"合约地址: {user_data['contract_address']}\n"
        f"监控地址: {update.message.text}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('操作已取消')
    return ConversationHandler.END

async def check_lp_status(context: ContextTypes.DEFAULT_TYPE):
    # 这里添加实际的LP状态检查逻辑
    pass

def run_flask():
    app.run(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    # 启动Flask
    from threading import Thread
    Thread(target=run_flask).start()

    # 创建Bot应用
    application = Application.builder().token(BOT_TOKEN).build()

    # 添加对话处理器
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', start_add)],
        states={
            CHAIN: [CallbackQueryHandler(chain_selected, pattern='^chain_')],
            CONTRACT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contract_address)],
            MONITOR_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_monitor_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    # 定时任务
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_lp_status, 'interval', minutes=5, args=[application])
    scheduler.start()

    # 启动Bot
    application.run_polling()
