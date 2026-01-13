import asyncio
import json
import logging
import os
import re
from datetime import datetime

import discord
import pandas as pd

from dataus.constant import DATA_DIR, ID_NAME_MAP, SERVER_DATA_FILENAME

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger('discord.http').setLevel(logging.ERROR)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)

intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot_data_future = None


def create_message_data(message: discord.Message) -> dict:
    return {
        "message_id": message.id,
        "author_id": message.author.id,
        "author_discord_name": message.author.name,
        "channel_id": message.channel.id,
        "content": message.content,
        "len_content": get_len_content(message.content),
        "created_at": message.created_at,
        "edited_at": message.edited_at,
        "attachments": len(message.attachments),
        "embeds": len(message.embeds),
        "mentions": [m.id for m in message.mentions],
        "mentioned_role_ids": [r.id for r in message.role_mentions],
        "top_reaction_emoji": str(message.reactions[0].emoji) if message.reactions else None,
        "top_reaction_count": int(message.reactions[0].count) if message.reactions else 0,
        "pinned": message.pinned,
        "jump_url": message.jump_url,
    }


def get_len_content(content_str: str) -> int:
    if not content_str:
        return 0
    s = content_str
    patterns = [
        (r"<a?:\w+:\d+>", "E"),
        (r"<@!?\d+>", "M"),
        (r"<@&?\d+>", "M"),
        (r"<@#?\d+>", "M"),
        (r"https?://\S+", "U"),
        (r"```([\s\S]*?)```", r"\1"),
        (r"`([^`]*)`", r"\1"),
        (r"\|\|([\s\S]*?)\|\|", r"\1"),
        (r"\*\*([^*]+)\*\*", r"\1"),
        (r"\*([^*]+)\*", r"\1"),
        (r"_([^_]+)_", r"\1"),
        (r"__([^_]+)__", r"\1"),
        (r"~~([^~]+)~~", r"\1"),
        (r"(?m)^>\s?", ""),
    ]
    for pattern, repl in patterns:
        s = re.sub(pattern, repl, s)
    return len(s.replace(" ", ""))


async def fetch_channel_messages_as_df(
    channel: discord.TextChannel, cache_df: pd.DataFrame
) -> pd.DataFrame:
    after_date = None
    if cache_df is not None and not cache_df.empty:
        channel_messages = cache_df[cache_df["channel_id"] == channel.id]
        if not channel_messages.empty:
            after_date = pd.to_datetime(channel_messages["created_at"].max())

    after_str = (
        f"after {after_date.strftime('%Y-%m-%d')}" if after_date else "from beginning"
    )

    messages_data = []
    start_time = datetime.now()
    progress_counter = 0

    try:
        async for message in channel.history(
            limit=None, after=after_date, oldest_first=True
        ):
            if message.author.bot:
                continue

            messages_data.append(create_message_data(message))
            if client.excluded_channel_ids is not None and message.channel.id in client.excluded_channel_ids:
                continue
            progress_counter += 1
            if progress_counter % 10000 == 0:
                logging.info(f"  Progress: {progress_counter} messages fetched from #{channel.name}...")

        main_msg_count = len(messages_data)

        threads_fetched = 0
        try:
            for thread in channel.threads:
                threads_fetched += 1
                async for message in thread.history(
                    limit=None, after=after_date, oldest_first=True
                ):
                    if message.author.bot:
                        continue
                    
                    progress_counter += 1
                    if progress_counter % 10000 == 0:
                        logging.info(f"  Progress: {progress_counter} messages fetched from #{channel.name} (threads)...")
                    
                    messages_data.append(create_message_data(message))

            async for thread in channel.archived_threads(limit=None):
                async for message in thread.history(
                    limit=None, after=after_date, oldest_first=True
                ):
                    if message.author.bot:
                        continue
                    
                    progress_counter += 1
                    if progress_counter % 10000 == 0:
                        logging.info(f"  Progress: {progress_counter} messages fetched from #{channel.name} (archived threads)...")
                    
                    messages_data.append(create_message_data(message))
        except Exception as e:
            logging.warning(f"Error fetching threads for #{channel.name}: {e}")

        thread_msg_count = len(messages_data) - main_msg_count
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = len(messages_data) / elapsed if elapsed > 0 else 0
        
        if len(messages_data) > 0:
            logging.info(
                f"[END] #{channel.name}: {len(messages_data)} msgs ({main_msg_count} main + {thread_msg_count} threads from {threads_fetched} threads) in {elapsed:.1f}s ({rate:.0f} msg/s)"
            )

    except discord.errors.Forbidden:
        logging.warning(f"No access to channel #{channel.name}.")
    except Exception as e:
        logging.exception(f"Error fetching #{channel.name}")

    return pd.DataFrame(messages_data)


