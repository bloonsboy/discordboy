# discordboy/appus.py

import asyncio
import json
import logging
import os

import pandas as pd
from corus.botus import run_bot
from corus.processus import process_and_save_stats
from dashboardus.appus import create_app
from dataus.constant import (CACHE_FILENAME, DATA_DIR, MIN_MESSAGE_COUNT,
                             NAME_REPLACE_MAP, ROLE_COLORS_FILENAME,
                             ROLE_NAMES_FILENAME, SMURF_IDS, STATS_FILENAME)
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

os.makedirs(DATA_DIR, exist_ok=True)

def prepare_dataframe(df, member_data):
    df = df.copy()
    df = df[~df["author_id"].isin(SMURF_IDS)]


    df["original_author_name"] = df["author_name"]
    df["author_name"] = (
        df["author_id"].map(NAME_REPLACE_MAP).fillna(df["author_name"])
    )

    total_counts = df["author_name"].value_counts()
    active_users = total_counts[total_counts >= MIN_MESSAGE_COUNT].index
    df = df[df["author_name"].isin(active_users)]

    for col in [
        "character_count",
        "reaction_count",
        "attachment_count",
        "sticker_count",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
        else:
            df[col] = 0

    for col in ["mentioned_user_ids", "mentioned_role_ids"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])
        else:
            df[col] = pd.Series(
                [[] for _ in range(len(df))], index=df.index, dtype="object"
            )

    for col in [
        "replied_to_author_id",
        "thread_id",
        "thread_name",
        "message_type",
        "content",
        "jump_url",
    ]:
        if col not in df.columns:
            df[col] = pd.NA

    logging.info(
        f"Preparation complete. {len(df)} messages and {len(active_users)} active users retained."
    )
    return df, member_data


async def main():
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN is not set! Please check your .env file.")
        return

    dashboard_df, role_colors_map, member_data, role_names_map = await run_bot(
        DISCORD_TOKEN,
        DATA_DIR,
        CACHE_FILENAME,
        ROLE_COLORS_FILENAME,
        ROLE_NAMES_FILENAME,
    )

    if not dashboard_df.empty:
        processed_df, processed_member_data = prepare_dataframe(
            dashboard_df, member_data
        )

        if processed_df.empty:
            logging.warning(
                "No data remaining after filtering. Dashboard cannot be launched."
            )
            return

        process_and_save_stats(processed_df, os.path.join(DATA_DIR, STATS_FILENAME))

        app = create_app(
            processed_df, role_colors_map, processed_member_data, role_names_map
        )
        logging.info("Launching Dash web server on http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=False)
    else:
        logging.warning("No data was collected. Program will exit.")


if __name__ == "__main__":
    asyncio.run(main())
