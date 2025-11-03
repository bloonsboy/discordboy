import asyncio
import json
import logging
import os

import pandas as pd
from dotenv import load_dotenv

from corus.botus import run_bot
from corus.processus import process_and_save_stats
from dashboardus.appus import create_app
from dataus.constant import (
    CACHE_FILENAME,
    DATA_DIR,
    EXCLUDED_CHANNEL_IDS,
    ID_NAME_MAP,
    IDS_TO_EXCLUDE,
    MIN_MESSAGE_COUNT,
    ROLE_DATA_FILENAME,
    SMURF_IDS,
    STATS_FILENAME,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

os.makedirs(DATA_DIR, exist_ok=True)


def prepare_dataframe(df, member_data):
    logging.info("Preparing DataFrame for dashboard...")
    if df.empty:
        logging.warning("DataFrame is empty, skipping preparation.")
        return df, member_data

    df_copy = df.copy()

    df_copy["original_author_name"] = df_copy["author_name"]

    id_mapped_names = df_copy["author_id"].map(ID_NAME_MAP)
    df_copy["author_name"] = id_mapped_names.fillna(df_copy["original_author_name"])

    EXCLUDE_LIST = list(IDS_TO_EXCLUDE) + list(SMURF_IDS)
    df_copy = df_copy[~df_copy["author_id"].isin(EXCLUDE_LIST)]

    if MIN_MESSAGE_COUNT > 0:
        total_counts = df_copy["author_name"].value_counts()
        active_users = total_counts[total_counts >= MIN_MESSAGE_COUNT].index
        df_copy = df_copy[df_copy["author_name"].isin(active_users)]
        active_user_count = len(active_users)
    else:
        active_user_count = len(df_copy["author_name"].unique())

    for col in [
        "character_count",
        "reaction_count",
        "attachment_count",
        "sticker_count",
    ]:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].fillna(0).astype(int)
        else:
            df_copy[col] = 0

    for col in ["mentioned_user_ids", "mentioned_role_ids"]:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(
                lambda x: x if isinstance(x, list) else []
            )
        else:
            df_copy[col] = pd.Series(
                [[] for _ in range(len(df_copy))], index=df_copy.index, dtype="object"
            )

    for col in [
        "replied_to_author_id",
        "thread_id",
        "thread_name",
        "message_type",
        "content",
        "jump_url",
        "channel_id",
    ]:
        if col not in df_copy.columns:
            df_copy[col] = pd.NA

    logging.info(
        f"Preparation complete. {len(df_copy)} messages and {active_user_count} active users retained."
    )
    return df_copy, member_data


async def main():
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN is not set! Please check your .env file.")
        return

    dashboard_df, member_data, role_data = await run_bot(
        DISCORD_TOKEN, DATA_DIR, CACHE_FILENAME, ROLE_DATA_FILENAME
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
            processed_df,
            processed_member_data,
            role_data,
            EXCLUDED_CHANNEL_IDS,
        )
        logging.info("Launching Dash web server on http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=False)
    else:
        logging.warning("No data was collected. Program will exit.")


if __name__ == "__main__":
    asyncio.run(main())
