# dashboardus/layoutus.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd

def create_layout(df):
    """
    Crée le layout du tableau de bord Dash en utilisant les données du DataFrame.
    """
    if df.empty:
        return html.Div("Aucune donnée disponible pour créer le tableau de bord.")

    # Pré-calculer les 5 premiers utilisateurs pour la valeur par défaut
    user_counts_all_time = df["author_name"].value_counts()
    initial_users = user_counts_all_time.nlargest(5).index.tolist()

    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    return html.Div(
        className="container-fluid bg-light",
        style={"fontFamily": "Inter, sans-serif"},
        children=[
            dcc.Markdown(id='dynamic-styles', style={'display': 'none'}),
            html.Header(
                className="bg-white shadow-sm mb-4",
                children=html.Div(
                    className="container d-flex align-items-center py-3",
                    children=[
                        html.I(className="fas fa-chart-bar me-3", style={"fontSize": "2rem", "color": "#4a90e2"}),
                        html.H1("Tableau de Bord des Messages Discord", className="h3 mb-0"),
                    ]
                )
            ),
            
            html.Div(
                id="filter-panel",
                className="card shadow-sm mb-4",
                children=html.Div(
                    className="card-body",
                    children=[
                        html.H5("Filtres", className="card-title"),
                        html.Div(
                            className="row g-3 align-items-end",
                            children=[
                                html.Div(
                                    className="col-md-3",
                                    children=[
                                        html.Label("Top", className="form-label"),
                                        dcc.Dropdown(
                                            id="top-n-dropdown",
                                            options=[
                                                {"label": "Top 5", "value": 5}, {"label": "Top 10", "value": 10},
                                                {"label": "Top 20", "value": 20}, {"label": "+ 1000 messages", "value": "1000+"},
                                                {"label": "Personnalisé", "value": "custom"},
                                            ],
                                            value=5, clearable=False,
                                        ),
                                    ]
                                ),
                                html.Div(
                                    className="col-md-5",
                                    children=[
                                        html.Label("Utilisateurs", className="form-label"),
                                        dcc.Dropdown(id="user-dropdown", multi=True),
                                    ]
                                ),
                                html.Div(
                                    className="col-md-4",
                                    children=[
                                        html.Label("Période", className="form-label"),
                                        dcc.Dropdown(
                                            id="date-range-dropdown",
                                            options=[
                                                {"label": "Personnalisé", "value": "custom"}, {"label": "Année en cours", "value": "current_year"},
                                                {"label": "Derniers 365 jours", "value": "last_365"}, {"label": "Derniers 6 mois", "value": "last_6_months"},
                                                {"label": "All-time", "value": "all-time"},
                                            ],
                                            value="last_365", clearable=False,
                                        ),
                                    ]
                                ),
                                html.Div(
                                    className="col-md-8",
                                    children=[
                                        html.Label("Plage de dates", className="form-label"),
                                        dcc.DatePickerRange(
                                            id="date-picker-range",
                                            min_date_allowed=min_date, max_date_allowed=max_date,
                                            start_date=min_date, end_date=max_date, display_format="DD/MM/YYYY",
                                            className="w-100"
                                        ),
                                        html.Div(id="date-range-display", className="text-muted mt-2 small"),
                                    ]
                                ),
                                # <-- NOUVEAU SÉLECTEUR -->
                                html.Div(
                                    className="col-md-4",
                                    children=[
                                        html.Label("Analyser par :", className="form-label fw-bold"),
                                        dbc.RadioItems(
                                            id='metric-selector',
                                            options=[
                                                {'label': 'Nombre de Messages', 'value': 'messages'},
                                                {'label': 'Nombre de Caractères', 'value': 'characters'},
                                            ],
                                            value='messages',
                                            inline=True,
                                            labelClassName="me-3",
                                            inputClassName="me-1",
                                        )
                                    ]
                                )
                            ],
                        ),
                    ]
                )
            ),

            html.Div(id="user-profile-card-container"),

            html.Div(
                className="row",
                children=[
                    html.Div(className="col-lg-12 mb-4", children=create_graph_card("📈 Évolution Cumulative", "cumulative-graph")),
                    html.Div(className="col-lg-6 mb-4", children=create_graph_card("📅 Activité par Mois", "monthly-graph")),
                    html.Div(className="col-lg-6 mb-4", children=create_graph_card("⏰ Distribution Horaire (%)", "hourly-graph")),
                    html.Div(className="col-lg-6 mb-4", children=create_graph_card("🗓️ Activité par Jour de la Semaine", "weekday-graph")),
                    html.Div(className="col-lg-3 mb-4", children=create_leaderboard_card("🏆 Champions Mensuels", "monthly-leaderboard-container")),
                    html.Div(className="col-lg-3 mb-4", children=create_leaderboard_card("🥇 Champions Journaliers", "daily-leaderboard-container")),
                ],
            ),
        ],
    )

def create_graph_card(title, graph_id):
    return html.Div(
        className="card shadow-sm h-100",
        children=[
            html.Div(className="card-header", children=html.H5(title, className="card-title mb-0")),
            html.Div(className="card-body", children=dcc.Loading(dcc.Graph(id=graph_id, className="h-100"), type="default")),
        ]
    )

def create_leaderboard_card(title, container_id):
    return html.Div(
        className="card shadow-sm h-100",
        children=[
            html.Div(className="card-header", children=html.H5(title, className="card-title mb-0")),
            html.Div(className="card-body", children=dcc.Loading(html.Div(id=container_id), type="default")),
        ]
    )

