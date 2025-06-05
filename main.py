import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import os
import base64
import io
import zipfile
import pandas as pd

from fonctionus.extractus import *
from interfacus.dashus import *



def prepare_for_dash_datatable(table_data_input, headers_input):
    """
    Transforme les données brutes (liste de listes) et les en-têtes
    en un format utilisable par dash_table.DataTable.
    """
    data_rows_raw = []
    total_row_raw = None
    for row in table_data_input:
        if isinstance(row, list) and len(row) > 0:
            processed_row = [str(item) for item in row]
            if processed_row[0].strip().lower() == "total":
                total_row_raw = processed_row
            else:
                data_rows_raw.append(processed_row)
    
    data_for_table = [dict(zip(headers_input, row_values)) for row_values in data_rows_raw]
    if total_row_raw:
        data_for_table.append(dict(zip(headers_input, total_row_raw)))
    columns_for_table = [{"name": str(col_id), "id": str(col_id)} for col_id in headers_input]
    return data_for_table, columns_for_table

def load_and_process_data_from_csv(csv_path):
    """
    Charge et traite les données du fichier CSV.
    REMPLACEZ CECI PAR VOTRE LOGIQUE DE TRAITEMENT DE DONNÉES RÉELLE.
    Cette fonction doit retourner les `headers` et `data_rows` pour la table.
    """
    # Exemple de simulation de chargement et de traitement de données:
    # try:
    #     df = pd.read_csv(csv_path)
    #     # ... votre logique pour extraire top_message_data et actual_headers à partir du df ...
    #     # Par exemple, en appelant votre fonction top_messages(df, ...)
    #     # type_list_local = ["DM", "Messages Groupe", "Messages Serveur"] # ou dérivé du df
    #     # top_messages_data_local = top_messages(df, 10, type_list_local) # Votre fonction
    #     # actual_headers_local = ["Utilisateur/Canal"] + type_list_local
    #     # return actual_headers_local, top_messages_data_local
    # except Exception as e:
    #     print(f"Error loading data from CSV: {e}")
    #     return [], [] # Retourner des données vides en cas d'erreur

    # Simulation pour l'exemple sans Pandas et sans la fonction top_messages définie ici:
    simulated_type_list = ["DM", "Messages Groupe", "Messages Serveur"]
    actual_headers_local = ["Utilisateur/Canal"] + simulated_type_list
    top_message_data_local = [
        ["Alice", 150, 25, 10], ["Bob", 120, 30, 5], ["Charlie", 100, 10, 0],
        ["David", 90, 0, 15], ["Eve", 80, 5, 5], ["Frank", 70, 0, 0],
        ["Grace", 60, 10, 10], ["Henry", 50, 5, 0], ["Ivy", 40, 0, 2],
        ["Jack", 30, 2, 3], ["Total", 890, 87, 50]
    ]
    return actual_headers_local, top_message_data_local

app = dash.Dash(__name__, suppress_callback_exceptions=True) # suppress_callback_exceptions utile car les sorties des callbacks sont dans render_page_content
app.title = "Statistiques Discord"

# --- Définition de la mise en page de l'application ---
app.layout = html.Div([
    dcc.Store(id='store-csv-status', data={'csv_exists': check_csv_exists()}),
    html.Div(id='page-content')
])

