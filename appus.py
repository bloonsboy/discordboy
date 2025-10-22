# appus.py (à la racine)

import logging
import os
import asyncio
import pandas as pd
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
DATA_DIR = "dataus"  # Le dossier est à la racine
CACHE_FILENAME = os.path.join(DATA_DIR, "discord_messages_cache.parquet")
ROLE_COLORS_FILENAME = os.path.join(DATA_DIR, "role_colors.json")
STATS_FILENAME = os.path.join(DATA_DIR, "discord_server_stats.csv")

# Crée le dossier data s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

# --- DÉFINITION DES FILTRES ET PSEUDONYMES ---
# Placer la configuration ici pour la centraliser

# 1. Liste des comptes à exclure (smurfs, etc.)
EXCLUDE_LIST = [
    "daka1845",
    ".uwu2",
    "nqtqn",
    "nathsmurf",
    "lugrocha",
    "kdamamadousakho",
]

# 2. Seuil minimum de messages pour être affiché
MIN_MESSAGE_COUNT = 100

# 3. Dictionnaire de remplacement des noms
NAME_REPLACE_MAP = {
    ".danylo": "Danylo",
    ".emna_": "Enm",
    ".muhu": "Camille",
    ".redhot_": "Léo",
    "144kynn_": "144kynn_",
    "__boba___": "Boba",
    "_noko.": "Nadjy",
    "adriencumulo": "Adrien",
    "aimen9880": "Aimen",
    "akam.e": "Alice",
    "akuuuuuuuuu": "Aku",
    "aniistiti": "Anissa",
    "anita0732": "Anita",
    "antoin.e": "Antoine",
    "ascended_sao": "Sao My",
    "assiox": "Assia",
    "atillux": "Atilla",
    "attits": "Atti",
    "atzporos": "Jason",
    "axel005521": "Axel",
    "batman2715": "Batman",
    "busto_": "Matiya",
    "caeliumz": "Mathis",
    "catnelle": "Safia",
    "chehste": "Este",
    "cynthia_von_bottoks": "Cynthia",
    "darkysama": "Clément",
    "debonairfab": "Debonair Fab",
    "dinoz_": "Nicolas",
    "diploplo": "Diplo",
    "donpatchi": "Donpatchi",
    "doro.otea": "Clara",
    "edward511": "Edward",
    "entap.": "Kelly",
    "ersees": "Yanis",
    "g_remy": "Gérémy",
    "grasdenunu": "Gras de Nunu",
    "hanabiiii": "Tatiana",
    "helskin": "Helskin",
    "hujeau": "Hujeau",
    "irinacitron": "Irina",
    "iskander16": "Iskander",
    "itachill_": "Itachi",
    "jooojx": "Jooj",
    "jubjube": "Yliann",
    "kingu_avocado": "Bilal",
    "kirg0n": "Kirgon",
    "kuruuuka": "Eva",
    "kyky2005": "Kyllian",
    "kyubyyy": "Kyuby",
    "legrosk": "Legrosk",
    "lenatje": "Léna",
    "lilisica": "Pauline",
    "lupoticha": "Lu Man",
    "lxst_nayra": "Nayra",
    "mademoiselle.layla": "Kenza",
    "maelhinio": "Maël",
    "mailyan": "Myan",
    "massieh": "Massieh",
    "may.86.b": "May",
    "menacing_cake": "Menacing Cake",
    "mezouze.": "Mezouze",
    "minasedai": "Mina",
    "mirapv": "Nina",
    "mymyyyyyy": "Mylanne",
    "narabiis": "Gaëlle",
    "nathsus": "Nathan",
    "nightx9": "Hugo",
    "niou": "Lucas",
    "otchi": "Otchi",
    "oxynemesis": "Oxy Nemesis",
    "pikacao": "Pikacao",
    "raijinsen": "Marius",
    "remli_8": "Remi",
    "sabrito_": "Sabri",
    "scotted": "Scotted",
    "seraksan": "Serak",
    "sheimi.": "Valou",
    "simo3329": "Simon3329",
    "simsimz": "Simon",
    "slinlpb": "Nils",
    "sodouille": "Gaylord",
    "solafleur": "Émilie",
    "stanis1018": "Stanis",
    "stef_35": "Stef",
    "tacina": "Tasnime",
    "tenesquik": "Ténébrisse",
    "timiane": "Mélanie",
    "tisema": "Matise",
    "tndstrs4real": "Tetsu",
    "tovounet": "Tov",
    "tuturino_": "Arthur",
    "ussererzada": "Emy",
    "uxtickets": "David",
    "virkos": "Edison",
    "wass9005": "Wass",
    "waykun": "Waykun",
    "woldek": "Woldek",
    "xpulpe": "Sophie",
    "xujing": "Sokat",
    "yassine_ic": "Yassine",
    "zeykoo": "Ali",
    "zumos69": "Zumos",
    "zyoulou": "Zyoulou",
}
# --- FIN DE LA CONFIGURATION ---


