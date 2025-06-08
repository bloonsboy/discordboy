from dash import dcc, html
from appus import CSV_FILE_NAME

def create_upload_view():
    """Génère la mise en page pour la vue de téléversement du fichier ZIP."""
    return html.Div(
        style={
            'fontFamily': 'Arial, sans-serif', 'padding': '30px', 'maxWidth': '700px',
            'margin': '50px auto', 'textAlign': 'center', 'border': '1px solid #ddd',
            'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'
        },
        children=[
            html.H1("Importation des Données Discord", style={'color': '#007bff', 'marginBottom': '25px'}),
            html.P(f"Le fichier de données requis ('{CSV_FILE_NAME}') est introuvable."),
            html.P("Veuillez téléverser l'archive .zip de vos données Discord."),
            dcc.Upload(
                id='upload-zip-data',
                children=html.Div([
                    'Glissez-déposez votre fichier .zip ici, ou ',
                    html.A('Cliquez pour sélectionner un fichier', style={'color': '#007bff', 'textDecoration': 'underline', 'cursor': 'pointer'})
                ]),
                style={
                    'width': '100%', 'height': '120px', 'lineHeight': '120px', 'borderWidth': '2px',
                    'borderStyle': 'dashed', 'borderColor': '#007bff', 'borderRadius': '5px',
                    'textAlign': 'center', 'margin': '30px 0', 'backgroundColor': '#f9f9f9'
                },
                multiple=False,
                accept='.zip'
            ),
            html.Div(id='upload-output-status', style={'marginTop': '20px', 'padding': '10px', 'minHeight': '40px', 'fontWeight': 'bold'})
        ]
    )

def create_main_page_view():
    """Génère la mise en page pour la vue principale (après chargement des données)."""
    return html.Div(
        style={
            'fontFamily': 'Arial, sans-serif', 'padding': '30px', 'maxWidth': '1200px',
            'margin': '30px auto', 'textAlign': 'center'
        },
        children=[
            html.H1("Page Principale - Statistiques Discord", style={'color': '#28a745', 'marginBottom': '30px'}),
            html.P("Le fichier de données a été chargé avec succès."),
            html.P("Cette page affichera bientôt vos graphiques et analyses.", style={'fontSize': '1.1em', 'color': '#333'}),
            html.Div(id="graphs-container", style={'marginTop': '40px'}),
            html.Footer(
                "Application de statistiques Discord",
                style={'marginTop': '50px', 'paddingTop': '20px', 'borderTop': '1px solid #eee', 'fontSize': '0.9em', 'color': 'grey'}
            )
        ]
    )
