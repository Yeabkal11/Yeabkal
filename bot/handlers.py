from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from decimal import Decimal
import uuid
import httpx

from core.config import settings
from db.manager import get_or_create_user, get_user_balance, create_deposit_transaction, create_withdrawal_request
from bot.game_logic import LudoGame
from db.manager import create_game

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_or_create_user(context.bot_data['pool'], user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("Play Ludo 🎲", callback_data="create_game_prompt_stake")],
        [InlineKeyboardButton("Deposit 💰", callback_data="deposit_prompt"), InlineKeyboardButton("Check Balance ⚖️", callback_data="check_balance")],
        [InlineKeyboardButton("Withdraw 💸", callback_data="withdraw_prompt"), InlineKeyboardButton("Help ❓", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Welcome to Yeab Game Zone, {user.first_name}!",
        reply_markup=reply_markup
    )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    next_step = context.user_data.get('next_step')
    if next_step == 'handle_deposit_amount':
        await handle_deposit_amount(update, context)
    elif next_step == 'handle_withdrawal_amount':
        await handle_withdrawal_amount(update, context)
    elif next_step == 'handle_withdrawal_details':
        await handle_withdrawal_details(update, context)

async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_str = update.message.text
    try:
        amount = Decimal(amount_str)
        if amount < settings.MIN_DEPOSIT_AMOUNT:
            await update.message.reply_text(f"Deposit amount must be at least {settings.MIN_DEPOSIT_AMOUNT} ETB.")
            return
    except:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    tx_ref = f"yeab-tx-{update.effective_user.id}-{uuid.uuid4()}"
    headers = {"Authorization": f"Bearer {settings.CHAPA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "amount": str(amount), "currency": "ETB", "tx_ref": tx_ref,
        "callback_url": f"{settings.WEBHOOK_URL}/api/chapa/webhook",
        "return_url": f"https://t.me/{context.bot.username}",
        "first_name": update.effective_user.first_name or "Player", "last_name": update.effective_user.last_name or "User",
        "email": f"{update.effective_user.id}@telegram.user"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.chapa.co/v1/transaction/initialize", headers=headers, json=payload, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                checkout_url = data['data']['checkout_url']
                await create_deposit_transaction(context.bot_data['pool'], tx_ref, update.effective_user.id, amount)
                keyboard = [[InlineKeyboardButton("Click Here to Pay", url=checkout_url)]]
                await update.message.reply_text("Transaction created. Complete payment using the button.", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(f"Payment gateway error: {response.text}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to payment gateway: {e}")
            
    context.user_data['next_step'] = None

async def handle_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']
    balance = await get_user_balance(pool, user_id)
    
    try:
        amount = Decimal(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Invalid amount.")
            return
        if amount > balance:
            await update.message.reply_text("Insufficient balance.")
            return
    except:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return
        
    context.user_data['withdrawal_amount'] = amount
    context.user_data['next_step'] = 'handle_withdrawal_details'
    await update.message.reply_text("Please provide your Telebirr or CBE bank account details for the transfer.")

async def handle_withdrawal_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text
    amount = context.user_data.get('withdrawal_amount')
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    if not amount or not details:
        context.user_data.clear()
        return

    try:
        await update_user_balance(pool, user_id, amount, 'subtract')
        await create_withdrawal_request(pool, user_id, amount, details)
        
        await update.message.reply_text("Your withdrawal request has been submitted and is pending approval. The amount has been deducted from your balance.")
        
        await context.bot.send_message(
            chat_id=settings.ADMIN_TELEGRAM_ID,
            text=f"New withdrawal request:\nUser: {update.effective_user.mention_html()}\nAmount: {amount} ETB\nDetails: {details}"
        )
    except ValueError:
        await update.message.reply_text("An error occurred. Your balance might be insufficient.")
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred: {e}")

    context.user_data.clear()