# dashboardus/appus.py

import dash
import json
import os
import pandas as pd
import dash_bootstrap_components as dbc
from .layoutus import create_layout
from .callbackus import register_callbacks

# Thème Litera et Font Awesome pour les icônes
EXTERNAL_STYLESHEETS = [
    dbc.themes.LITERA,
    "https://use.fontawesome.com/releases/v5.15.4/css/all.css",
]


def create_app(df, role_colors_map, member_data):
    """
    Crée et configure l'application Dash.
    """
    app = dash.Dash(
        __name__,
        title="Statistiques Discord",
        external_stylesheets=EXTERNAL_STYLESHEETS,
    )

    app.layout = create_layout(df)

    # Transmet les nouvelles 'member_data' aux callbacks
    register_callbacks(app, df, role_colors_map, member_data)

    return app
