# corus/botus.py

import asyncio
import json
import logging
import os
import time
from datetime import datetime
import discord
import pandas as pd

# ==============================================================================
#  CONFIGURATION
# ==============================================================================
IDS_TO_EXCLUDE = [456226577798135808]
# ==============================================================================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
user_id_to_name_map = {}
role_colors_map = {}
member_data_map = {}  # Pour stocker les rôles et autres infos


async def fetch_server_data(guild, colors_filename):
    """Récupère et sauvegarde les couleurs de rôle et les données des membres."""
    global role_colors_map, member_data_map

    logging.info(f"Récupération des données du serveur '{guild.name}'...")
    logging.info(
        "Cette opération (guild.chunk) peut prendre plusieurs minutes sur un gros serveur..."
    )

    start_chunk = time.time()
    await guild.chunk(cache=True)  # Demande à Discord d'envoyer tous les membres
    end_chunk = time.time()

    logging.info(
        f"Données des {len(guild.members)} membres récupérées en {end_chunk - start_chunk:.2f} secondes."
    )

    role_colors_map = {}
    member_data_map = {}

    for member in guild.members:
        if member.bot:
            continue

        member_id_str = str(member.id)

        # 1. Sauvegarder la couleur
        if str(member.color) != "#000000":
            role_colors_map[member_id_str] = str(member.color)

        # 2. Sauvegarder les données du membre (rôles)
        member_data_map[member_id_str] = {
            "name": str(member),
            "roles": [role.name for role in member.roles if role.name != "@everyone"],
        }

    with open(colors_filename, "w") as f:
        json.dump(role_colors_map, f, indent=4)
    logging.info(f"Couleurs de rôle sauvegardées dans {colors_filename}.")

    # Retourne les IDs des membres présents pour le filtrage
    return set(int(mid) for mid in member_data_map.keys())


async def fetch_channel_messages_as_df(channel, after_date=None):
    """Récupère les messages d'un canal et les retourne sous forme de DataFrame."""
    messages = []
    if "mudae" in channel.name.lower() or "log" in channel.name.lower():
        return pd.DataFrame(), 0  # Retourne un tuple (DataFrame, count)

    log_message = f"[INFO] Vérification de #{channel.name}"
    if after_date:
        log_message += f" (après le {after_date.strftime('%Y-%m-%d %H:%M')})"
    # Ne pas logger le début pour l'instant

    start_time = time.time()
    count = 0
    try:
        async for message in channel.history(limit=None, after=after_date):
            if not message.author.bot:
                # Compter les caractères sans les espaces
                char_count_no_spaces = len(message.content.replace(" ", ""))

                messages.append(
                    {
                        "timestamp": message.created_at,
                        "author_id": message.author.id,
                        "author_name": str(message.author),
                        "channel_id": channel.id,
                        "character_count": char_count_no_spaces,  # Nouvelle donnée
                    }
                )
                count += 1

        end_time = time.time()

        # --- CORRECTION ---
        # N'afficher le log que s'il y a eu de nouveaux messages
        if count > 0:
            logging.info(
                f"[MISE À JOUR] #{channel.name}: {count} nouveaux messages récupérés en {end_time - start_time:.2f} secondes."
            )

        return pd.DataFrame(messages), count  # Retourne le count
    except discord.errors.Forbidden:
        # logging.warning(f"[ACCÈS REFUSÉ] Impossible de lire l'historique de #{channel.name}.")
        return pd.DataFrame(), 0
    except Exception as e:
        logging.error(f"Erreur dans #{channel.name}: {e}")
        return pd.DataFrame(), 0


