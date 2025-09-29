# dashboardus/appus.py

import dash
import dash_bootstrap_components as dbc
from .layoutus import create_layout
from .callbackus import register_callbacks

# Thème Bootstrap 5 "Litera" et icônes Font Awesome
EXTERNAL_STYLESHEETS = [dbc.themes.LITERA, dbc.icons.FONT_AWESOME]

def create_app(df, user_id_to_name_map, role_colors_map, current_member_ids):
    """
    Crée et configure l'application Dash.
    """
    app = dash.Dash(
        __name__, 
        title="Statistiques Discord", 
        external_stylesheets=EXTERNAL_STYLESHEETS
    )
    
    # Configure la mise en page
    app.layout = create_layout(df)
    
    # Enregistre toutes les fonctions de callback, en passant la liste des membres
    register_callbacks(app, df, user_id_to_name_map, role_colors_map, current_member_ids)
    
    return app

