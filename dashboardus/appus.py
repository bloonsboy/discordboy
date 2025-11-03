import dash
import dash_bootstrap_components as dbc

from .callbackus import register_callbacks
from .layoutus import create_layout

EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME]


def create_app(df, member_data, role_data, mudae_channel_ids):
    app = dash.Dash(
        __name__,
        external_stylesheets=EXTERNAL_STYLESHEETS,
        suppress_callback_exceptions=True,
        update_title=None,
    )

    app.title = "Virgule du 4'"
    app.layout = create_layout(df)

    register_callbacks(app, df, member_data, role_data, mudae_channel_ids)

    return app
