import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State

from fonctionus.extractus import *

def init():
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Goofy aah stats discordo"

    app.layout = html.Div([
        dcc.Store(id='store-csv-status', data={'csv_exists': check_csv_exists()}),
        html.Div(id='page-content')
    ])