# dashboardus/layoutus.py

from dash import dcc, html
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
    sorted_users = sorted(df["author_name"].unique())

    return html.Div(
        className="container-fluid",
        style={
            "fontFamily": "Inter, sans-serif",
            "padding": "0",
            "margin": "0",
            "backgroundColor": "#F4F4F9",
            "color": "#333",
        },
        children=[
            html.H1(
                "📊 Tableau de Bord des Messages Discord",
                className="text-center my-4",
            ),
            html.Div(
                className="p-3 mb-4",
                children=[
                    html.Div(
                        className="row g-3",
                        children=[
                            # Filtre TOP
                            html.Div(
                                className="col-md-3",
                                children=[
                                    html.Label("Top", className="form-label"),
                                    dcc.Dropdown(
                                        id="top-n-dropdown",
                                        options=[
                                            {"label": "Top 5", "value": 5},
                                            {"label": "Top 10", "value": 10},
                                            {"label": "Top 20", "value": 20},
                                            {"label": "+ 1000 messages", "value": "1000+"},
                                            {"label": "Personnalisé", "value": "custom"},
                                        ],
                                        value=5,
                                        clearable=False,
                                        style={"border": "0px", "boxShadow": "none"},
                                        className="form-control"
                                    ),
                                ]
                            ),
                            # Filtre Utilisateurs
                            html.Div(
                                className="col-md-4",
                                children=[
                                    html.Label("Utilisateurs", className="form-label"),
                                    dcc.Dropdown(
                                        id="user-dropdown",
                                        options=[{"label": user, "value": user} for user in sorted_users],
                                        value=initial_users, # <-- Nouvelle valeur par défaut
                                        multi=True,
                                        style={"border": "0px", "boxShadow": "none"},
                                        className="form-control",
                                    ),
                                ]
                            ),
                            # Filtre Période
                            html.Div(
                                className="col-md-2",
                                children=[
                                    html.Label("Période", className="form-label"),
                                    dcc.Dropdown(
                                        id="date-range-dropdown",
                                        options=[
                                            {"label": "Personnalisé", "value": "custom"},
                                            {"label": "Année en cours", "value": "current_year"},
                                            {"label": "Derniers 365 jours", "value": "last_365"},
                                            {"label": "Derniers 6 mois", "value": "last_6_months"},
                                            {"label": "All-time", "value": "all-time"},
                                        ],
                                        value="last_365",
                                        clearable=False,
                                        style={"border": "0px", "boxShadow": "none"},
                                        className="form-control",
                                    ),
                                ]
                            ),
                            # Plage de dates
                            html.Div(
                                className="col-md-3",
                                children=[
                                    html.Label("Plage de dates", className="form-label"),
                                    dcc.DatePickerRange(
                                        id="date-picker-range",
                                        min_date_allowed=min_date,
                                        max_date_allowed=max_date,
                                        start_date=min_date,
                                        end_date=max_date,
                                        display_format="DD/MM/YYYY",
                                        style={"border": "0px", "boxShadow": "none"},
                                        className="form-control",
                                    ),
                                    html.Div(
                                        id="date-range-display",
                                        className="text-muted mt-2 small"
                                    ),
                                ]
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="graphs-container",
                className="mt-4",
                children=[
                    create_graph_section("📈 Messages Cumulés au Fil du Temps (par jour)", "cumulative", "cumulative-graph"),
                    create_graph_section("📅 Messages par Mois", "monthly", "monthly-graph"),
                    create_graph_section("⏰ Distribution des messages par heure (%)", "hourly", "hourly-graph"),
                    html.Div(
                        className="row mt-4 g-3",
                        children=[
                            html.Div(
                                className="col-md-6",
                                children=create_leaderboard_section("🏆 Champion mensuel du nombre de messages", "monthly-leaderboard-container"),
                            ),
                            html.Div(
                                className="col-md-6",
                                children=create_leaderboard_section("🏆 Champion journalier du nombre de messages", "daily-leaderboard-container"),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

def create_graph_section(title, id_prefix, graph_id):
    """
    Crée une section de graphique réutilisable.
    """
    return html.Div(
        className="card p-3 mb-4",
        children=[
            html.Div(
                className="d-flex align-items-center justify-content-center mb-3",
                children=[
                    html.H2(title, className="me-2 mb-0"),
                    html.Button(
                        "Afficher/Masquer",
                        id=f"toggle-{id_prefix}",
                        n_clicks=0,
                        className="btn btn-outline-secondary btn-sm"
                    ),
                ],
            ),
            dcc.Graph(id=graph_id),
        ],
    )

def create_leaderboard_section(title, container_id):
    """
    Crée une section de classement réutilisable.
    """
    return html.Div(
        className="card p-3",
        children=[
            html.H2(title, className="text-center"),
            html.Div(id=container_id, className="mt-3"),
        ],
    )