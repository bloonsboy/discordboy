import base64
import io
import os
from dash.dependencies import Input, Output, State
from dash import html, dash

from .appus import app_instance as app, CSV_FILE_NAME, check_csv_exists
from .viewus import main_page_view, upload_view

from fonctionus.extractus import *
from fonctionus.convertus import *

@app.callback(
    Output('page-content', 'children'),
    Input('store-csv-status', 'data')
)
def render_page_content(csv_status_data):
    if csv_status_data and csv_status_data.get('csv_exists'):
        return main_page_view()
    else:
        return upload_view()

@app.callback(
    [Output('upload-output-status', 'children'),
     Output('store-csv-status', 'data')],
    Input('upload-zip-data', 'contents'),
    State('upload-zip-data', 'filename'),
    prevent_initial_call=True
)
def handle_zip_upload(contents, filename):
    """
    Traite le fichier .zip téléversé, crée le fichier CSV,
    et fournit un retour visuel à l'utilisateur.
    """
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded_content = base64.b64decode(content_string)

        try:
            if filename is not None and filename.endswith('.zip'):
                print(f"Traitement du fichier ZIP téléversé : {filename}")

                # 1. Extraire l'intégralité du ZIP dans un dossier
                with io.BytesIO(decoded_content) as zip_file_object:
                    extracted_package_path = extract_full_package_from_zip(zip_file_object, clear_existing_extraction=True)

                if extracted_package_path:
                    print(f"ZIP extrait dans : {extracted_package_path}")

                    # 2. Traiter les fichiers extraits pour créer le CSV final
                    # Le fichier sera créé à la racine du projet
                    success_processing = process_discord_package_to_csv(extracted_package_path, CSV_FILE_NAME)

                    if success_processing:
                        print(f"Fichier '{CSV_FILE_NAME}' créé avec succès.")
                        # On met à jour le message de statut ET le store pour changer de page
                        return html.Span(f"Fichier '{filename}' traité et '{CSV_FILE_NAME}' créé ! Redirection...", style={'color': 'green', 'fontWeight': 'bold'}), \
                               {'csv_exists': True}
                    else:
                        print(f"Échec du traitement du package pour créer '{CSV_FILE_NAME}'.")
                        # On affiche un message d'erreur et on ne change pas de page
                        return html.Span(f"Erreur lors du traitement des données de '{filename}'. Vérifiez les logs du serveur.", style={'color': 'red'}), \
                               {'csv_exists': check_csv_exists()}
                else:
                    print(f"Échec de l'extraction du ZIP '{filename}'.")
                    return html.Span(f"Erreur lors de l'extraction de '{filename}'. Est-il valide ?", style={'color': 'red'}), \
                           {'csv_exists': check_csv_exists()}
            else:
                return html.Span(f"Erreur : Le fichier '{filename}' n'est pas un .zip valide.", style={'color': 'red'}), \
                       {'csv_exists': check_csv_exists()}

        except Exception as e:
            print(f"Erreur inattendue dans handle_zip_upload pour '{filename}': {e}")
            import traceback
            traceback.print_exc()
            return html.Span(f"Une erreur serveur majeure est survenue. Détails: {e}", style={'color': 'red'}), \
                   {'csv_exists': check_csv_exists()}

    return dash.no_update, dash.no_update
