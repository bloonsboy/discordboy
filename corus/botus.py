
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone

import discord
import pandas as pd

from dataus.constant import DATA_DIR, ID_NAME_MAP, SERVER_DATA_FILENAME
from corus.firestorus import FirestoreClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger('discord.http').setLevel(logging.ERROR)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)

intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot_data_future = None


async def create_message_data(message: discord.Message, server_id: int) -> dict:
    reactions_list = []
    all_user_ids = set()
    for reaction in message.reactions:
        try:
            users = [user async for user in reaction.users()]
            user_ids = [user.id for user in users]
            all_user_ids.update(user_ids)
            reactions_list.append({
                "emoji": str(reaction.emoji),
                "count": reaction.count,
                "user_ids": user_ids
            })
        except Exception:
            reactions_list.append({
                "emoji": str(reaction.emoji),
                "count": reaction.count,
                "user_ids": []
            })
    reactions_list.sort(key=lambda r: r["count"], reverse=True)
    # Stockage en timestamp UTC (float)
    created_at_ts = message.created_at.replace(tzinfo=timezone.utc).timestamp() if message.created_at else None
    edited_at_ts = message.edited_at.replace(tzinfo=timezone.utc).timestamp() if message.edited_at else None
    # Gestion du reply (réponse à un autre message)
    reply_to_message_id = None
    reply_to_user_id = None
    if message.reference is not None:
        reply_to_message_id = message.reference.message_id
        # Si le message d'origine est chargé, on peut avoir l'auteur
        resolved = getattr(message.reference, "resolved", None)
        if resolved is not None and hasattr(resolved, "author") and getattr(resolved, "author", None) is not None:
            reply_to_user_id = resolved.author.id
        else:
            reply_to_user_id = None
        # Si c'est un reply, il faut absolument un reply_to_user_id (sinon on ne stocke pas le reply)
        if reply_to_message_id is not None and reply_to_user_id is None:
            reply_to_message_id = None


    return {
        "server_id": server_id,
        "channel_id": message.channel.id,
        "message_id": message.id,
        "author_id": message.author.id,
        "content": message.content,
        "len_content": get_len_content(message.content),
        "created_at": created_at_ts,
        "edited_at": edited_at_ts,
        "mentions": list({m.id for m in message.mentions}),
        "mentioned_role_ids": [r.id for r in message.role_mentions],
        "attachments": len(message.attachments),
        "embeds": len(message.embeds),
        "reactions": reactions_list,
        "reacted_user_ids": list(all_user_ids),
        "reply_to_message_id": reply_to_message_id,
        "reply_to_user_id": reply_to_user_id,
        "pinned": message.pinned,
        "jump_url": message.jump_url,
    }

# Utilitaire pour convertir un timestamp UTC en datetime Paris (avec gestion été/hiver)
def timestamp_to_paris_datetime(ts):
    import pytz
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    paris = pytz.timezone('Europe/Paris')
    return utc_dt.astimezone(paris)


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

    # 1. Cherche le dernier timestamp dans Firestore pour ce channel
    from corus.firestorus import FirestoreClient
    firestore = FirestoreClient.get_instance()
    collection_name = os.getenv("FIRESTORE_COLLECTION", "messages")
    # On suppose que le server_id est accessible (sinon à passer en paramètre)
    server_id = str(getattr(channel.guild, 'id', 443091773602922497))
    channel_id = str(channel.id)
    last_ts = firestore.get_last_message_timestamp(collection_name, server_id, channel_id)

    after_date = None
    if last_ts is not None:
        after_date = datetime.fromtimestamp(float(last_ts), tz=timezone.utc)
    elif cache_df is not None and not cache_df.empty:
        channel_messages = cache_df[cache_df["channel_id"] == channel.id]
        if not channel_messages.empty:
            after_date = pd.to_datetime(channel_messages["created_at"].max())

    after_str = (
        f"after {after_date.strftime('%Y-%m-%d %H:%M:%S')}" if after_date else "from beginning"
    )

    messages_data = []
    start_time = datetime.now()
    progress_counter = 0

    import time
    max_retries = 5
    retry_delay = 30  # secondes
    attempt = 0
    while attempt < max_retries:
        try:
            from corus.firestorus import FirestoreClient
            firestore = FirestoreClient.get_instance()
            collection_name = os.getenv("FIRESTORE_COLLECTION", "messages")
            server_id = 443091773602922497
            async for message in channel.history(
                limit=None, after=after_date, oldest_first=True
            ):
                if message.author.bot:
                    continue
                msg_data = await create_message_data(message, server_id)
                messages_data.append(msg_data)
                if client.excluded_channel_ids is not None and message.channel.id in client.excluded_channel_ids:
                    continue
                progress_counter += 1
                if progress_counter % 10000 == 0:
                    logging.info(f"  Progress: {progress_counter} messages fetched from #{channel.name}...")

            # Ajout de tous les messages du channel dans Firestore à la fin
            if messages_data:
                firestore.insert_messages(collection_name, messages_data)

            main_msg_count = len(messages_data)
            break  # Succès, on sort de la boucle
        except Exception as e:
            # Gestion du DiscordServerError 503
            if hasattr(e, 'status') and getattr(e, 'status', None) == 503:
                attempt += 1
                logging.error(f"Discord 503 Service Unavailable sur #{channel.name}, tentative {attempt}/{max_retries}. Attente {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            else:
                raise

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
                    
                    msg_data = await create_message_data(message, server_id)
                    messages_data.append(msg_data)

            async for thread in channel.archived_threads(limit=None):
                async for message in thread.history(
                    limit=None, after=after_date, oldest_first=True
                ):
                    if message.author.bot:
                        continue
                    
                    progress_counter += 1
                    if progress_counter % 10000 == 0:
                        logging.info(f"  Progress: {progress_counter} messages fetched from #{channel.name} (archived threads)...")
                    
                    msg_data = await create_message_data(message, server_id)
                    messages_data.append(msg_data)
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
        # Si le paramètre est un ID (tout chiffre), cherche par id, sinon par nom
        if str(server_name).isdigit():
            guild = discord.utils.get(client.guilds, id=int(server_name))
        else:
            guild = discord.utils.get(client.guilds, name=server_name)
    else:
        guild = discord.utils.get(client.guilds, name="Virgule du 4'")

    if guild is None:
        logging.error(f"Server '{server_name}' not found. Available servers:")
        for g in client.guilds:
            logging.error(f"- {g.name} (ID: {g.id})")
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

    # Suppression de la logique de cache parquet
    cache_df = None

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

    for i, channel in enumerate(text_channels, 1):
        try:
            df = await fetch_channel_messages_as_df(channel, cache_df)
            if not df.empty:
                logging.info(f"[{i}/{len(text_channels)}] Processing #{channel.name}")
                logging.info(f"Added {len(df)} messages from #{channel.name}")
        except Exception as e:
            logging.exception(f"Error fetching #{channel.name}")

    final_df = cache_df

    await client.close()
    global bot_data_future
    if bot_data_future:
        bot_data_future.set_result((final_df, server_data))

    # Fermeture explicite de la connexion Firestore si elle existe
    if hasattr(FirestoreClient, '_instance') and FirestoreClient._instance:
        FirestoreClient._instance.close()


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