def prepare_dataframe(df, member_data):
    """
    Applique tous les filtres et transformations au DataFrame principal.
    """
    logging.info("Préparation du DataFrame pour le tableau de bord...")

    # 1. Sauvegarder le nom original avant de le remplacer
    df["original_author_name"] = df["author_name"]

    # 2. Remplacer les pseudos par les prénoms
    df["author_name"] = (
        df["author_name"].map(NAME_REPLACE_MAP).fillna(df["author_name"])
    )

    # 3. Filtrer les comptes exclus (smurfs)
    # Nous filtrons sur les deux noms (original et remplacé) par sécurité
    df = df[~df["original_author_name"].isin(EXCLUDE_LIST)]
    df = df[~df["author_name"].isin(EXCLUDE_LIST)]

    # 4. Filtrer les utilisateurs inactifs (moins de 100 messages au total)
    total_counts = df["author_name"].value_counts()
    active_users = total_counts[total_counts >= MIN_MESSAGE_COUNT].index
    df = df[df["author_name"].isin(active_users)]

    # 5. Remplir les 'character_count' manquants (au cas où)
    df["character_count"] = df["character_count"].fillna(0).astype(int)

    logging.info(
        f"Préparation terminée. {len(df)} messages et {len(active_users)} utilisateurs actifs retenus."
    )
    return df, member_data


async def main():
    """
    Fonction principale asynchrone pour exécuter le bot et le tableau de bord.
    """
    if not DISCORD_TOKEN:
        logging.error(
            "Le DISCORD_TOKEN n'est pas défini ! Assurez-vous d'avoir un fichier .env."
        )
        return

    logging.info("Démarrage du processus de collecte de données Discord...")

    # Exécute le bot Discord pour collecter les données
    # 'member_data' contient maintenant les infos sur les membres (dont les rôles)
    dashboard_df, role_colors_map, member_data = await run_bot(
        DISCORD_TOKEN, CACHE_FILENAME, ROLE_COLORS_FILENAME
    )

    if not dashboard_df.empty:
        logging.info("La collecte de données est terminée. Préparation des données...")

        # Appliquer les filtres et transformations
        processed_df, processed_member_data = prepare_dataframe(
            dashboard_df, member_data
        )

        if processed_df.empty:
            logging.warning(
                "Aucune donnée restante après filtrage. Le tableau de bord ne peut pas être lancé."
            )
            return

        # Traite les données et sauvegarde les statistiques (optionnel, mais gardé)
        process_and_save_stats(processed_df, STATS_FILENAME)

        # Crée et exécute le tableau de bord Dash
        app = create_app(processed_df, role_colors_map, processed_member_data)
        logging.info("Lancement du serveur web Dash sur http://localhost:8050/")
        app.run(
            host="0.0.0.0", port=8050, debug=True
        )  # debug=True est utile pour le développement
    else:
        logging.warning("Aucune donnée n'a été collectée. Le programme se termine.")


if __name__ == "__main__":
    asyncio.run(main())
