import dash
from dash import dcc, html
import os

CSV_FILE_NAME = "package_messages.csv"

def check_csv_exists():
    return os.path.exists(CSV_FILE_NAME)

def init_app():
    app = dash.Dash(
        __name__,
        suppress_callback_exceptions=True,
        title="Statistiques Discord"
    )

    app.layout = html.Div([
        dcc.Store(id='store-csv-status', data={'csv_exists': check_csv_exists()}),
        html.Div(id='page-content')
    ])
    return app

app_instance = init_app()
server = app_instance.server
