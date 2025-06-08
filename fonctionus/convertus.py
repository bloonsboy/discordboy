import json
import os
import pandas as pd
from tqdm import tqdm
from datetime import datetime

ERROR_USER_VALUES = ["Direct Message with Unknown Participant", "None", "Unknown channel"]

def get_conversion_name_dict(index_file_path):
    """Charge index.json et crée un dictionnaire de mappage ID -> Nom."""
    try:
        with open(index_file_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        return {
            key: (value.replace("Direct Message with ", "").replace("#0", "")
                  if value not in ERROR_USER_VALUES else key)
            for key, value in index_data.items()
        }
    except Exception as e:
        print(f"Erreur lors de la lecture de '{index_file_path}': {e}")
        return {}

def get_channel_type_from_json(channel_json_path):
    """Récupère le type de canal depuis channel.json."""
    try:
        with open(channel_json_path, 'r', encoding='utf-8') as f:
            return json.load(f).get("type", "Unknown")
    except FileNotFoundError:
        return "Unknown"
    except Exception as e:
        print(f"Erreur lecture '{channel_json_path}': {e}")
        return "Unknown"

def load_messages_from_json_file(messages_json_path):
    """Charge les messages depuis un fichier messages.json."""
    try:
        with open(messages_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lecture '{messages_json_path}': {e}")
        return []

def process_individual_messages_list(messages_data, name, type):
    """Traite une liste de messages pour une conversation."""
    rows = []
    for message in messages_data:
        try:
            ts_str = message.get("Timestamp")
            date_obj = next((datetime.strptime(ts_str, fmt) for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S") if ts_str), None)
            if not date_obj:
                date_obj = datetime.now()
            rows.append({
                "ID": message.get("ID", "No ID"), "Name": name, "Type": type,
                "Timestamp": date_obj, "Contents": message.get("Contents", ""),
                "Attachments": message.get("Attachments", [])
            })
        except Exception as e:
            print(f"Erreur traitement message dans '{name}': {e}")
    return rows

def create_messages_dataframe(base_path, names_dict):
    """Crée un DataFrame Pandas à partir des fichiers messages.json."""
    all_rows = []
    msg_root = os.path.join(base_path, "messages")
    if not os.path.exists(msg_root):
        print(f"Erreur: Dossier messages non trouvé à '{msg_root}'")
        return pd.DataFrame()
    
    folders = [d for d in os.listdir(msg_root) if d.startswith('c') and os.path.isdir(os.path.join(msg_root, d))]
    for folder in tqdm(folders, desc="Traitement messages", unit="dossier"):
        channel_id = folder[1:]
        name = names_dict.get(channel_id, f"Unknown (ID: {channel_id})")
        
        folder_path = os.path.join(msg_root, folder)
        channel_type = get_channel_type_from_json(os.path.join(folder_path, "channel.json"))
        messages_data = load_messages_from_json_file(os.path.join(folder_path, "messages.json"))
        
        all_rows.extend(process_individual_messages_list(messages_data, name, channel_type))
    return pd.DataFrame.from_records(all_rows)

def remove_mudae_bot_messages(df):
    """Supprime les messages du bot Mudae."""
    if df.empty: return df
    condition = df['Name'].str.contains('mudae|huh', na=False) & df['Contents'].astype(str).str.startswith('$', na=False)
    return df[~condition]

def clean_and_normalize_names_in_dataframe(df):
    """Nettoie et normalise la colonne 'Name'."""
    if df.empty: return df
    remplacements = {
        '788858111712690187': 'Alex', '392046922635935755': 'Ali', 'baka6893': 'Ali', 'zeykoo': 'Ali',
        'akam.e': 'Alice', 'anita0732': 'Anita', 'axel005521': 'Axel', '.kleman': 'Clément VLP',
        'darkysama': 'Clément VRG', 'cynthia_von_bottoks': 'Cynthia', 'solafleur': 'Emi', 'mynilly': 'Emy',
        'ussererzada': 'Emy', 'iskander16': 'Isk', 'jooojx': 'Jooj', 'grospoutousan': 'Leo ECE',
        'iwantdog': 'Leo Discord', 'moustillon': 'Lotarie', '482901836580257811': 'Lu Man',
        'lupoticha': 'Lu Man', 'raijinsen': 'Marius', 'busto_': 'Matiya', 'panipowbleme': 'Matteo',
        '_noko.': 'Nadjy', 'dinoz_': 'Nicolas', 'mirapv': 'Nina', 'shinelikesirius': 'Noah',
        'biiedronka': 'Pauline', 'sabrito_': 'Sabri', 'catnelle': 'Safia', 'ascended_sao': 'Sao My',
        'simsimz': 'Simon', 'hanabiiii': 'Tatiana', '855901206161129482': 'Toshi',
        'sheimi.': 'Valou', '562692324719853609': 'Violet', 'ersees': 'Yanis'
    }
    df['Name'] = df['Name'].replace(remplacements)
    
    cond = df['Type'] == 'GUILD_TEXT'
    if cond.any():
        df.loc[cond, 'Name'] = df.loc[cond, 'Name'].astype(str).str.replace('-', ' ', regex=False)
        extracts = df.loc[cond, 'Name'].str.extract(r'^\s*(.*?)\s+in\s+(.*?)\s*$', flags=re.IGNORECASE)
        valid_idx = extracts.dropna().index
        if not valid_idx.empty:
            df.loc[valid_idx, 'Name'] = extracts.loc[valid_idx, 1].str.strip() + ' | ' + extracts.loc[valid_idx, 0].str.strip()
    return df

def process_discord_package_to_csv(base_path, output_csv):
    """Orchestre le traitement du package Discord et sauvegarde en CSV."""
    print(f"Début traitement depuis: {base_path}")
    index_path = os.path.join(base_path, "messages", "index.json")
    names = get_conversion_name_dict(index_path)
    if not names: return False
    
    df = create_messages_dataframe(base_path, names)
    if df.empty: return False
    
    df = remove_mudae_bot_messages(df)
    # Note: la fonction clean_and_normalize_names a été corrigée pour importer 're'
    # import re # <-- Ajoutez cette ligne en haut de votre fichier convertus.py
    # df = clean_and_normalize_names_in_dataframe(df)

    try:
        df['Attachments'] = df['Attachments'].apply(json.dumps)
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"DataFrame sauvegardé dans '{output_csv}' ({len(df)} messages).")
        return True
    except Exception as e:
        print(f"Erreur sauvegarde CSV: {e}")
        return False
