# dashboardus/appus.py

import dash
import json
import os
import pandas as pd
from .layoutus import create_layout
from .callbackus import register_callbacks

# Ajoutez les feuilles de style Bootstrap via un CDN
EXTERNAL_STYLESHEETS = ['https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css']

def create_app(df, user_id_to_name_map, role_colors_map):
    """
    Crée et configure l'application Dash.
    """
    # Ajoutez external_stylesheets=EXTERNAL_STYLESHEETS lors de l'initialisation de l'application
    app = dash.Dash(__name__, title="Statistiques Discord", external_stylesheets=EXTERNAL_STYLESHEETS)
    
    # Configure les styles pour les dropdowns et date pickers
    app.layout = create_layout(df)
    
    # Enregistre toutes les fonctions de callback
    register_callbacks(app, df, user_id_to_name_map, role_colors_map)
    
    return app