# --- Callbacks ---
@app.callback(
    Output('page-content', 'children'),
    Input('store-csv-status', 'data')
)
def render_page_content(csv_status_data):
    """Rendu conditionnel du contenu de la page basé sur l'existence du CSV."""
    if csv_status_data and csv_status_data.get('csv_exists'):
        # Le CSV existe, afficher la vue principale de l'application
        actual_headers_local, top_message_data_local = load_and_process_data_from_csv(CSV_FILE_NAME)
        
        if not actual_headers_local or not top_message_data_local:
             # Gérer le cas où le chargement des données a échoué même si le CSV existe
            return html.Div([
                html.H3("Erreur lors du chargement des données depuis package_messages.csv.", style={'color': 'red', 'textAlign': 'center'}),
                html.P("Veuillez vérifier le fichier CSV ou essayer de réimporter le ZIP.", style={'textAlign': 'center'}),
                # Optionnellement, ajouter un bouton pour retourner à l'upload
                 html.Button("Réessayer l'importation ZIP", id="force-upload-view-btn", n_clicks=0, style={'display': 'block', 'margin': '20px auto'})

            ])

        current_data_for_dash, current_columns_for_dash = prepare_for_dash_datatable(top_message_data_local, actual_headers_local)

        return html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'maxWidth': '1000px', 'margin': 'auto'}, children=[
            html.H1("Tableau de Bord Discord", style={'textAlign': 'center', 'color': '#1DA1F2', 'marginBottom': '30px'}),
            html.Div([
                dcc.Input(id='path-input', type='text', placeholder='Entrez un chemin de fichier/dossier ici...', style={'width': '70%', 'padding': '10px', 'marginRight': '10px', 'borderRadius': '5px', 'border': '1px solid #ccc'}),
                html.Button('Lancer le traitement', id='submit-path-button', n_clicks=0, style={'padding': '10px 15px', 'backgroundColor': '#1DA1F2', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer'})
            ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'}),
            html.Div(id='path-output-status', style={'marginBottom': '20px', 'padding': '10px', 'border': '1px dashed #ccc', 'borderRadius': '5px', 'minHeight': '30px', 'lineHeight': '30px'}),
            html.H2("Top Interactions Discord", style={'textAlign': 'center', 'color': '#333', 'marginTop': '40px', 'marginBottom': '20px'}),
            dash_table.DataTable(
                id='discord-stats-table',
                columns=current_columns_for_dash,
                data=current_data_for_dash,
                style_as_list_view=True,
                style_header={'backgroundColor': 'rgb(240, 240, 240)', 'fontWeight': 'bold', 'border': '1px solid grey', 'textAlign': 'center', 'padding': '10px', 'color': 'black'},
                style_cell={'textAlign': 'left', 'padding': '8px', 'border': '1px solid lightgrey', 'minWidth': '80px', 'width': '120px', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap'},
                style_cell_conditional=[
                    {'if': {'column_id': actual_headers_local[0] if actual_headers_local else ''}, 'textAlign': 'center', 'minWidth': '150px', 'width': '180px'}
                ] + [
                    {'if': {'column_id': col_id}, 'textAlign': 'right'} for col_id in (actual_headers_local[1:] if actual_headers_local and len(actual_headers_local) > 1 else [])
                ],
                style_data_conditional=[
                    {'if': {'filter_query': f'{{{actual_headers_local[0] if actual_headers_local else ""}}} = "Total"'}, 'fontWeight': 'bold', 'backgroundColor': 'rgb(230, 230, 230)'}
                ],
                page_size=11,
                markdown_options={"html": True}
            ),
            html.Footer("Application générée avec Dash.", style={'textAlign': 'center', 'marginTop': '40px', 'fontSize': '0.8em', 'color': 'grey'})
        ])
    else:
        # Le CSV n'existe pas, afficher la vue de téléversement
        return html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'maxWidth': '800px', 'margin': 'auto', 'textAlign': 'center'}, children=[
            html.H1("Importation des Données Discord", style={'color': '#1DA1F2', 'marginBottom': '30px'}),
            html.P(f"Le fichier '{CSV_FILE_NAME}' est introuvable."),
            html.P("Veuillez téléverser le fichier .zip contenant vos données Discord."),
            dcc.Upload(
                id='upload-zip-data',
                children=html.Div(['Glissez-déposez ou ', html.A('Sélectionnez un fichier .zip')]),
                style={'width': '90%', 'height': '100px', 'lineHeight': '100px', 'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center', 'margin': '20px auto', 'padding': '10px'},
                multiple=False,
                accept='.zip'
            ),
            html.Div(id='upload-output-status', style={'marginTop': '20px', 'padding': '10px', 'minHeight': '30px'})
        ])

@app.callback(
    Output('path-output-status', 'children', allow_duplicate=True), # allow_duplicate car path-output-status peut être initialisé par render_page_content
    Input('submit-path-button', 'n_clicks'),
    State('path-input', 'value'),
    prevent_initial_call=True
)
def update_output_div_on_path_submit(n_clicks, path_value):
    """Gère la soumission du chemin."""
    if n_clicks > 0: # Agit seulement si le bouton a été cliqué
        if path_value:
            try:
                if os.path.exists(path_value):
                    # Ici, vous mettriez votre logique de traitement du chemin
                    return html.Span(f"Le chemin '{path_value}' existe. Traitement simulé lancé...", style={'color': 'green'})
                else:
                    return html.Span(f"Le chemin '{path_value}' n'existe pas ou est inaccessible.", style={'color': 'orange'})
            except Exception as e:
                return html.Span(f"Erreur lors du traitement du chemin '{path_value}': {e}", style={'color': 'red'})
        else:
            return html.Span("Veuillez entrer un chemin avant de soumettre.", style={'color': 'grey'})
    return "Entrez un chemin et cliquez sur 'Lancer le traitement'." # Message par défaut ou dash.no_update

@app.callback(
    [Output('upload-output-status', 'children'),
     Output('store-csv-status', 'data')],
    Input('upload-zip-data', 'contents'),
    State('upload-zip-data', 'filename'),
    prevent_initial_call=True
)
def handle_zip_upload(contents, filename):
    """Gère le téléversement du fichier ZIP et l'extraction du CSV."""
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if filename is not None and filename.endswith('.zip'):
                with io.BytesIO(decoded) as zip_buffer:
                    with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                        if CSV_FILE_NAME in zip_ref.namelist():
                            # Extrait vers le répertoire courant du script
                            zip_ref.extract(CSV_FILE_NAME, path=".") 
                            return html.Span(f"'{CSV_FILE_NAME}' extrait de '{filename}' avec succès!", style={'color': 'green'}), \
                                   {'csv_exists': True} # Met à jour le store pour recharger la page-content
                        else:
                            return html.Span(f"'{CSV_FILE_NAME}' non trouvé dans '{filename}'. Vérifiez le contenu du ZIP.", style={'color': 'orange'}), \
                                   dash.no_update # Ne change pas le statut de csv_exists
            else:
                return html.Span("Type de fichier invalide. Veuillez téléverser un fichier .zip.", style={'color': 'red'}), \
                       dash.no_update
        except zipfile.BadZipFile:
            return html.Span(f"Erreur: Le fichier '{filename}' n'est pas un fichier ZIP valide ou est corrompu.", style={'color': 'red'}), \
                   dash.no_update
        except Exception as e:
            return html.Span(f"Erreur lors du traitement du fichier ZIP : {e}", style={'color': 'red'}), \
                   dash.no_update
    return dash.no_update, dash.no_update

@app.callback(
    Output('store-csv-status', 'data', allow_duplicate=True),
    Input('force-upload-view-btn', 'n_clicks'),
    prevent_initial_call=True
)
def force_upload_view(n_clicks):
    """Permet de retourner à la vue d'upload si le chargement de CSV échoue."""
    if n_clicks > 0:
        return {'csv_exists': False}
    return dash.no_update

# --- Lancement du serveur Dash ---
if __name__ == '__main__':
    app.run(debug=True)
