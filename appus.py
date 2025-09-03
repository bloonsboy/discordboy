# appus.py

import logging
import os
import asyncio

from dotenv import load_dotenv

# Mise à jour des imports
from corus.botus import run_bot
from dashboardus.appus import create_app
from corus.processus import process_and_save_stats

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Chargement des variables d'environnement
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATA_DIR = "dataus"
CACHE_FILENAME = os.path.join(DATA_DIR, "discord_messages_cache.parquet")
ROLE_COLORS_FILENAME = os.path.join(DATA_DIR, "role_colors.json")
STATS_FILENAME = os.path.join(DATA_DIR, "discord_server_stats.csv")

# Crée le dossier data s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

async def main():
    """
    Fonction principale asynchrone pour exécuter le bot et le tableau de bord.
    """
    logging.info("Démarrage du processus de collecte de données Discord...")
    
    # Exécute le bot Discord pour collecter les données
    dashboard_df, user_id_to_name_map, role_colors_map = await run_bot(
        DISCORD_TOKEN, CACHE_FILENAME, ROLE_COLORS_FILENAME
    )

    if not dashboard_df.empty:
        logging.info("La collecte de données est terminée. Lancement du tableau de bord.")
        
        # Traite les données et sauvegarde les statistiques
        process_and_save_stats(dashboard_df, STATS_FILENAME)
        
        # Crée et exécute le tableau de bord Dash
        app = create_app(
            dashboard_df, user_id_to_name_map, role_colors_map
        )
        logging.info("Lancement du serveur web Dash sur http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=False)
    else:
        logging.info("Aucune donnée à afficher. Le programme se termine.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logging.error("Le DISCORD_TOKEN n'est pas défini ! Assurez-vous d'avoir un fichier .env.")
    else:
        # Exécute la boucle d'événements asynchrone
        asyncio.run(main())