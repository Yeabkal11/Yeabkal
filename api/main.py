import asyncio
import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from telegram import Update

from core.config import settings
from bot.bot import create_bot_app
from db.manager import get_transaction, update_transaction_status, update_user_balance

app = FastAPI()
ptb_app = create_bot_app()

@app.on_event("startup")
async def startup_event():
    await ptb_app.initialize()
    if not ptb_app.post_init:
        raise RuntimeError("post_init not set on application")
    await ptb_app.post_init(ptb_app)
    
    # The application update queue needs to be running for process_update to work.
    if ptb_app.updater:
        await ptb_app.updater.start_polling() # This runs the queue but doesn't poll if webhook is set
    else:
        # For newer versions or different setups
        asyncio.create_task(ptb_app.start())

@app.on_event("shutdown")
async def shutdown_event():
    if ptb_app.updater:
       await ptb_app.updater.stop()
    else:
       await ptb_app.stop()
    await ptb_app.shutdown()


async def process_telegram_update(data: dict):
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    background_tasks.add_task(process_telegram_update, data)
    return {"status": "ok"}

@app.post("/api/chapa/webhook")
async def chapa_webhook(request: Request):
    try:
        payload = await request.json()
        tx_ref = payload.get('tx_ref')

        if not tx_ref: raise HTTPException(400, "tx_ref missing")

        headers = {"Authorization": f"Bearer {settings.CHAPA_API_KEY}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.chapa.co/v1/transaction/verify/{tx_ref}", headers=headers)
        
        if response.status_code != 200: raise HTTPException(400, "Chapa transaction not found")
        
        chapa_data = response.json()
        if chapa_data.get('status') != 'success' or chapa_data['data']['status'] != 'success':
            return {"status": "not a success event"}

        pool = ptb_app.bot_data['pool']
        transaction = await get_transaction(pool, tx_ref)
        if not transaction or transaction['status'] == 'success':
            return {"status": "already processed or not found"}

        await update_user_balance(pool, transaction['telegram_id'], transaction['amount'], 'add')
        await update_transaction_status(pool, tx_ref, 'success')
        await ptb_app.bot.send_message(
            chat_id=transaction['telegram_id'],
            text=f"✅ Your deposit of {transaction['amount']:.2f} ETB is successful!"
        )
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/")
def root():
    return {"status": "Yeab Game Zone API is running"}