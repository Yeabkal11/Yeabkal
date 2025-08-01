# Yeab Game Zone - Real-Money Ludo Telegram Bot

Welcome to the Yeab Game Zone! This is a complete, production-ready Python project for a Telegram bot that facilitates real-money Ludo games between two players. It includes a robust game engine, deposit/withdrawal handling via the Chapa payment gateway, and is designed for seamless deployment on Render.

## Features

- **Real-Money Gameplay**: Players stake real money (ETB) to play a game of Ludo.
- **Two-Player Ludo**: A complete implementation of Ludo rules for two players.
- **Selectable Win Conditions**: Game creators can choose to win by getting 1, 2, or all 4 tokens home.
- **Chapa Payment Integration**: Securely handle deposits via the Chapa API.
- **Internal Wallet System**: Each user has a persistent balance stored in a PostgreSQL database.
- **Commission System**: A configurable 10% commission is taken from the pot, rewarding the bot owner.
- **Dynamic Board Rendering**: The game board is rendered using emojis and updated in the same message to prevent chat spam.
- **Turn Timer & Forfeit Logic**: Players who are inactive for too long automatically forfeit the game.
- **Asynchronous Architecture**: Built with FastAPI and `asyncpg` for high performance.
- **Cloud-Native Deployment**: Optimized for deployment on Render with a `render.yaml` blueprint.
- **Dev-Friendly Setup**: Includes a GitHub Codespaces configuration for a one-click development environment.

## Technical Stack

- **Programming Language**: Python 3.10
- **Telegram Bot Framework**: `python-telegram-bot`
- **Web Framework**: FastAPI (for webhooks)
- **Database**: PostgreSQL (with `asyncpg`)
- **Payment Gateway**: Chapa API V1
- **Deployment**: Render (PaaS)

---

## Deployment to Render (Step-by-Step)

This project is designed for easy deployment using Render's "Blueprint" feature.

### Step 1: Fork the Repository

First, fork this repository to your own GitHub account.

### Step 2: Create a New Blueprint on Render

1.  Go to your [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** and select **Blueprint**.
3.  Connect the GitHub repository you just forked.
4.  Render will automatically detect the `render.yaml` file. Give your project a unique name (e.g., `yeab-game-zone`).
5.  Render will list the two services (`yeab-game-zone-api` and `yeab-game-zone-db`) defined in the `render.yaml` file.

### Step 3: Configure Environment Variables

Before you deploy, you must set up your secret environment variables.

1.  In the Render dashboard during the blueprint setup, click on **Environment Variables**.
2.  Click **Add Secret File** and create a `.env` file or add individual variables.
3.  Add the following required environment variables:
    -   `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather.
    -   `CHAPA_API_KEY`: Your secret API key from your Chapa merchant account.
    -   `ADMIN_TELEGRAM_ID`: Your personal Telegram user ID. The bot will send withdrawal notifications here.

    **Note**: `DATABASE_URL` and `WEBHOOK_URL` are automatically configured by the `render.yaml` file. You do not need to set them manually.

### Step 4: Deploy

1.  Click **Apply** to save the environment variables.
2.  Click **Create New Services**.

Render will now build and deploy both the web service and the database. The initial deployment may take a few minutes. The `buildCommand` in the `render.yaml` will automatically run the `setup_database` script to create the necessary tables.

### How It Works on Render

-   **Web Service (`yeab-game-zone-api`)**: Runs the FastAPI application using Gunicorn. This service receives all webhooks from Telegram and Chapa. It has a public URL (`WEBHOOK_URL`).
-   **Database (`yeab-game-zone-db`)**: A managed PostgreSQL instance that stores all user, game, and transaction data.
-   **Webhook Auto-Configuration**: The FastAPI application, upon starting, automatically tells Telegram where to send updates by setting the webhook to its own public URL. This means you **do not** need to set the webhook manually.

---

## Development with GitHub Codespaces

For a seamless development experience, you can use GitHub Codespaces.

1.  Go to the main page of your forked repository on GitHub.
2.  Click the **Code** button.
3.  Go to the **Codespaces** tab and click **Create codespace on main**.

This will launch a complete, pre-configured development environment in your browser, including a running PostgreSQL instance. The `postCreateCommand` will install all Python dependencies automatically. You can start coding immediately.