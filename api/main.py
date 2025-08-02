# main.py - Main entry point for the application

import uvicorn
import os
import sys
import asyncio
from dotenv import load_dotenv

from database_models.models import init_db

def main():
    """
    Main entry point for running the application.
    This script handles both database initialization and running the web server.
    """
    load_dotenv()

    # Handle the 'initdb' command for the build process
    if len(sys.argv) > 1 and sys.argv[1] == "initdb":
        print("--- Initializing Database as per buildCommand ---")
        asyncio.run(init_db())
        print("--- Database Initialization Complete ---")
        return # Exit after finishing the build command task

    # --- IMPLEMENTING YOUR PROMPT ---
    # This is the logic you provided, adapted for our project.

    print("--- Starting Uvicorn Web Server ---")
    
    # Get the port from Render's PORT environment variable.
    # Default to 10000 (Render's default) if not set.
    try:
        port = int(os.environ.get("PORT", 10000))
        print(f"--- Binding to host 0.0.0.0 on port: {port} ---")
    except ValueError:
        print("--- Invalid PORT env var. Defaulting to 10000. ---")
        port = 10000

    # Here we replace "slime.run" with "uvicorn.run" and point it
    # to your FastAPI app located in "api/main.py".
    


# This makes the script directly runnable with `python main.py`
if __name__ == "__main__":
    main()```

#### **Step 2: Update `render.yaml`**

Now we tell Render to use our new, reliable `main.py` script as the start command. This is much simpler and less prone to shell errors.

**Action:** Go to your `render.yaml` file on GitHub. Click the edit icon, **delete everything**, and **replace it with this final, simplified version**:

```yaml
# render.yaml - FINAL VERSION using programmatic start

services:
  - type: web
    name: yeab-game-zone-api
    env: python
    plan: starter
    region: frankfurt
    # The build command still prepares the database
    buildCommand: "pip install -r requirements.txt && python main.py initdb"
    # The start command is now extremely simple and reliable
    startCommand: "python main.py"
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: yeab-ludo-db
          property: connectionString
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: CHAPA_API_KEY
        sync: false
      - key: WEBHOOK_URL
        fromService:
          type: web
          name: yeab-game-zone-api
          property: url

  - type: pserv
    name: yeab-ludo-db
    region: frankfurt
    databaseName: yeab_game_db
    databaseUser: yeab_user
    plan: free

  - type: worker
    name: yeab-game-forfeit-worker
    env: python
    plan: starter
    region: frankfurt
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python -m bot.worker"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: yeab-ludo-db
          property: connectionString
      - key: TELEGRAM_BOT_TOKEN
        sync: false