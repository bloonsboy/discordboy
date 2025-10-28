# corus/botus.py

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
import re

import discord
import pandas as pd
import pyarrow

# --- Configuration --- (Keep your existing config)
IDS_TO_EXCLUDE = [456226577798135808]
ID_MERGE_MAP = {"183303146955735040": "lupoticha"}
NAME_MERGE_MAP = {"iwantdog": ".redhot_"}
# --- End Configuration ---

# --- Intents ---
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

client = discord.Client(intents=intents)
user_id_to_name_map = {}
role_colors_map = {}
member_data = {}


async def fetch_guild_data(guild, colors_filename):
    """Fetches member data (roles, color) and saves role colors."""
    global role_colors_map, member_data
    logging.info(f"Fetching data for server '{guild.name}'...")
    logging.info(
        "This operation (guild.chunk) can take several minutes on large servers..."
    )
    start_time = time.time()

    try:
        await guild.chunk(cache=True)
        end_time = time.time()
        logging.info(
            f"Fetched data for {guild.member_count} members in {end_time - start_time:.2f} seconds."
        )

        role_colors_map = {}
        member_data = {}

        for member in guild.members:
            if member.bot:
                continue

            member_data[str(member.id)] = {
                "name": str(member),
                "roles": [
                    role.name for role in member.roles if role.name != "@everyone"
                ],
                "color": str(member.color) if str(member.color) != "#000000" else None,
            }

            if str(member.color) != "#000000":
                role_colors_map[str(member.id)] = str(member.color)

        with open(colors_filename, "w") as f:
            json.dump(role_colors_map, f, indent=4)
        logging.info(f"Role colors saved to {colors_filename}.")

    except discord.errors.ChunkedGuildNotFound:
        logging.error(
            "Failed to chunk guild, maybe missing Members Intent or server too large?"
        )
    except Exception as e:
        logging.error(f"Error fetching guild data: {e}")

    return member_data


async def fetch_channel_messages_as_df(channel, after_date=None):
    """Fetches messages from a channel and returns them as a DataFrame."""
    messages_data = []
    if "mudae" in channel.name.lower() or "log" in channel.name.lower():
        return pd.DataFrame()

    # --- LOGGING CORRECTION: Always log start ---
    log_message = f"[START] Fetching #{channel.name}"
    if after_date:
        log_message += f" (after {after_date.strftime('%Y-%m-%d %H:%M')})"
    logging.info(log_message)
    # --- END LOGGING CORRECTION ---

    start_time = time.time()
    count = 0
    try:
        async for message in channel.history(limit=None, after=after_date):
            if not message.author.bot:
                mentioned_user_ids = [
                    str(mention.id) for mention in message.mentions if not mention.bot
                ]

                replied_to_author_id = None
                if message.reference and isinstance(
                    message.reference.resolved, discord.Message
                ):
                    # Check if the resolved message and its author exist and are not bots
                    if (
                        message.reference.resolved.author
                        and not message.reference.resolved.author.bot
                    ):
                        replied_to_author_id = str(message.reference.resolved.author.id)

                reactions_unique_users = set()
                # Check if message has reactions before iterating
                if message.reactions:
                    for reaction in message.reactions:
                        try:
                            # Iterate using users() async iterator
                            async for user in reaction.users():
                                if not user.bot:
                                    reactions_unique_users.add(str(user.id))
                        except discord.HTTPException as e:
                            logging.warning(
                                f"Could not fetch users for reaction in message {message.id} (Channel: #{channel.name}): {e}"
                            )
                        except (
                            Exception
                        ) as e:  # Catch potential other errors during reaction fetching
                            logging.error(
                                f"Unexpected error fetching reaction users for message {message.id}: {e}"
                            )

                attachment_count = len(message.attachments)
                sticker_count = len(message.stickers)
                thread_id = message.thread.id if message.thread else None
                thread_name = message.thread.name if message.thread else None
                message_type = str(message.type)

                messages_data.append(
                    {
                        "message_id": message.id,
                        "timestamp": message.created_at,
                        "author_id": message.author.id,
                        "author_name": str(message.author),
                        "channel_id": channel.id,
                        "character_count": len(message.content.replace(" ", "")),
                        "content": message.content,
                        "mentioned_user_ids": mentioned_user_ids,
                        "replied_to_author_id": replied_to_author_id,
                        "reaction_users": list(reactions_unique_users),
                        "reaction_count": len(reactions_unique_users),
                        "jump_url": message.jump_url,
                        "attachment_count": attachment_count,
                        "sticker_count": sticker_count,
                        "thread_id": thread_id,
                        "thread_name": thread_name,
                        "message_type": message_type,
                    }
                )
                count += 1

        # --- LOGGING CORRECTION: Log end only if messages were found ---
        if count > 0:
            end_time = time.time()
            logging.info(
                f"[END] Fetching #{channel.name} finished. {count} messages retrieved in {end_time - start_time:.2f} seconds."
            )
        # --- END LOGGING CORRECTION ---

        return pd.DataFrame(messages_data)
    except discord.errors.Forbidden:
        logging.warning(
            f"No permission to read history for #{channel.name}. Skipping."
        )  # Log permission issues
        pass
    except Exception as e:
        logging.error(f"Error in #{channel.name}: {e}")
        return pd.DataFrame()


