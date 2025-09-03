# core/data_processing.py

import pandas as pd
import logging

def process_and_save_stats(df, filename):
    """
    Traite le DataFrame pour générer des statistiques annuelles et les sauvegarde en CSV.
    """
    if df.empty:
        logging.info("Le DataFrame est vide, pas de statistiques à générer.")
        return pd.DataFrame()
        
    df_copy = df.copy()
    df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"])
    df_copy["year"] = df_copy["timestamp"].dt.year
    
    yearly_counts = df_copy.groupby(["author_name", "year"]).size().unstack(fill_value=0)
    yearly_counts["total_messages"] = yearly_counts.sum(axis=1)
    
    final_csv_df = yearly_counts.reset_index().sort_values("total_messages", ascending=False)
    
    # Convertit les colonnes de comptage en entiers
    count_cols = [col for col in final_csv_df.columns if col not in ["author_name"]]
    final_csv_df[count_cols] = final_csv_df[count_cols].astype(int)
    
    # Sauvegarde le DataFrame en CSV
    final_csv_df.to_csv(filename, index=False)
    logging.info(f"Statistiques sauvegardées dans {filename}.")
    
    return df