async def fetch_messages_with_cache(guild, cache_filename):
    """
    Récupère les messages des canaux en utilisant un cache pour plus d'efficacité.
    """
    global user_id_to_name_map
    df_cache = pd.DataFrame()
    latest_timestamps = {}

    if os.path.exists(cache_filename):
        logging.info(f"Chargement du cache depuis {cache_filename}...")
        df_cache = pd.read_parquet(cache_filename)
        df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"])
        if not df_cache.empty:
            df_known_users = df_cache[
                df_cache["author_name"] != "Deleted User#0000"
            ].drop_duplicates(subset=["author_id"], keep="last")
            user_id_to_name_map = pd.Series(
                df_known_users.author_name.values, index=df_known_users.author_id
            ).to_dict()
            latest_timestamps = (
                df_cache.loc[df_cache.groupby("channel_id")["timestamp"].idxmax()]
                .set_index("channel_id")["timestamp"]
                .to_dict()
            )
    else:
        logging.info("Aucun cache trouvé. Une analyse complète est nécessaire.")

    tasks = [
        asyncio.create_task(
            fetch_channel_messages_as_df(c, after_date=latest_timestamps.get(c.id))
        )
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_dfs = []
    total_new_messages = 0
    for res in results:
        if isinstance(res, tuple):
            df_res, count_res = res
            if not df_res.empty:
                new_dfs.append(df_res)
            total_new_messages += count_res
        elif isinstance(res, Exception):
            logging.error(f"Une tâche de fetch a échoué : {res}")

    if not new_dfs:
        logging.info("Aucun nouveau message à ajouter au cache.")
        if df_cache.empty:
            logging.error("Le cache est vide et aucun nouveau message n'a été trouvé.")
            return pd.DataFrame()
        return df_cache.drop(columns=["channel_id"], errors="ignore")

    logging.info(
        f"Total de {total_new_messages} nouveaux messages trouvés sur l'ensemble des salons."
    )
    df_new = pd.concat(new_dfs, ignore_index=True) if new_dfs else pd.DataFrame()

    if not df_new.empty:
        df_new_known = df_new[
            df_new["author_name"] != "Deleted User#0000"
        ].drop_duplicates(subset=["author_id"], keep="last")
        user_id_to_name_map.update(
            pd.Series(
                df_new_known.author_name.values, index=df_new_known.author_id
            ).to_dict()
        )

    final_df = pd.concat([df_cache, df_new], ignore_index=True)

    if "character_count" not in final_df.columns:
        final_df["character_count"] = 0
    else:
        final_df["character_count"] = final_df["character_count"].fillna(0).astype(int)

    final_df = final_df[~final_df["author_id"].isin(IDS_TO_EXCLUDE)]

    logging.info(f"Sauvegarde du cache mis à jour dans {cache_filename}...")
    final_df.to_parquet(cache_filename, index=False)
    logging.info("Sauvegarde terminée.")

    final_df["author_name"] = final_df["author_id"].map(user_id_to_name_map)
    unknown_mask = final_df["author_name"].isnull()
    final_df.loc[unknown_mask, "author_name"] = "ID: " + final_df.loc[
        unknown_mask, "author_id"
    ].astype(str)

    return final_df.drop(columns=["channel_id"], errors="ignore")


async def run_bot(token, cache_filename, colors_filename):
    """
    Fonction principale pour exécuter le bot et lancer le processus.
    """
    global dashboard_df, role_colors_map_global, member_data_map_global
    dashboard_df = pd.DataFrame()
    role_colors_map_global = {}
    member_data_map_global = {}

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
            global role_colors_map_global, member_data_map_global

            # 1. Récupérer les rôles, couleurs et la liste des membres actuels
            await fetch_server_data(guild, colors_filename)
            role_colors_map_global = role_colors_map
            member_data_map_global = member_data_map

            # 2. Récupérer les messages
            main_df = await fetch_messages_with_cache(guild, cache_filename)
            logging.info("La collecte de données est terminée.")

            global dashboard_df
            dashboard_df = main_df

        except Exception as e:
            logging.error(
                f"Une erreur est survenue pendant la collecte : {e}", exc_info=True
            )
        finally:
            await client.close()
            on_ready_event.set()

    asyncio.create_task(client.start(token))
    await on_ready_event.wait()

    return dashboard_df, role_colors_map_global, member_data_map_global
    