async def fetch_messages_with_cache(guild, cache_filename):
    """Fetches channel messages using a cache for efficiency."""
    global user_id_to_name_map
    df_cache = pd.DataFrame()
    latest_timestamps = {}

    # --- Cache Loading ---
    if os.path.exists(cache_filename):
        logging.info(f"Loading cache from {cache_filename}...")
        try:
            df_cache = pd.read_parquet(cache_filename)
            required_cols = [
                "message_id",
                "timestamp",
                "author_id",
                "author_name",
                "channel_id",
                "character_count",
                "content",
                "mentioned_user_ids",
                "replied_to_author_id",
                "reaction_users",
                "reaction_count",
                "jump_url",
                "attachment_count",
                "sticker_count",
                "thread_id",
                "thread_name",
                "message_type",
            ]
            for col in required_cols:
                if col not in df_cache.columns:
                    logging.warning(f"Cache missing column '{col}', adding empty.")
                    if col in ["mentioned_user_ids", "reaction_users"]:
                        df_cache[col] = pd.Series(dtype="object")
                    else:
                        df_cache[col] = pd.NA

            for col in ["mentioned_user_ids", "reaction_users"]:
                # Ensure existing lists remain lists, fill NA with empty list
                df_cache[col] = df_cache[col].apply(
                    lambda x: x if isinstance(x, list) else []
                )

            df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"], utc=True)

            if not df_cache.empty:
                # Update user map from cache first
                df_known_users_cache = df_cache[
                    df_cache["author_name"] != "Deleted User#0000"
                ].drop_duplicates(subset=["author_id"], keep="last")
                user_id_to_name_map = pd.Series(
                    df_known_users_cache.author_name.values,
                    index=df_known_users_cache.author_id,
                ).to_dict()

                # Get latest timestamp per channel *from the cache*
                latest_timestamps = (
                    df_cache.loc[df_cache.groupby("channel_id")["timestamp"].idxmax()]
                    .set_index("channel_id")["timestamp"]
                    .to_dict()
                )
        except Exception as e:
            logging.error(
                f"Failed to load or process cache file {cache_filename}: {e}. Fetching all messages."
            )
            df_cache = pd.DataFrame()
            latest_timestamps = {}
            user_id_to_name_map = {}  # Reset map if cache fails
    else:
        logging.info("No cache file found. Fetching all messages.")

    # --- Fetching New Messages ---
    # Filter channels first
    channels_to_fetch = [
        c
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
    ]
    logging.info(
        f"Preparing to fetch messages for {len(channels_to_fetch)} channels..."
    )  # Log before gather

    tasks = [
        asyncio.create_task(
            fetch_channel_messages_as_df(c, after_date=latest_timestamps.get(c.id))
        )
        for c in channels_to_fetch  # Use the filtered list
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    logging.info("Finished fetching tasks for all channels.")  # Log after gather

    new_dfs = []
    for i, res in enumerate(results):
        # Use the filtered list index to get the correct channel
        channel_name = (
            channels_to_fetch[i].name
            if i < len(channels_to_fetch)
            else "Unknown Channel"
        )
        if isinstance(res, pd.DataFrame) and not res.empty:
            new_dfs.append(res)
        elif isinstance(res, Exception):
            # Don't log Forbidden errors as they are expected
            if not isinstance(res, discord.errors.Forbidden):
                logging.error(f"Task for channel '{channel_name}' failed: {res}")

    df_new = pd.concat(new_dfs, ignore_index=True) if new_dfs else pd.DataFrame()

    # --- Merging Cache and New Data ---
    if not df_new.empty:
        logging.info(f"Fetched {len(df_new)} new messages across channels.")
        # Update user map again with names from new messages (overwrites old cache names if changed)
        df_new_known = df_new[
            df_new["author_name"] != "Deleted User#0000"
        ].drop_duplicates(subset=["author_id"], keep="last")
        user_id_to_name_map.update(
            pd.Series(
                df_new_known.author_name.values, index=df_new_known.author_id
            ).to_dict()
        )

        # Ensure UTC timestamps
        if "timestamp" in df_new.columns:
            df_new["timestamp"] = pd.to_datetime(df_new["timestamp"]).dt.tz_convert(
                "UTC"
            )

        if not df_cache.empty and "timestamp" in df_cache.columns:
            df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"]).dt.tz_convert(
                "UTC"
            )

        final_df = pd.concat([df_cache, df_new], ignore_index=True)
        # Ensure message_id exists before dropping duplicates
        if "message_id" in final_df.columns:
            final_df = final_df.drop_duplicates(subset=["message_id"], keep="last")
        else:
            logging.warning(
                "Column 'message_id' not found, cannot drop duplicates based on it."
            )

    else:
        logging.info("No new messages found.")
        final_df = df_cache

    if final_df.empty:
        logging.warning("No messages collected or cached.")
        return final_df

    # --- Data Cleaning & Saving ---
    final_df = final_df[~final_df["author_id"].isin(IDS_TO_EXCLUDE)]

    # --- IMPORTANT: Perform Name Mapping BEFORE Saving ---
    # This ensures the cache contains the most current display names

    # Map original names first (used for merges)
    final_df["original_author_name"] = final_df["author_id"].map(user_id_to_name_map)
    unknown_mask = final_df["original_author_name"].isnull()
    final_df.loc[unknown_mask, "original_author_name"] = "ID: " + final_df.loc[
        unknown_mask, "author_id"
    ].astype(str)

    # Initialize author_name with original, then apply merges
    final_df["author_name"] = final_df["original_author_name"]

    if ID_MERGE_MAP:
        for old_id, new_name in ID_MERGE_MAP.items():
            try:  # Add try-except for potential type issues
                final_df.loc[final_df["author_id"] == int(old_id), "author_name"] = (
                    new_name
                )
            except ValueError:
                logging.warning(
                    f"Could not convert ID '{old_id}' to integer for merging."
                )

    if NAME_MERGE_MAP:
        for old_name, new_name in NAME_MERGE_MAP.items():
            final_df.loc[
                final_df["original_author_name"] == old_name, "author_name"
            ] = new_name

    # --- Save Cache AFTER name mapping ---
    logging.info(f"Saving updated cache to {cache_filename}...")
    try:
        # Save only necessary columns? Or all? Let's save all for now.
        final_df.to_parquet(cache_filename)
        logging.info("Save complete.")
    except Exception as e:
        logging.error(f"Failed to save cache: {e}")

    # Return the DataFrame with mapped names
    return final_df


