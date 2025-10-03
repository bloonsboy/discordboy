import logging
import os
import asyncio
import pandas as pd
import json

from dotenv import load_dotenv

from corus.botus import run_bot
from dashboardus.appus import create_app
from corus.processus import process_and_save_stats
from dataus.user import NAME_REPLACE_MAP, SMURF_ACCOUNTS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATA_DIR = "dataus" 
CACHE_FILENAME = os.path.join(DATA_DIR, "discord_messages_cache.parquet")
ROLE_COLORS_FILENAME = os.path.join(DATA_DIR, "role_colors.json")
STATS_FILENAME = os.path.join(DATA_DIR, "discord_server_stats.csv")

os.makedirs(DATA_DIR, exist_ok=True)

async def main():
    logging.info("Starting data collection from Discord...")
    try:
        df, user_map, colors_map, current_members = await run_bot(
            DISCORD_TOKEN, CACHE_FILENAME, ROLE_COLORS_FILENAME
        )
    except Exception as e:
        logging.error(f"Error during data collection: {e}")
        df = pd.DataFrame()

    if df.empty:
        logging.warning("No data was retrieved. Attempting to load from local cache...")
        if os.path.exists(CACHE_FILENAME) and os.path.exists(ROLE_COLORS_FILENAME):
            df = pd.read_parquet(CACHE_FILENAME)
            with open(ROLE_COLORS_FILENAME, 'r') as f:
                colors_map = json.load(f)
            current_members = [] 
        else:
            logging.error("No local cache found. Exiting.")
            return

    df = df[~df['author_name'].isin(SMURF_ACCOUNTS)]
    user_total_counts = df['author_name'].value_counts()
    active_users = user_total_counts[user_total_counts >= 100].index
    df = df[df['author_name'].isin(active_users)]
    
    if 'character_count' in df.columns:
        df['character_count'] = df['character_count'].fillna(0)
    else:
        df['character_count'] = 0
        
    df['original_author_name'] = df['author_name']
    df['author_name'] = df['author_name'].replace(NAME_REPLACE_MAP)

    if not df.empty:       
        process_and_save_stats(df, STATS_FILENAME)
        
        app = create_app(df, colors_map, current_members)
        logging.info("Launching the dashboard on http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=True)
    else:
        logging.warning("No data to display after filtering. Exiting.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN is not set! Please ensure you have a .env file.")
    else:
        asyncio.run(main())

