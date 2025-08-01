import asyncpg
from decimal import Decimal
import json
from typing import Optional, Dict, Any, List

from core.config import settings

# --- Schema Setup ---
async def create_db_pool():
    """Creates a connection pool to the PostgreSQL database."""
    return await asyncpg.create_pool(dsn=settings.DATABASE_URL)

async def setup_database(pool: asyncpg.Pool):
    """Sets up the necessary tables and indexes in the database."""
    async with pool.acquire() as connection:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00
            );
        """)
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id SERIAL PRIMARY KEY,
                game_state JSONB NOT NULL,
                status TEXT NOT NULL, -- 'lobby', 'active', 'finished', 'forfeited'
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_action_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_ref TEXT PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                status TEXT NOT NULL, -- 'pending', 'success', 'failed'
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                withdrawal_id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                account_details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processed', 'failed'
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

# --- User Management ---
async def get_or_create_user(pool: asyncpg.Pool, telegram_id: int, username: str) -> Dict[str, Any]:
    """Retrieves a user or creates one if they don't exist."""
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
        if not user:
            await conn.execute("INSERT INTO users (telegram_id, username, balance) VALUES ($1, $2, 0.00)", telegram_id, username)
            user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
        return dict(user)

async def get_user_balance(pool: asyncpg.Pool, telegram_id: int) -> Decimal:
    """Gets a user's balance."""
    async with pool.acquire() as conn:
        balance = await conn.fetchval("SELECT balance FROM users WHERE telegram_id = $1", telegram_id)
        return balance or Decimal('0.00')

async def update_user_balance(pool: asyncpg.Pool, telegram_id: int, amount: Decimal, operation: str = 'add'):
    """Updates a user's balance. Use 'add' or 'subtract' for operation."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            current_balance = await conn.fetchval("SELECT balance FROM users WHERE telegram_id = $1 FOR UPDATE", telegram_id)
            new_balance = current_balance + amount if operation == 'add' else current_balance - amount
            if new_balance < 0:
                raise ValueError("Insufficient funds.")
            await conn.execute("UPDATE users SET balance = $1 WHERE telegram_id = $2", new_balance, telegram_id)

# --- Transaction Management ---
async def create_deposit_transaction(pool: asyncpg.Pool, tx_ref: str, telegram_id: int, amount: Decimal):
    """Creates a pending deposit transaction."""
    await pool.execute("INSERT INTO transactions (tx_ref, telegram_id, amount, status) VALUES ($1, $2, $3, 'pending')", tx_ref, telegram_id, amount)

async def get_transaction(pool: asyncpg.Pool, tx_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves a transaction by its reference."""
    record = await pool.fetchrow("SELECT * FROM transactions WHERE tx_ref = $1", tx_ref)
    return dict(record) if record else None

async def update_transaction_status(pool: asyncpg.Pool, tx_ref: str, status: str):
    """Updates the status of a transaction."""
    await pool.execute("UPDATE transactions SET status = $1 WHERE tx_ref = $2", status, tx_ref)

# --- Game Management ---
async def create_game(pool: asyncpg.Pool, initial_state: Dict[str, Any]) -> int:
    """Creates a new game in the database."""
    game_id = await pool.fetchval(
        "INSERT INTO games (game_state, status) VALUES ($1, 'lobby') RETURNING game_id",
        json.dumps(initial_state)
    )
    return game_id

async def get_game(pool: asyncpg.Pool, game_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a game by its ID."""
    record = await pool.fetchrow("SELECT * FROM games WHERE game_id = $1", game_id)
    if record:
        game_data = dict(record)
        game_data['game_state'] = json.loads(game_data['game_state'])
        return game_data
    return None

async def update_game(pool: asyncpg.Pool, game_id: int, new_state: Dict[str, Any], status: str):
    """Updates a game's state and status."""
    await pool.execute(
        "UPDATE games SET game_state = $1, status = $2, last_action_at = NOW() WHERE game_id = $3",
        json.dumps(new_state), status, game_id
    )

# --- Withdrawal Management ---
async def create_withdrawal_request(pool: asyncpg.Pool, telegram_id: int, amount: Decimal, account_details: str) -> int:
    """Creates a pending withdrawal request."""
    req_id = await pool.fetchval(
        "INSERT INTO withdrawals (telegram_id, amount, account_details, status) VALUES ($1, $2, $3, 'pending') RETURNING withdrawal_id",
        telegram_id, amount, account_details
    )
    return req_id