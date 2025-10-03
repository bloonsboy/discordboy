# dashboardus/appus.py

import dash
import dash_bootstrap_components as dbc
from .layoutus import create_layout
from .callbackus import register_callbacks

EXTERNAL_STYLESHEETS = [dbc.themes.LITERA, dbc.icons.FONT_AWESOME]

def create_app(df, role_colors_map, current_member_ids):
    app = dash.Dash(
        __name__, 
        title="Discord Dashboard", 
        external_stylesheets=EXTERNAL_STYLESHEETS
    )
    
    app.layout = create_layout(df)    
    register_callbacks(app, df, role_colors_map, current_member_ids)
    return app

