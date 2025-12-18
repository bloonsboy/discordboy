import asyncio
import json
import logging
import os
import re
from datetime import datetime

import discord
import pandas as pd
from tqdm.asyncio import tqdm
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
    content_no_custom_emote = re.sub(r"<a?:\w+:\d+>", "E", content_str)
    content_no_space = content_no_custom_emote.replace(" ", "")
    return len(content_no_space)


async def fetch_channel_messages_as_df(
    channel: discord.TextChannel, cache_df: pd.DataFrame
) -> pd.DataFrame:
    after_date = None
    if cache_df is not None and not cache_df.empty:
        channel_messages = cache_df[cache_df["channel_id"] == channel.id]
        if not channel_messages.empty:
            after_date = pd.to_datetime(channel_messages["created_at"].max())

    if after_date is None or await channel.history(limit=1, after=after_date).flatten():
        logging.info(
            f"Fetching #{channel.name} (after {after_date or ''})"
        )

    messages_data = []
    messages_with_reactions = []
    message_count = 0

    try:
        chunk_size = 10000
        chunk_start = datetime.now()

        async for message in channel.history(limit=None, after=after_date, oldest_first=True):
            if message.author.bot:
                continue

            messages_data.append(
                {
                    "message_id": message.id,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                    "content": message.content,
                    "len_content": get_len_content(message.content),
                    "created_at": message.created_at,
                    "edited_at": message.edited_at,
                    "attachments": len(message.attachments),
                    "embeds": len(message.embeds),
                    "mentions": [m.id for m in message.mentions],
                    "mentioned_role_ids": [r.id for r in message.role_mentions],
                    "reactions": "[]",
                    "total_reaction_count": 0,
                    "pinned": message.pinned,
                    "jump_url": message.jump_url,
                }
            )

            if message.reactions:
                messages_with_reactions.append((message_count, message))
            message_count += 1

            if message_count % chunk_size == 0:
                chunk_time = (datetime.now() - chunk_start).total_seconds()
                rate = chunk_size / chunk_time if chunk_time > 0 else 0
                logging.info(
                    f"  #{channel.name}: {message_count} messages fetched ({rate:.0f} messages/s)"
                )
                chunk_start = datetime.now()
            await asyncio.sleep(0.02)

        if messages_with_reactions:
            async def process_message_reactions(index, message):
                unique_reactors = set()
                reactions_summary = []

                async def fetch_reaction_users(reaction):
                    try:
                        users = [
                            user async for user in reaction.users() if not user.bot
                        ]
                        return {
                            "emoji": str(reaction.emoji),
                            "count": len(users),
                            "user_ids": [u.id for u in users],
                        }
                    except Exception:
                        return {
                            "emoji": str(reaction.emoji),
                            "count": reaction.count,
                            "user_ids": [],
                        }

                reaction_results = await asyncio.gather(
                    *[fetch_reaction_users(r) for r in message.reactions],
                    return_exceptions=True,
                )

                for result in reaction_results:
                    if isinstance(result, dict):
                        reactions_summary.append(
                            {"emoji": result["emoji"], "count": result["count"]}
                        )
                        unique_reactors.update(result["user_ids"])

                return index, json.dumps(reactions_summary), len(unique_reactors)

            reaction_tasks = [
                process_message_reactions(idx, msg)
                for idx, msg in messages_with_reactions
            ]
            reaction_updates = await asyncio.gather(
                *reaction_tasks, return_exceptions=True
            )

            for update in reaction_updates:
                if isinstance(update, tuple) and len(update) == 3:
                    idx, reactions_json, total_count = update
                    messages_data[idx]["reactions"] = reactions_json
                    messages_data[idx]["total_reaction_count"] = total_count

        if message_count > 0:
            logging.info(
                f"#{channel.name} finished. {message_count} new messages."
            )
        elif after_date is not None:
            pass
        else:
            logging.info(f"Fetching #{channel.name} finished. 0 messages found.")

    except discord.errors.Forbidden:
        logging.warning(f"No access to channel #{channel.name}.")
    except Exception as e:
        logging.error(f"Error fetching messages from #{channel.name}: {e}")

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
            sorted(server_data["members"].items(), key=lambda item: item[1]["original_name"].lower())
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

    logging.info(f"Fetch data from {len(text_channels)} channels")
    all_dfs = []

    for i in range(0, len(text_channels)):
        tasks = [fetch_channel_messages_as_df(text_channels[i], cache_df)]
        result = await asyncio.gather(*tasks, return_exceptions=True)
        if isinstance(result, pd.DataFrame):
            all_dfs.append(result)
        elif isinstance(result, Exception):
            logging.error(f"Error in batch processing: {result}")
    valid_dfs = [df for df in all_dfs if not df.empty]

    if not valid_dfs and cache_df is None:
        final_df = pd.DataFrame()
    elif not valid_dfs and cache_df is not None:
        final_df = cache_df
    else:
        new_data_df = pd.concat(valid_dfs, ignore_index=True)
        if cache_df is not None:
            logging.info(f"Adding {len(new_data_df)} new messages.")
            final_df = pd.concat(
                [cache_df, new_data_df], ignore_index=True
            ).drop_duplicates(subset=["message_id"], keep="last")
        else:
            logging.info(f"Creating new cache with {len(new_data_df)} messages.")
            final_df = new_data_df

        try:
            final_df.to_parquet(cache_path, index=False)
        except Exception as e:
            logging.error(f"Error saving parquet file: {e}")

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
) -> None:
    global bot_data_future
    bot_data_future = asyncio.Future()

    client.data_dir = data_dir
    client.cache_file = cache_file
    client.server_data_file = server_data_file
    client.server_name = server_name
    client.channel_ids = channel_ids

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
