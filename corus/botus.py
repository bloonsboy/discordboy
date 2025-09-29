import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta

import discord
import pandas as pd
import pyarrow

# ==============================================================================
#  CONFIGURATION DES DONNÉES
# ==============================================================================
IDS_TO_EXCLUDE = [456226577798135808]
ID_MERGE_MAP = {"183303146955735040": "lupoticha"}
NAME_MERGE_MAP = {"iwantdog": ".redhot_"}
# ==============================================================================

# Update the intents to include members
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
user_id_to_name_map = {}
role_colors_map = {}


async def fetch_and_save_role_colors(guild, filename):
    """Récupère et sauvegarde les couleurs de rôle des membres du serveur."""
    logging.info("Récupération des couleurs de rôle...")
    global role_colors_map
    await guild.chunk()
    role_colors_map = {
        str(member.id): str(member.color)
        for member in guild.members
        if not member.bot and str(member.color) != "#000000"
    }
    
    with open(filename, "w") as f:
        json.dump(role_colors_map, f, indent=4)
    logging.info(f"Couleurs de rôle sauvegardées dans {filename}.")

async def fetch_channel_messages_as_df(channel, after_date=None):
    """Récupère les messages d'un canal et les retourne sous forme de DataFrame."""
    messages = []
    if "mudae" in channel.name.lower() or "log" in channel.name.lower():
        return pd.DataFrame()
    
    log_message = f"[DÉBUT] Récupération de #{channel.name}"
    if after_date:
        log_message += f" (après le {after_date.strftime('%Y-%m-%d %H:%M')})"
    logging.info(log_message)
    
    start_time = time.time()
    count = 0
    try:
        async for message in channel.history(limit=None, after=after_date):
            if not message.author.bot:
                messages.append({
                    "timestamp": message.created_at,
                    "author_id": message.author.id,
                    "author_name": str(message.author),
                    "channel_id": channel.id,
                    # --- LIGNE MODIFIÉE ---
                    "character_count": len(message.content.replace(' ', ''))
                })
                count += 1
        
        end_time = time.time()
        logging.info(f"[FIN] Récupération de #{channel.name} terminée. {count} messages récupérés en {end_time - start_time:.2f} secondes.")
        
        return pd.DataFrame(messages)
    except Exception as e:
        logging.error(f"Erreur dans #{channel.name}: {e}")
        return pd.DataFrame()

async def fetch_messages_with_cache(guild, cache_filename):
    """
    Récupère les messages des canaux en utilisant un cache pour plus d'efficacité.
    """
    global user_id_to_name_map
    df_cache = pd.DataFrame()
    latest_timestamps = {}
    
    if os.path.exists(cache_filename):
        df_cache = pd.read_parquet(cache_filename)
        df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"])
        if not df_cache.empty:
            df_known_users = df_cache[df_cache["author_name"] != "Deleted User#0000"].drop_duplicates(subset=["author_id"], keep="last")
            user_id_to_name_map = pd.Series(df_known_users.author_name.values, index=df_known_users.author_id).to_dict()
            latest_timestamps = df_cache.loc[df_cache.groupby("channel_id")["timestamp"].idxmax()].set_index("channel_id")["timestamp"].to_dict()

    tasks = [
        asyncio.create_task(
            fetch_channel_messages_as_df(c, after_date=latest_timestamps.get(c.id))
        )
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    new_dfs = [res for res in results if isinstance(res, pd.DataFrame) and not res.empty]
    df_new = pd.concat(new_dfs, ignore_index=True) if new_dfs else pd.DataFrame()

    if not df_new.empty:
        df_new_known = df_new[df_new["author_name"] != "Deleted User#0000"].drop_duplicates(subset=["author_id"], keep="last")
        user_id_to_name_map.update(pd.Series(df_new_known.author_name.values, index=df_new_known.author_id).to_dict())

    final_df = pd.concat([df_cache, df_new], ignore_index=True).drop_duplicates(subset=['timestamp', 'author_id'])
    final_df = final_df[~final_df["author_id"].isin(IDS_TO_EXCLUDE)]
    final_df.to_parquet(cache_filename)

    final_df["author_name"] = final_df["author_id"].map(user_id_to_name_map)
    unknown_mask = final_df["author_name"].isnull()
    final_df.loc[unknown_mask, "author_name"] = "ID: " + final_df.loc[unknown_mask, "author_id"].astype(str)

    if ID_MERGE_MAP:
        for old_id, new_name in ID_MERGE_MAP.items():
            final_df.loc[final_df["author_id"] == int(old_id), "author_name"] = new_name

    if NAME_MERGE_MAP:
        for old_name, new_name in NAME_MERGE_MAP.items():
            final_df.loc[final_df["author_name"] == old_name, "author_name"] = new_name

    return final_df.drop(columns=["channel_id"], errors="ignore")


async def run_bot(token, cache_filename, colors_filename):
    """
    Fonction principale pour exécuter le bot et lancer le processus.
    """
    global dashboard_df, user_id_to_name_map_global, role_colors_map_global, current_member_ids_global
    dashboard_df = pd.DataFrame()
    user_id_to_name_map_global = {}
    role_colors_map_global = {}
    current_member_ids_global = []

    on_ready_event = asyncio.Event()

    @client.event
    async def on_ready():
        logging.info(f"{client.user} s'est connecté à Discord !")
        if not client.guilds:
            logging.error("Le bot n'est pas sur un serveur. Fermeture...")
            await client.close()
            on_ready_event.set()
            return
        
        guild = client.guilds[0]
        try:
            logging.info("Récupération de la liste des membres actuels...")
            await guild.chunk()
            current_members = [member.id for member in guild.members if not member.bot]
            
            await fetch_and_save_role_colors(guild, colors_filename)
            main_df = await fetch_messages_with_cache(guild, cache_filename)
            logging.info("La collecte de données est terminée.")
            
            global dashboard_df, user_id_to_name_map_global, role_colors_map_global, current_member_ids_global
            dashboard_df = main_df
            user_id_to_name_map_global = user_id_to_name_map
            role_colors_map_global = role_colors_map
            current_member_ids_global = current_members

        except Exception as e:
            logging.error(f"Une erreur est survenue pendant la collecte : {e}")
        finally:
            await client.close()
            on_ready_event.set()

    asyncio.create_task(client.start(token))
    await on_ready_event.wait()
    
    return dashboard_df, user_id_to_name_map_global, role_colors_map_global, current_member_ids_global

