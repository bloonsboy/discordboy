import argparse
import asyncio
import json
import logging
import os

import pandas as pd
from dotenv import load_dotenv

from corus.botus import run_bot
from dashboardus.appus import create_app
from dataus.constant import (
    CACHE_FILENAME,
    DATA_DIR,
    EXCLUDED_CHANNEL_IDS,
    ID_NAME_MAP,
    IDS_TO_EXCLUDE,
    MIN_MESSAGE_COUNT,
    MUDAE_CHANNELS,
    SERVER_DATA_FILENAME,
    SMURF_IDS,
    STATS_FILENAME,
)

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
    excluded_ids = list(EXCLUDED_CHANNEL_IDS) + list(MUDAE_CHANNELS)
    df_copy = df_copy[~df_copy["channel_id"].isin(excluded_ids)]
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
    
    for id_str, name in ID_NAME_MAP.items():
        author_id = int(id_str)
        if author_id not in author_map:
            author_map[author_id] = name
    
    channel_map = {
        int(k): v["name"] for k, v in server_data.get("channels", {}).items()
    }

    df_copy["author_name"] = df_copy["author_id"].map(author_map)
    df_copy["channel_name"] = df_copy["channel_id"].map(channel_map)

    mask_unknown = df_copy["author_name"].isna()
    df_copy.loc[mask_unknown, "author_name"] = df_copy.loc[mask_unknown].apply(
        lambda row: row.get("author_discord_name", f"Ex-membre ({row['author_id']})"),
        axis=1
    )
    df_copy["created_at"] = pd.to_datetime(df_copy["created_at"], utc=True)

    EXCLUDE_LIST = list(IDS_TO_EXCLUDE) + list(SMURF_IDS)
    df_copy = df_copy[~df_copy["author_id"].isin(EXCLUDE_LIST)]

    active_user_count = len(df_copy["author_name"].unique())

    if "top_reaction_count" in df_copy.columns:
        df_copy["total_reaction_count"] = df_copy["top_reaction_count"]

    numeric_cols = ["len_content", "total_reaction_count", "attachments", "embeds"]
    for col in numeric_cols:
        df_copy[col] = df_copy.get(col, 0).fillna(0).astype(int) if col in df_copy.columns else 0

    list_cols = ["mentions", "mentioned_role_ids", "reactions"]
    for col in list_cols:
        if col in df_copy.columns:
            # Handle both string JSON, numpy arrays, and lists
            def parse_list_col(x):
                # Handle None first
                if x is None:
                    return []
                # Handle numpy arrays and pandas scalars
                try:
                    if hasattr(x, 'size') and x.size == 0:
                        return []
                    # Check for pandas NA/None values more carefully
                    if pd.isna(x).any() if hasattr(pd.isna(x), 'any') else pd.isna(x):
                        return []
                except (ValueError, TypeError):
                    # If pd.isna fails, continue to other checks
                    pass
                
                if isinstance(x, str):
                    try:
                        return json.loads(x)
                    except (json.JSONDecodeError, ValueError):
                        return []
                if isinstance(x, list):
                    return x
                # Handle numpy arrays or other iterables
                try:
                    return list(x)
                except (TypeError, ValueError):
                    return []
            
            df_copy[col] = df_copy[col].apply(parse_list_col)
        else:
            df_copy[col] = [[] for _ in range(len(df_copy))]

    optional_cols = ["edited_at", "pinned", "content", "jump_url"]
    for col in optional_cols:
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
            logging.info(f"Will fetch {len(channel_ids)} specific channel(s)")
        except ValueError as e:
            logging.error(f"Invalid channel IDs format: {e}")
            return

    dashboard_df, server_data = await run_bot(
        DISCORD_TOKEN,
        DATA_DIR,
        CACHE_FILENAME,
        SERVER_DATA_FILENAME,
        server_name,
        channel_ids,
        EXCLUDED_CHANNEL_IDS,
    )

    if dashboard_df.empty:
        logging.warning("No data was collected. Program will exit.")
        return

    processed_df = prepare_dataframe(dashboard_df, server_data)
    if processed_df.empty:
        logging.warning("No data remaining after filtering. Dashboard cannot be launched.")
        return

    process_and_save_stats(processed_df, os.path.join(DATA_DIR, STATS_FILENAME))

    app = create_app(processed_df, server_data, MUDAE_CHANNELS)
    logging.info("Launching Dash web server on http://localhost:8050/")
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    asyncio.run(main())
