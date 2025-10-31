# discordboy/dashboardus/appus.py

import dash
import dash_bootstrap_components as dbc

from .callbackus import register_callbacks
from .layoutus import create_layout

EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME]


def create_app(df, role_colors_map, member_data, role_names_map):
    app = dash.Dash(
        __name__,
        external_stylesheets=EXTERNAL_STYLESHEETS,
        suppress_callback_exceptions=True,
        update_title=None,
    )

    app.title = "Virgule du 4'"
    app.layout = create_layout(df)

    register_callbacks(app, df, role_colors_map, member_data, role_names_map)

    return app
