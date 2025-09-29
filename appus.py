import logging
import os
import asyncio
import pandas as pd
import json

from dotenv import load_dotenv

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

# --- LIGNE CORRIGÉE ---
DATA_DIR = "dataus" 
# --- FIN DE LA CORRECTION ---

CACHE_FILENAME = os.path.join(DATA_DIR, "discord_messages_cache.parquet")
ROLE_COLORS_FILENAME = os.path.join(DATA_DIR, "role_colors.json")
STATS_FILENAME = os.path.join(DATA_DIR, "discord_server_stats.csv")

# Crée le dossier data s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

# --- LOGIQUE DE PRÉPARATION DES DONNÉES (CENTRALISÉE) ---
NAME_REPLACE_MAP = {
    "nathsus": "Nathan", "ersees": "Yanis", "sabrito_": "Sabri", "darkysama": "Clément",
    "raijinsen": "Marius", "dinoz_": "Nicolas", "solafleur": "Émilie", "_noko.": "Nadjy",
    "iskander16": "Iskander", "massieh": "Massieh", "simsimz": "Simon", "mirapv": "Nina",
    "virkos": "Edison", "busto_": "Matiya", "maelhinio": "Maël", "sheimi.": "Valou",
    "tisema": "Matise", "jooojx": "Jooj", "lupoticha": "Lu Man", "lilisica": "Pauline",
    "niou": "Lucas", "uxtickets": "David", ".redhot_": "Léo", "ascended_sao": "Sao My",
    "zeykoo": "Ali", "anita0732": "Anita", "ussererzada": "Emy", "catnelle": "Safia",
    "axel005521": "Axel", "caeliumz": "Mathis", "menacing_cake": "Menacing Cake",
    "aniistiti": "Anissa", "cynthia_von_bottoks": "Cynthia", "akam.e": "Alice",
    "nightx9": "Hugo", "timiane": "Mélanie", "mademoiselle.layla": "Kenza",
    "donpatchi": "Donpatchi", "entap.": "Kelly", "xpulpe": "Sophie", "mailyan": "Myan",
    "helskin": "Helskin", "sodouille": "Gaylord", "assiox": "Assia", "tuturino_": "Arthur",
    "narabiis": "Gaëlle", "g_remy": "Gérémy", "slinlpb": "Nils", "batman2715": "Batman",
    "stef_35": "Stef", "otchi": "Otchi", "tenesquik": "Ténébrisse", "lenatje": "Léna",
    "tovounet": "Tov", "yassine_ic": "Yassine", "adriencumulo": "Adrien",
    "irinacitron": "Irina", "may.86.b": "May", "edward511": "Edward",
    "chehste": "Este", "xujing": "Sokat", "hujeau": "Hujeau", "antoin.e": "Antoine",
    "mymyyyyyy": "Mylanne", "zumos69": "Zumos", "atzporos": "Jason", "oxynemesis": "Oxy Nemesis",
    "grasdenunu": "Gras de Nunu", "scotted": "Scotted", "waykun": "Waykun", "atillux": "Atilla",
    "kirg0n": "Kirgon", "tacina": "Tasnime", "legrosk": "Legrosk", "aimen9880": "Aimen",
    "itachill_": "Itachi", "mezouze.": "Mezouze", "seraksan": "Serak", "tndstrs4real": "Tetsu",
    "stanis1018": "Stanis", "jubjube": "Yliann", "kyky2005": "Kyllian", "diploplo": "Diplo",
    "minasedai": "Mina", "debonairfab": "Debonair Fab", "doro.otea": "Clara", "lxst_nayra": "Nayra",
    ".emna_": "Enm", "144kynn_": "144kynn_", "simo3329": "Simon3329", "woldek": "Woldek",
    "pikacao": "Pikacao", "akuuuuuuuuu": "Aku", "zyoulou": "Zyoulou", ".danylo": "Danylo",
    "attits": "Atti", ".muhu": "Camille", "wass9005": "Wass", "__boba___": "Boba",
    "kingu_avocado": "Bilal", "kyubyyy": "Kyuby", "remli_8": "Remi", "hanabiiii": "Tatiana"
}

SMURF_ACCOUNTS = [
    "daka1845", ".uwu2", "nqtqn", "nathsmurf", "lugrocha", "kdamamadousakho"
]
# --- FIN DE LA LOGIQUE DE PRÉPARATION ---

async def main():
    """
    Fonction principale asynchrone pour exécuter le bot et le tableau de bord.
    """
    logging.info("Démarrage du processus de collecte de données Discord...")
    
    try:
        df, user_map, colors_map, current_members = await run_bot(
            DISCORD_TOKEN, CACHE_FILENAME, ROLE_COLORS_FILENAME
        )
    except Exception as e:
        logging.error(f"Une erreur critique est survenue lors de l'exécution du bot : {e}")
        df = pd.DataFrame() # Assure que df est défini même en cas d'erreur

    if df.empty:
        logging.warning("Aucune donnée n'a été récupérée. Tentative de chargement depuis le cache local...")
        if os.path.exists(CACHE_FILENAME) and os.path.exists(ROLE_COLORS_FILENAME):
            df = pd.read_parquet(CACHE_FILENAME)
            with open(ROLE_COLORS_FILENAME, 'r') as f:
                colors_map = json.load(f)
            user_map = {} 
            current_members = [] 
        else:
            logging.error("Aucune donnée à afficher et cache inexistant. Le programme se termine.")
            return

    # --- APPLICATION DU NETTOYAGE DES DONNÉES ---
    df = df[~df['author_name'].isin(SMURF_ACCOUNTS)]
    user_total_counts = df['author_name'].value_counts()
    active_users = user_total_counts[user_total_counts >= 100].index
    df = df[df['author_name'].isin(active_users)]
    
    if 'character_count' in df.columns:
        df['character_count'] = df['character_count'].fillna(0)
    else:
        df['character_count'] = 0
        
    df['original_author_name'] = df['author_name']
    df['author_name'] = df['author_name'].replace(NAME_REPLACE_MAP)
    # --- FIN DU NETTOYAGE ---

    if not df.empty:
        logging.info("La collecte de données est terminée. Lancement du tableau de bord.")
        
        process_and_save_stats(df, STATS_FILENAME)
        
        app = create_app(df, user_map, colors_map, current_members)
        logging.info("Lancement du serveur web Dash sur http://localhost:8050/")
        app.run(host="0.0.0.0", port=8050, debug=True)
    else:
        logging.warning("Aucune donnée à afficher après filtrage. Le programme se termine.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logging.error("Le DISCORD_TOKEN n'est pas défini ! Assurez-vous d'avoir un fichier .env.")
    else:
        asyncio.run(main())

