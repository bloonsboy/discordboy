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

intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot_data_future = None


def get_len_content(content_str: str) -> int:
    if not content_str:
        return 0
    s = content_str
    s = re.sub(r"<a?:\w+:\d+>", "E", s)  # custom emoji
    s = re.sub(r"<@!?\d+>", "M", s)  # user mentions
    s = re.sub(r"<@&?\d+>", "M", s)  # role mentions
    s = re.sub(r"<@#?\d+>", "M", s)  # channel mentions
    s = re.sub(r"https?://\S+", "U", s)  # links
    s = re.sub(r"```([\s\S]*?)```", r"\1", s)  # code blocks
    s = re.sub(r"`([^`]*)`", r"\1", s)  # inline code
    s = re.sub(r"\|\|([\s\S]*?)\|\|", r"\1", s)  # spoilers
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)  # bold
    s = re.sub(r"\*([^*]+)\*", r"\1", s)  # italic
    s = re.sub(r"_([^_]+)_", r"\1", s)  # italic
    s = re.sub(r"__([^_]+)__", r"\1", s)  # underline
    s = re.sub(r"~~([^~]+)~~", r"\1", s)  # strikethrough
    s = re.sub(r"(?m)^>\s?", "", s)  # blockquotes
    s = s.replace(" ", "")  # remove spaces
    return len(s)


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
    logging.info(f"[START] Fetching #{channel.name} ({after_str})")

    messages_data = []
    start_time = datetime.now()

    try:
        # Fetch main channel messages
        async for message in channel.history(
            limit=None, after=after_date, oldest_first=True
        ):
            if message.author.bot:
                continue

            messages_data.append(
                {
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
                    "top_reaction_emoji": (
                        str(message.reactions[0].emoji) if message.reactions else None
                    ),
                    "top_reaction_count": (
                        int(message.reactions[0].count) if message.reactions else 0
                    ),
                    "pinned": message.pinned,
                    "jump_url": message.jump_url,
                }
            )

        main_msg_count = len(messages_data)

        # Fetch messages from threads (active + archived)
        threads_fetched = 0
        try:
            # Active threads
            for thread in channel.threads:
                threads_fetched += 1
                async for message in thread.history(
                    limit=None, after=after_date, oldest_first=True
                ):
                    if message.author.bot:
                        continue
                    messages_data.append(
                        {
                            "message_id": message.id,
                            "author_id": message.author.id,
                            "author_discord_name": message.author.name,
                            "channel_id": thread.id,
                            "content": message.content,
                            "len_content": get_len_content(message.content),
                            "created_at": message.created_at,
                            "edited_at": message.edited_at,
                            "attachments": len(message.attachments),
                            "embeds": len(message.embeds),
                            "mentions": [m.id for m in message.mentions],
                            "mentioned_role_ids": [r.id for r in message.role_mentions],
                            "top_reaction_emoji": (
                                str(message.reactions[0].emoji)
                                if message.reactions
                                else None
                            ),
                            "top_reaction_count": (
                                int(message.reactions[0].count)
                                if message.reactions
                                else 0
                            ),
                            "pinned": message.pinned,
                            "jump_url": message.jump_url,
                        }
                    )

            # Archived threads
            async for thread in channel.archived_threads(limit=None):
                threads_fetched += 1
                async for message in thread.history(
                    limit=None, after=after_date, oldest_first=True
                ):
                    if message.author.bot:
                        continue
                    messages_data.append(
                        {
                            "message_id": message.id,
                            "author_id": message.author.id,
                            "author_discord_name": message.author.name,
                            "channel_id": thread.id,
                            "content": message.content,
                            "len_content": get_len_content(message.content),
                            "created_at": message.created_at,
                            "edited_at": message.edited_at,
                            "attachments": len(message.attachments),
                            "embeds": len(message.embeds),
                            "mentions": [m.id for m in message.mentions],
                            "mentioned_role_ids": [r.id for r in message.role_mentions],
                            "top_reaction_emoji": (
                                str(message.reactions[0].emoji)
                                if message.reactions
                                else None
                            ),
                            "top_reaction_count": (
                                int(message.reactions[0].count)
                                if message.reactions
                                else 0
                            ),
                            "pinned": message.pinned,
                            "jump_url": message.jump_url,
                        }
                    )
        except Exception as e:
            logging.warning(f"Error fetching threads for #{channel.name}: {e}")

        thread_msg_count = len(messages_data) - main_msg_count
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = len(messages_data) / elapsed if elapsed > 0 else 0
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
    ]

    if channel_ids:
        text_channels = [c for c in text_channels if c.id in channel_ids]
        logging.info(f"Filtered to {len(text_channels)} channels")

    logging.info(f"Preparing to fetch data from {len(text_channels)} channels...")
    
    # Initialize cache_df as empty DataFrame if None
    if cache_df is None:
        cache_df = pd.DataFrame()

    # Fetch channels sequentially and save after each channel
    for i, channel in enumerate(text_channels, 1):
        logging.info(f"[{i}/{len(text_channels)}] Processing #{channel.name}")
        try:
            df = await fetch_channel_messages_as_df(channel, cache_df)
            if not df.empty:
                # Add new messages to cache
                if cache_df.empty:
                    cache_df = df
                    logging.info(f"Added {len(df)} messages from #{channel.name}")
                else:
                    initial_count = len(cache_df)
                    cache_df = pd.concat([cache_df, df], ignore_index=True).drop_duplicates(
                        subset=["message_id"], keep="last"
                    )
                    new_count = len(cache_df) - initial_count
                    logging.info(f"Added {new_count} new messages from #{channel.name}")
                
                # Save to parquet after each channel
                try:
                    cache_df.to_parquet(cache_path, index=False)
                    logging.info(f"✓ Cache saved ({len(cache_df)} total messages)")
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
        )
    )


async def run_bot(
    token: str,
    data_dir: str,
    cache_file: str,
    server_data_file: str,
    server_name: str = None,
    channel_ids: list = None,
    reaction_batch_size: int = 10,
) -> None:
    global bot_data_future
    bot_data_future = asyncio.Future()

    client.data_dir = data_dir
    client.cache_file = cache_file
    client.server_data_file = server_data_file
    client.server_name = server_name
    client.channel_ids = channel_ids
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
