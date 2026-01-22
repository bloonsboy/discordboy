import os
import re
import pandas as pd
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.resolve()))
try:
    from dataus.constant import DATA_DIR
except ImportError:
    raise ImportError("Impossible d'importer dataus.constant. Vérifie la structure du projet et la présence d'un __init__.py dans dataus/.")

import asyncio
import discord
import pandas as pd
from datetime import datetime, timezone
from corus.botus import create_message_data


def extract_wordle_results_from_messages(df):
    # Regex pour détecter les messages Wordle (ex : Wordle 220 4/6)
    wordle_pattern = re.compile(r"Wordle (\d{1,4}) ([X1-6])/6", re.IGNORECASE)
    results = []
    for _, row in df.iterrows():
        match = wordle_pattern.search(str(row.get("content", "")))
        if match:
            wordle_number = int(match.group(1))
            score = match.group(2)
            results.append(
                {
                    "author_id": row["author_id"],
                    "created_at": row["created_at"],
                    "wordle_number": wordle_number,
                    "score": score,
                }
            )
    return pd.DataFrame(results)


def main(server_id):
    wordle_parquet_path = os.path.join(DATA_DIR, str(server_id), "wordle.parquet")
    if os.path.exists(wordle_parquet_path):
        df = pd.read_parquet(wordle_parquet_path)
    else:
        # Scraping Discord du channel Wordle
        print("Aucun fichier wordle.parquet trouvé, lancement du scraping du channel Wordle...")
        async def scrape_wordle_channel():
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)
            channel_id = 443137696446021652
            min_date = datetime(2025, 7, 24, tzinfo=timezone.utc)
            messages_data = []
            @client.event
            async def on_ready():
                guild = discord.utils.get(client.guilds, id=int(server_id))
                if guild is None:
                    print(f"Serveur {server_id} introuvable.")
                    await client.close()
                    return
                channel = discord.utils.get(guild.text_channels, id=channel_id)
                if channel is None:
                    print(f"Channel Wordle {channel_id} introuvable.")
                    await client.close()
                    return
                async for message in channel.history(limit=None, after=min_date, oldest_first=True):
                    if message.author.bot:
                        continue
                    msg_data = await create_message_data(message, server_id)
                    messages_data.append(msg_data)
                df_scraped = pd.DataFrame(messages_data)
                df_scraped.to_parquet(wordle_parquet_path, index=False)
                print(f"Fichier wordle.parquet créé avec {len(df_scraped)} messages du Wordle.")
                await client.close()
            # Charger le token Discord
            import dotenv
            import os
            dotenv.load_dotenv()
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                print("DISCORD_TOKEN non trouvé dans .env")
                return None
            await client.start(token)
            return pd.read_parquet(wordle_parquet_path)
        df = asyncio.run(scrape_wordle_channel())
        if df is None:
            print("Scraping Wordle annulé.")
            return
    # Filtrer sur le channel et la date
    # Vérification de la présence de la colonne 'channel_id'
    if "channel_id" not in df.columns:
        print("Erreur : le fichier messages.parquet ne contient pas la colonne 'channel_id'.")
        print("Le fichier est peut-être vide, corrompu, ou le scraping n'a pas fonctionné.")
        return
    channel_id = 443137696446021652
    min_date = pd.Timestamp("2025-07-24", tz="UTC")
    df = df[
        (df["channel_id"] == channel_id)
        & (pd.to_datetime(df["created_at"], unit="s", utc=True) >= min_date)
    ]
    wordle_df = extract_wordle_results_from_messages(df)
    if wordle_df.empty:
        print("Aucun résultat Wordle trouvé.")
        return
    # Sauvegarde des messages bruts Wordle
    wordle_msgs = df[
        df["content"].str.contains(
            r"Wordle \\d{1,4} [X1-6]/6", case=False, na=False, regex=True
        )
    ]
    wordle_msgs_path = os.path.join(DATA_DIR, str(server_id), "wordle_messages.parquet")
    wordle_msgs.to_parquet(wordle_msgs_path, index=False)
    print(f"Messages Wordle bruts sauvegardés dans {wordle_msgs_path}")
    # Statistiques simples
    print(f"Nombre de résultats Wordle trouvés : {len(wordle_df)}")
    print(wordle_df.groupby("score").size().sort_index())
    # Sauvegarde CSV
    out_path = os.path.join(DATA_DIR, str(server_id), "wordle_stats.csv")
    wordle_df.to_csv(out_path, index=False)
    print(f"Statistiques sauvegardées dans {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyse les scores Wordle sur le serveur Discord."
    )
    parser.add_argument(
        "--server-id", type=str, required=True, help="ID du serveur Discord"
    )
    args = parser.parse_args()
    main(args.server_id)