async def run_bot(token, cache_filename, colors_filename):
    """Main function to run the bot and start the process."""
    global dashboard_df, user_id_to_name_map_global, role_colors_map_global, member_data_global
    dashboard_df = pd.DataFrame()
    user_id_to_name_map_global = {}
    role_colors_map_global = {}
    member_data_global = {}

    on_ready_event = asyncio.Event()

    @client.event
    async def on_ready():
        global dashboard_df, user_id_to_name_map_global, role_colors_map_global, member_data_global
        logging.info(f"{client.user} connected to Discord!")
        if not client.guilds:
            logging.error("Bot is not in any server. Shutting down...")
            await client.close()
            on_ready_event.set()
            return

        guild = client.guilds[0]
        try:
            member_data_fetched = await fetch_guild_data(guild, colors_filename)
            main_df = await fetch_messages_with_cache(guild, cache_filename)
            logging.info("Data collection finished.")

            dashboard_df = main_df
            # Use the final user_id_to_name_map which includes updates from cache AND new messages
            user_id_to_name_map_global = user_id_to_name_map
            role_colors_map_global = role_colors_map
            member_data_global = member_data_fetched

        except Exception as e:
            logging.error(
                f"An error occurred during data collection: {e}", exc_info=True
            )
        finally:
            logging.info("Closing Discord client.")
            await client.close()
            on_ready_event.set()

    try:
        logging.info("Starting Discord client...")
        client_task = asyncio.create_task(client.start(token))
        await on_ready_event.wait()
        logging.info("Client task finished.")

    except discord.LoginFailure:
        logging.error("Login failed: Invalid token provided.")
    except Exception as e:
        logging.error(
            f"An unexpected error occurred running the bot: {e}", exc_info=True
        )

    # Return the results gathered during on_ready
    return dashboard_df, role_colors_map_global, member_data_global
