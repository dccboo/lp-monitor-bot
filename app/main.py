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
import sqlite3
from datetime import datetime

# 数据库配置（添加到文件开头，其他import之后）
DB_CONFIG = {
    'db_name': os.getenv('DB_PATH', 'db/tasks.db')  # 优先使用环境变量，否则用本地路径
}

def init_db():
    """初始化数据库和表结构"""
    conn = sqlite3.connect(DB_CONFIG['db_name'])
    cursor = conn.cursor()
    
    # 创建监控任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chain TEXT NOT NULL,
            contract_address TEXT NOT NULL,
            monitor_address TEXT NOT NULL,
            last_state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, chain, contract_address, monitor_address)
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON monitor_tasks(user_id)')
    
    conn.commit()
    conn.close()
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
    Thread(target=lambda: app.run(port=8000, host='0.0.0.0')).start()

    # 创建Bot应用
    application = Application.builder().token(BOT_TOKEN).build()

    # 设置webhook（Render适用）
    await application.bot.set_webhook(
        url=f"https://your-render-app.onrender.com/{BOT_TOKEN}",
        allowed_updates=Update.ALL_TYPES
    )
    
    # 启动webhook模式
    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        secret_token='WEBHOOK_SECRET',
        webhook_url=f"https://your-render-app.onrender.com/{BOT_TOKEN}"
    )
# 在原有代码基础上添加以下内容

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示所有监控任务"""
    user_id = update.message.from_user.id
    conn = sqlite3.connect(DB_CONFIG['db_name'])
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM monitor_tasks WHERE user_id = ?', (user_id,))
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        await update.message.reply_text("您当前没有监控任务")
        return

    message = "📋 您的监控任务：\n\n"
    for task in tasks:
        task_id, _, chain, contract, monitor, _, _ = task
        message += (
            f"🔹 ID: {task_id}\n"
            f"区块链: {chain.upper()}\n"
            f"合约地址: {contract[:6]}...{contract[-4:]}\n"
            f"监控地址: {monitor[:6]}...{monitor[-4:]}\n"
            f"────────────────\n"
        )
    await update.message.reply_text(message)

async def remove_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始删除流程"""
    await update.message.reply_text("请输入要删除的任务ID（使用/list查看ID）:")
    return 'REMOVE_TASK'

async def remove_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """执行删除操作"""
    try:
        task_id = int(update.message.text)
        user_id = update.message.from_user.id
        
        conn = sqlite3.connect(DB_CONFIG['db_name'])
        cursor = conn.cursor()
        
        # 验证任务属于该用户
        cursor.execute('SELECT 1 FROM monitor_tasks WHERE id = ? AND user_id = ?',
                      (task_id, user_id))
        if not cursor.fetchone():
            await update.message.reply_text("❌ 任务ID不存在或不属于您")
            return ConversationHandler.END
            
        cursor.execute('DELETE FROM monitor_tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ 已成功删除任务 {task_id}")
    except ValueError:
        await update.message.reply_text("❌ 请输入有效的数字ID")
    finally:
        return ConversationHandler.END

# 在 main() 函数中添加处理器：
def main():
    init_db()
    # ... 原有代码 ...
    application = Application.builder().token(BOT_TOKEN).build()
    # 添加新命令处理器
    application.add_handler(CommandHandler("list", list_tasks))
    
    remove_conv = ConversationHandler(
        entry_points=[CommandHandler("remove", remove_task_start)],
        states={
            'REMOVE_TASK': [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_task)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(remove_conv)
    
    # ... 其余原有代码 ...
