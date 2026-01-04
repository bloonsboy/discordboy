import argparse
import asyncio
import json
import logging
import os

import pandas as pd
from corus.botus import run_bot
from dashboardus.appus import create_app
from dataus.constant import (
    CACHE_FILENAME,
    DATA_DIR,
    EXCLUDED_CHANNEL_IDS,
    IDS_TO_EXCLUDE,
    MIN_MESSAGE_COUNT,
    SERVER_DATA_FILENAME,
    SMURF_IDS,
    STATS_FILENAME,
)
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

os.makedirs(DATA_DIR, exist_ok=True)


def process_and_save_stats(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    excluded_channel_ids = [519208892207595540, 745615034201407610, 443134774291202088]
    df_copy = df_copy[~df_copy["channel_id"].isin(excluded_channel_ids)]
    df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"])
    df_copy["year"] = df_copy["timestamp"].dt.year
    yearly_counts = (
        df_copy.groupby(["author_name", "year"]).size().unstack(fill_value=0)
    )
    yearly_counts["total_messages"] = yearly_counts.sum(axis=1)
    final_csv_df = yearly_counts.reset_index().sort_values(
        "total_messages", ascending=False
    )
    count_cols = [col for col in final_csv_df.columns if col not in ["author_name"]]
    final_csv_df[count_cols] = final_csv_df[count_cols].astype(int)

    try:
        final_csv_df.to_csv(filename, index=False)
    except IOError as e:
        logging.error(f"Failed to save stats CSV: {e}")

    return df


def prepare_dataframe(df: pd.DataFrame, server_data: dict) -> pd.DataFrame:
    if df.empty:
        logging.warning("DataFrame is empty, skipping preparation.")
        return df

    df_copy = df.copy()

    author_map = {int(k): v["name"] for k, v in server_data.get("members", {}).items()}
    channel_map = {
        int(k): v["name"] for k, v in server_data.get("channels", {}).items()
    }

    df_copy["author_name"] = df_copy["author_id"].map(author_map)
    df_copy["channel_name"] = df_copy["channel_id"].map(channel_map)

    df_copy = df_copy.dropna(subset=["author_name"])
    df_copy["created_at"] = pd.to_datetime(df_copy["created_at"])

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
        "len_content",
        "total_reaction_count",
        "attachments",
        "embeds",
    ]:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].fillna(0).astype(int)
        else:
            df_copy[col] = 0

    for col in ["mentions", "mentioned_role_ids", "reactions"]:
        if col in df_copy.columns:
            df_copy[col] = (
                df_copy[col]
                .fillna("[]")
                .apply(lambda x: x if isinstance(x, (list, str)) else "[]")
            )
        else:
            df_copy[col] = "[]"

    for col in [
        "edited_at",
        "pinned",
        "content",
        "jump_url",
    ]:
        if col not in df_copy.columns:
            df_copy[col] = pd.NA

    df_copy.rename(columns={"created_at": "timestamp"}, inplace=True)

    logging.info(
        f"Preparation complete. {len(df_copy)} messages and {active_user_count} active users retained."
    )
    return df_copy


async def main():
    parser = argparse.ArgumentParser(description="Discord Activity Dashboard")
    parser.add_argument(
        "--server",
        type=str,
        default=None,
        help="Name of the Discord server to scrape (e.g., --server 'Virgule du 4')",
    )
    parser.add_argument(
        "--channels",
        type=str,
        default=None,
        help="Comma-separated list of channel IDs to fetch (e.g., --channels 123456789,987654321)",
    )
    parser.add_argument(
        "--throttle-every",
        type=int,
        default=40,
        help="Sleep after this many messages per channel",
    )
    args = parser.parse_args()

    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN is not set! Please check your .env file.")
        return

    server_name = args.server
    if server_name:
        logging.info(f"Will search for server: {server_name}")
    else:
        logging.info("No server specified. Will use the first available server.")

    channel_ids = None
    if args.channels:
        try:
            channel_ids = [int(ch_id.strip()) for ch_id in args.channels.split(",")]
            logging.info(f"Will fetch only channels: {channel_ids}")
        except ValueError:
            logging.error(
                "Invalid channel IDs format. Please use comma-separated integers."
            )
            return

    dashboard_df, server_data = await run_bot(
        DISCORD_TOKEN,
        DATA_DIR,
        CACHE_FILENAME,
        SERVER_DATA_FILENAME,
        server_name,
        channel_ids
    )

    if not dashboard_df.empty:
        processed_df = prepare_dataframe(dashboard_df, server_data)

        if processed_df.empty:
            logging.warning(
                "No data remaining after filtering. Dashboard cannot be launched."
            )
            return

        process_and_save_stats(processed_df, os.path.join(DATA_DIR, STATS_FILENAME))

        app = create_app(
            processed_df,
            server_data,
            EXCLUDED_CHANNEL_IDS,
        )
        logging.info("Launching Dash web server on http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=False)
    else:
        logging.warning("No data was collected. Program will exit.")


if __name__ == "__main__":
    asyncio.run(main())