async def run_bot_logic(
    data_dir: str,
    cache_file: str,
    server_data_file: str,
    server_name: str = None,
    channel_ids: list = None,
    excluded_channel_ids: list = None,
) -> None:
    if server_name:
        guild = discord.utils.get(client.guilds, name=server_name)
    else:
        guild = discord.utils.get(client.guilds, name="Virgule du 4'")

    if guild is None:
        logging.error(f"Server '{server_name}' not found. Available servers:")
        for g in client.guilds:
            logging.error(f"- {g.name}")
        await client.close()
        return

    logging.info(f"Connected to server {guild.name}")
    await guild.chunk(cache=True)
    logging.info(f"Fetched data for {len(guild.members)} members.")

    server_data = {"roles": {}, "channels": {}, "members": {}}

    for role in guild.roles:
        if role.name != "@everyone":
            server_data["roles"][str(role.id)] = {
                "name": role.name,
                "color": str(role.color) if str(role.color) != "#000000" else "#99aab5",
            }

    for channel in guild.text_channels:
        server_data["channels"][str(channel.id)] = {"name": channel.name}

    for member in guild.members:
        if member.bot:
            continue
        member_id_str = str(member.id)
        author_name = ID_NAME_MAP.get(member_id_str, member.name)
        server_data["members"][member_id_str] = {
            "name": author_name,
            "original_name": member.name,
            "roles": [r.id for r in member.roles if r.name != "@everyone"],
            "top_role_color": (
                str(member.color) if str(member.color) != "#000000" else "#99aab5"
            ),
        }
        server_data["members"] = dict(
            sorted(
                server_data["members"].items(),
                key=lambda item: item[1]["original_name"].lower(),
            )
        )

    os.makedirs(data_dir, exist_ok=True)
    server_data_path = os.path.join(data_dir, server_data_file)
    try:
        with open(server_data_path, "w", encoding="utf-8") as f:
            json.dump(server_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.error(f"Error writing server data file: {e}")

    cache_path = os.path.join(data_dir, cache_file)
    cache_df = None
    if os.path.exists(cache_path):
        try:
            cache_df = pd.read_parquet(cache_path)
            cache_df["created_at"] = pd.to_datetime(cache_df["created_at"])
        except Exception as e:
            logging.error(f"Error loading cache: {e}.")
            cache_df = None
    else:
        logging.info("No cache file found.")

    text_channels = [
        c
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
        and (excluded_channel_ids is None or c.id not in excluded_channel_ids)
    ]

    if channel_ids:
        text_channels = [c for c in text_channels if c.id in channel_ids]
        logging.info(f"Filtered to {len(text_channels)} channels")

    logging.info(f"Preparing to fetch data from {len(text_channels)} channels...")
    
    if cache_df is None:
        cache_df = pd.DataFrame()

    for i, channel in enumerate(text_channels, 1):
        try:
            df = await fetch_channel_messages_as_df(channel, cache_df)
            if not df.empty:
                logging.info(f"[{i}/{len(text_channels)}] Processing #{channel.name}")
                if cache_df.empty:
                    logging.info(f"Added {len(df)} messages from #{channel.name}")
                else:
                    initial_count = len(cache_df)
                    cache_df = pd.concat([cache_df, df], ignore_index=True).drop_duplicates(
                        subset=["message_id"], keep="last"
                    )
                    new_count = len(cache_df) - initial_count
                    logging.info(f"Added {new_count} new messages from #{channel.name}")
                
                try:
                    cache_df.to_parquet(cache_path, index=False)
                except Exception as e:
                    logging.error(f"Error saving parquet file: {e}")
        except Exception as e:
            logging.exception(f"Error fetching #{channel.name}")

    final_df = cache_df

    await client.close()
    global bot_data_future
    if bot_data_future:
        bot_data_future.set_result((final_df, server_data))


@client.event
async def on_ready():
    logging.info(f"Bot {client.user} connected")
    client.loop.create_task(
        run_bot_logic(
            client.data_dir,
            client.cache_file,
            client.server_data_file,
            client.server_name,
            client.channel_ids,
            client.excluded_channel_ids,
        )
    )


async def run_bot(
    token: str,
    data_dir: str,
    cache_file: str,
    server_data_file: str,
    server_name: str = None,
    channel_ids: list = None,
    excluded_channel_ids: list = None,
    reaction_batch_size: int = 10,
) -> None:
    global bot_data_future
    bot_data_future = asyncio.Future()

    client.data_dir = data_dir
    client.cache_file = cache_file
    client.server_data_file = server_data_file
    client.server_name = server_name
    client.channel_ids = channel_ids
    client.excluded_channel_ids = excluded_channel_ids
    client.reaction_batch_size = reaction_batch_size

    try:
        await client.start(token)
    except discord.LoginFailure:
        logging.error("Invalid Discord token. Please check your .env file.")
        bot_data_future.set_result((pd.DataFrame(), {}))
    except Exception as e:
        logging.error(f"An error occurred during client.start: {e}")
        if not bot_data_future.done():
            bot_data_future.set_result((pd.DataFrame(), {}))

    return await bot_data_future
