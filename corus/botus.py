# discordboy/corus/botus.py

import asyncio
import json
import logging
import os
from datetime import datetime

import discord
import pandas as pd

from discordboy.dataus.constant import EXCLUDED_CHANNEL_IDS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.reactions = True

client = discord.Client(intents=intents)
bot_data_future = None


async def fetch_channel_messages_as_df(channel, cache_df):
    after_date = None
    if cache_df is not None and not cache_df.empty:
        channel_messages = cache_df[cache_df["channel_id"] == channel.id]
        if not channel_messages.empty:
            after_date = pd.to_datetime(channel_messages["timestamp"].max())

    logging.info(
        f"[START] Fetching #{channel.name} (after {after_date or 'beginning'})"
    )

    messages_data = []
    message_count = 0

    try:
        async for message in channel.history(limit=None, after=after_date):
            if message.author.bot:
                continue

            reaction_user_ids = set()
            for reaction in message.reactions:
                async for user in reaction.users():
                    reaction_user_ids.add(user.id)

            replied_to_author_id = None
            if (
                message.reference
                and message.reference.resolved
                and isinstance(message.reference.resolved, discord.Message)
            ):
                replied_to_author_id = message.reference.resolved.author.id

            thread_id = message.thread.id if message.thread else None
            thread_name = message.thread.name if message.thread else None

            messages_data.append(
                {
                    "message_id": message.id,
                    "timestamp": message.created_at,
                    "author_id": message.author.id,
                    "author_name": message.author.name,
                    "channel_id": message.channel.id,
                    "channel_name": message.channel.name,
                    "content": message.content,
                    "character_count": len(message.content.replace(" ", "")),
                    "mentioned_user_ids": [m.id for m in message.mentions],
                    "mentioned_role_ids": [r.id for r in message.role_mentions],
                    "replied_to_author_id": replied_to_author_id,
                    "reaction_count": len(reaction_user_ids),
                    "jump_url": message.jump_url,
                    "attachment_count": len(message.attachments),
                    "sticker_count": len(message.stickers),
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "message_type": str(message.type),
                }
            )
            message_count += 1

        if message_count > 0:
            logging.info(
                f"[END] Fetching #{channel.name} finished. {message_count} new messages retrieved."
            )

    except discord.errors.Forbidden:
        logging.warning(f"No access to channel #{channel.name}. Skipping.")
    except Exception as e:
        logging.error(f"Error fetching messages from #{channel.name}: {e}")

    return pd.DataFrame(messages_data)


async def run_bot_logic(data_dir, cache_file, role_color_file, role_name_file):
    logging.info(f"Fetching data for server '{client.guilds[0].name}'...")
    guild = client.guilds[0]

    start_chunk = datetime.now()
    await guild.chunk(cache=True)
    end_chunk = datetime.now()
    logging.info(
        f"Fetched data for {len(guild.members)} members in {(end_chunk - start_chunk).total_seconds():.2f} seconds."
    )

    member_data = {}
    for member in guild.members:
        if member.bot:
            continue
        member_data[str(member.id)] = {
            "name": member.name,
            "roles": [role.name for role in member.roles if role.name != "@everyone"],
            "top_role_color": (
                str(member.color) if str(member.color) != "#000000" else "#99aab5"
            ),
        }

    role_colors_map = {
        str(role.id): str(role.color)
        for role in guild.roles
        if str(role.color) != "#000000"
    }
    role_names_map = {str(role.id): role.name for role in guild.roles}

    os.makedirs(data_dir, exist_ok=True)
    role_color_path = os.path.join(data_dir, role_color_file)
    role_name_path = os.path.join(data_dir, role_name_file)

    try:
        with open(role_color_path, "w", encoding="utf-8") as f:
            json.dump(role_colors_map, f, ensure_ascii=False, indent=4)

        with open(role_name_path, "w", encoding="utf-8") as f:
            json.dump(role_names_map, f, ensure_ascii=False, indent=4)

    except IOError as e:
        logging.error(f"Error writing role file: {e}")

    cache_path = os.path.join(data_dir, cache_file)
    cache_df = None
    if os.path.exists(cache_path):
        try:
            logging.info(f"Loading cache from {cache_path}...")
            cache_df = pd.read_parquet(cache_path)
            cache_df["timestamp"] = pd.to_datetime(cache_df["timestamp"])
        except Exception as e:
            logging.error(f"Error loading cache: {e}. Fetching all messages.")
            cache_df = None
    else:
        logging.info("No cache file found. Fetching all messages.")

    text_channels = [
        c
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
        and str(c.id) not in EXCLUDED_CHANNEL_IDS
    ]
    logging.info(f"Preparing to fetch data from {len(text_channels)} channels...")

    tasks = [
        fetch_channel_messages_as_df(channel, cache_df) for channel in text_channels
    ]

    all_dfs = await asyncio.gather(*tasks)

    non_empty_dfs = [df for df in all_dfs if not df.empty]

    if non_empty_dfs:
        new_data_df = pd.concat(non_empty_dfs, ignore_index=True)
    else:
        new_data_df = pd.DataFrame()

    if not new_data_df.empty or cache_df is None:
        if cache_df is not None:
            final_df = pd.concat(
                [cache_df, new_data_df], ignore_index=True
            ).drop_duplicates(subset=["message_id"], keep="last")
        else:
            final_df = new_data_df

        try:
            final_df.to_parquet(cache_path, index=False)
        except Exception as e:
            logging.error(f"Error saving parquet file: {e}")
    else:
        final_df = cache_df

    await client.close()

    global bot_data_future
    if bot_data_future:
        bot_data_future.set_result(
            (final_df, role_colors_map, member_data, role_names_map)
        )


@client.event
async def on_ready():
    client.loop.create_task(
        run_bot_logic(
            client.data_dir,
            client.cache_file,
            client.role_color_file,
            client.role_name_file,
        )
    )


async def run_bot(token, data_dir, cache_file, role_color_file, role_name_file):
    global bot_data_future
    bot_data_future = asyncio.Future()

    client.data_dir = data_dir
    client.cache_file = cache_file
    client.role_color_file = role_color_file
    client.role_name_file = role_name_file

    try:
        await client.start(token)
    except discord.LoginFailure:
        logging.error("Invalid Discord token. Please check your .env file.")
        bot_data_future.set_result((pd.DataFrame(), {}, {}, {}))
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        if not bot_data_future.done():
            bot_data_future.set_result((pd.DataFrame(), {}, {}, {}))

    return await bot_data_future
