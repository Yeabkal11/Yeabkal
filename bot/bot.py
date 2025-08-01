import httpx
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from core.config import settings
from db.manager import create_db_pool, setup_database
from bot.handlers import start_command, handle_text_input
from bot.callbacks import (
    main_menu_callback, create_game_prompt_stake_callback, check_balance_callback,
    deposit_prompt_callback, withdraw_prompt_callback, create_game_stake_callback,
    create_game_final_callback, join_game_callback, roll_dice_callback, move_token_callback,
)

async def post_init(application: Application):
    """Runs after application is built."""
    pool = await create_db_pool()
    application.bot_data['pool'] = pool
    # The DB setup is run from render.yaml buildCommand, not here, to avoid race conditions.
    application.bot_data['http_session'] = httpx.AsyncClient()
    webhook_url = f"{settings.WEBHOOK_URL}/api/telegram/webhook"
    await application.bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])

async def post_shutdown(application: Application):
    """Runs before application shuts down."""
    if 'pool' in application.bot_data:
        await application.bot_data['pool'].close()
    if 'http_session' in application.bot_data:
        await application.bot_data['http_session'].aclose()

def create_bot_app() -> Application:
    """Creates and configures the Telegram bot application."""
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Command & Message Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Callback Query Handlers
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(create_game_prompt_stake_callback, pattern="^create_game_prompt_stake$"))
    application.add_handler(CallbackQueryHandler(check_balance_callback, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(deposit_prompt_callback, pattern="^deposit_prompt$"))
    application.add_handler(CallbackQueryHandler(withdraw_prompt_callback, pattern="^withdraw_prompt$"))
    application.add_handler(CallbackQueryHandler(create_game_stake_callback, pattern="^create_game_stake_"))
    application.add_handler(CallbackQueryHandler(create_game_final_callback, pattern="^create_game_win_"))
    application.add_handler(CallbackQueryHandler(join_game_callback, pattern="^join_game_"))
    application.add_handler(CallbackQueryHandler(roll_dice_callback, pattern="^roll_dice_"))
    application.add_handler(CallbackQueryHandler(move_token_callback, pattern="^move_token_"))
    
    return application