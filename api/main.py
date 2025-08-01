# main.py - Main entry point for the application

import uvicorn
import os
import sys
import asyncio
from dotenv import load_dotenv

from database_models.models import init_db

# This is the main function that runs everything.
def main():
    """
    Main entry point for running the application.
    This script can now be used to either run the web server
    or initialize the database.
    """
    load_dotenv()

    # Check for command-line arguments (like "initdb")
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "initdb":
            print("--- Initializing Database ---")
            asyncio.run(init_db())
            print("--- Database Initialization Complete ---")
            return # Exit after initializing the database
        # This allows the worker to still be run if needed in the future
        elif command == "forfeit_worker":
            print("Worker functionality to be implemented.")
            return

    # --- THIS IS THE NEW SECTION ---
    # If no command-line arguments, start the web server.
    print("--- Starting Uvicorn Web Server Programmatically ---")
    
    # Render provides the port to use in the "PORT" environment variable.
    # We default to 8000 for local development.
    try:
        port = int(os.environ.get("PORT", 8000))
        print(f"--- Attempting to bind to port: {port} ---")
    except ValueError:
        print("--- Invalid PORT environment variable. Defaulting to 8000. ---")
        port = 8000

    # We run the Uvicorn server directly here.
    # "api.main:app" points to the `app` object in your `api/main.py` file.
    # host="0.0.0.0" is crucial for Render to be able to connect.
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)


# This makes the script runnable
if __name__ == "__main__":
    main()