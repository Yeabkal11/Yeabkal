from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from decimal import Decimal
import asyncio

from db.manager import get_user_balance, update_user_balance, create_game, get_game, update_game
from bot.game_logic import LudoGame
from bot.renderer import render_board
from core.config import settings

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    keyboard = [
        [InlineKeyboardButton("Play Ludo 🎲", callback_data="create_game_prompt_stake")],
        [InlineKeyboardButton("Deposit 💰", callback_data="deposit_prompt"), InlineKeyboardButton("Check Balance ⚖️", callback_data="check_balance")],
        [InlineKeyboardButton("Withdraw 💸", callback_data="withdraw_prompt"), InlineKeyboardButton("Help ❓", callback_data="help")]
    ]
    await query.message.edit_text(f"Welcome back, {user.first_name}!", reply_markup=InlineKeyboardMarkup(keyboard))

async def create_game_prompt_stake_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("20 ETB", callback_data="create_game_stake_20"), InlineKeyboardButton("50 ETB", callback_data="create_game_stake_50"), InlineKeyboardButton("100 ETB", callback_data="create_game_stake_100")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]
    await update.callback_query.message.edit_text("Select your stake:", reply_markup=InlineKeyboardMarkup(keyboard))

async def check_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = await get_user_balance(context.bot_data['pool'], update.effective_user.id)
    await update.callback_query.answer(f"Your balance is: {balance:.2f} ETB", show_alert=True)

async def deposit_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['next_step'] = 'handle_deposit_amount'
    await update.callback_query.message.edit_text(f"Enter deposit amount (min {settings.MIN_DEPOSIT_AMOUNT} ETB):")

async def withdraw_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['next_step'] = 'handle_withdrawal_amount'
    balance = await get_user_balance(context.bot_data['pool'], update.effective_user.id)
    await update.callback_query.message.edit_text(f"Your balance is {balance:.2f} ETB. How much to withdraw?")

async def create_game_stake_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stake = int(update.callback_query.data.split('_')[-1])
    context.user_data['new_game_stake'] = stake
    keyboard = [
        [InlineKeyboardButton("1 Token Home", callback_data="create_game_win_1"), InlineKeyboardButton("2 Tokens Home", callback_data="create_game_win_2"), InlineKeyboardButton("4 Tokens Home", callback_data="create_game_win_4")],
        [InlineKeyboardButton("⬅️ Back", callback_data="create_game_prompt_stake")]
    ]
    await update.callback_query.message.edit_text(f"Stake: {stake} ETB. Now, choose the win condition:", reply_markup=InlineKeyboardMarkup(keyboard))

async def create_game_final_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    stake = context.user_data.get('new_game_stake')
    win_condition = int(query.data.split('_')[-1])
    balance = await get_user_balance(context.bot_data['pool'], user.id)

    if balance < stake:
        await query.answer("Insufficient funds to start this game.", show_alert=True)
        return

    game = LudoGame.new_game(user.id, user.username or user.first_name, stake, win_condition)
    game_id = await create_game(context.bot_data['pool'], game.state)
    
    keyboard = [[InlineKeyboardButton("Join Game 🤝", callback_data=f"join_game_{game_id}")]]
    await query.message.edit_text(f"{user.username or user.first_name} started a game for {stake} ETB!\nWin Condition: {win_condition} token(s) home.", reply_markup=InlineKeyboardMarkup(keyboard))

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    game_id = int(query.data.split('_')[-1])
    pool = context.bot_data['pool']
    
    game_data = await get_game(pool, game_id)
    if not game_data or game_data['status'] != 'lobby':
        await query.answer("Game not available.", show_alert=True)
        return

    game = LudoGame(game_data['game_state'])
    if user.id in game.state['players']:
        await query.answer("You cannot join your own game.", show_alert=True)
        return

    stake = game.state['stake_per_player']
    if await get_user_balance(pool, user.id) < stake:
        await query.answer("Insufficient funds to join.", show_alert=True)
        return
        
    try:
        creator_id = game.state['player_order'][0]
        await update_user_balance(pool, creator_id, Decimal(stake), 'subtract')
        await update_user_balance(pool, user.id, Decimal(stake), 'subtract')
    except ValueError:
        await query.answer("Stake collection failed.", show_alert=True)
        return
    
    game.add_player(user.id, user.username or user.first_name)
    game.state.update({'game_id': game_id, 'chat_id': query.message.chat_id, 'message_id': query.message.message_id})
    await update_game(pool, game_id, game.state, 'active')
    
    board_text = render_board(game.state)
    keyboard = get_game_keyboard(game.state)
    await query.message.edit_text(board_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    asyncio.create_task(check_game_timeout(context, game_id))

async def roll_dice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query, user, pool = update.callback_query, update.effective_user, context.bot_data['pool']
    game_id = int(query.data.split('_')[-1])
    game_data = await get_game(pool, game_id)
    game = LudoGame(game_data['game_state'])

    if user.id != game.current_player_id():
        await query.answer("It's not your turn!", show_alert=True)
        return

    game.roll_dice()
    await update_game(pool, game_id, game.state, game.state['status'])
    board_text = render_board(game.state)
    keyboard = get_game_keyboard(game.state)
    await query.message.edit_text(board_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')

async def move_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query, user, pool = update.callback_query, update.effective_user, context.bot_data['pool']
    _, _, game_id_str, token_index_str = query.data.split('_')
    game_id, token_index = int(game_id_str), int(token_index_str)
    game_data = await get_game(pool, game_id)
    game = LudoGame(game_data['game_state'])

    if user.id != game.current_player_id():
        await query.answer("It's not your turn!", show_alert=True)
        return

    win_info = game.move_token(user.id, token_index)
    if win_info:
        winner_id = win_info['winner']
        pot = game.state['pot']
        prize = Decimal(pot) - (Decimal(pot) * Decimal(settings.OWNER_COMMISSION_RATE))
        await update_user_balance(pool, winner_id, prize, 'add')
        
    await update_game(pool, game_id, game.state, game.state['status'])
    board_text = render_board(game.state)
    keyboard = get_game_keyboard(game.state) if not win_info else [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
    await query.message.edit_text(board_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')

def get_game_keyboard(game_state: dict) -> list:
    if game_state['status'] != 'active': return []
    game = LudoGame(game_state)
    game_id = game_state['game_id']
    if game_state.get('dice_roll'):
        moves = game.get_possible_moves(game.current_player_id(), game_state['dice_roll'])
        return [[InlineKeyboardButton(f"Move Token {i+1}", callback_data=f"move_token_{game_id}_{i}") for i in moves]]
    else:
        return [[InlineKeyboardButton("Roll Dice 🎲", callback_data=f"roll_dice_{game_id}")]]

async def check_game_timeout(context: ContextTypes.DEFAULT_TYPE, game_id: int):
    await asyncio.sleep(settings.GAME_TIMEOUT_SECONDS)
    pool = context.bot_data['pool']
    game_data = await get_game(pool, game_id)
    if not game_data or game_data['status'] != 'active': return
    
    # Simple check, assumes this coroutine is authoritative
    game = LudoGame(game_data['game_state'])
    winner_id = game.forfeit(game.current_player_id())
    pot, prize = game.state['pot'], Decimal(game.state['pot']) * (1 - Decimal(settings.OWNER_COMMISSION_RATE))
    await update_user_balance(pool, winner_id, prize, 'add')
    await update_game(pool, game_id, game.state, 'forfeited')
    
    board_text = render_board(game.state)
    try:
        await context.bot.edit_message_text(
            chat_id=game.state['chat_id'], message_id=game.state['message_id'], text=board_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]])
        )
    except: pass