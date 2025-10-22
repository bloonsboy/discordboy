# dashboardus/layoutus.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta  # <--- CORRECTION: timedelta ajouté
import pandas as pd


def create_layout(df):
    if df.empty:
        return html.Div("No data available to display.")
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    return html.Div(
        className="container-fluid bg-light",
        style={"fontFamily": "Inter, sans-serif"},
        children=[
            dcc.Markdown(id="dynamic-styles", style={"display": "none"}),
            # --- En-tête ---
            html.Header(
                className="bg-white shadow-sm mb-4",
                children=html.Div(
                    className="container-xxl d-flex align-items-center py-3",
                    children=[
                        html.I(
                            className="fab fa-discord me-3",
                            style={"fontSize": "2rem", "color": "#5865F2"},
                        ),
                        html.H1("Dashboard d'Activité Discord", className="h3 mb-0"),
                    ],
                ),
            ),
            # --- Panneau des Filtres ---
            html.Div(
                id="filter-panel",
                className="card shadow-sm mb-4",
                children=html.Div(
                    className="card-body",
                    children=[
                        html.H5("Filtres", className="card-title"),
                        html.Div(
                            className="row g-3",
                            children=[
                                # --- Colonne 1: Top & Analyse ---
                                html.Div(
                                    className="col-md-3",
                                    children=[
                                        html.Label("Top Users", className="form-label"),
                                        dcc.Dropdown(
                                            id="top-n-dropdown",
                                            options=[
                                                {"label": "Top 5", "value": 5},
                                                {"label": "Top 10", "value": 10},
                                                {"label": "Top 20", "value": 20},
                                                {"label": "Top 50", "value": 50},
                                                {"label": "Custom", "value": "custom"},
                                            ],
                                            value=10,
                                            clearable=False,
                                        ),
                                        html.Label(
                                            "Analyser par :",
                                            className="form-label fw-bold mt-3",
                                        ),
                                        dbc.RadioItems(
                                            id="metric-selector",
                                            options=[
                                                {
                                                    "label": "Nb. Messages",
                                                    "value": "messages",
                                                },
                                                {
                                                    "label": "Nb. Caractères",
                                                    "value": "characters",
                                                },
                                            ],
                                            value="messages",
                                            inline=True,
                                            labelClassName="me-3",
                                            inputClassName="me-1",
                                        ),
                                    ],
                                ),
                                # --- Colonne 2: Sélection des Utilisateurs ---
                                html.Div(
                                    className="col-md-5",
                                    children=[
                                        html.Label(
                                            "Utilisateurs", className="form-label"
                                        ),
                                        dcc.Dropdown(id="user-dropdown", multi=True),
                                        html.Label(
                                            "Highlight User",
                                            className="form-label mt-3",
                                        ),
                                        dcc.Dropdown(
                                            id="highlight-user-dropdown",
                                            clearable=True,
                                            placeholder="Sélectionner un utilisateur...",
                                        ),
                                    ],
                                ),
                                # --- Colonne 3: Période & Filtres de Rôle ---
                                html.Div(
                                    className="col-md-4",
                                    children=[
                                        html.Label("Période", className="form-label"),
                                        dcc.Dropdown(
                                            id="date-range-dropdown",
                                            options=[
                                                {"label": "Custom", "value": "custom"},
                                                {
                                                    "label": "Année en cours",
                                                    "value": "current_year",
                                                },
                                                {
                                                    "label": "Derniers 365 jours",
                                                    "value": "last_365",
                                                },
                                                {
                                                    "label": "6 derniers mois",
                                                    "value": "last_6_months",
                                                },
                                                {
                                                    "label": "All-time",
                                                    "value": "all-time",
                                                },
                                            ],
                                            value="last_365",
                                            clearable=False,
                                        ),
                                        html.Label("Date", className="form-label mt-3"),
                                        dcc.DatePickerRange(
                                            id="date-picker-range",
                                            min_date_allowed=min_date,
                                            max_date_allowed=max_date,
                                            start_date=(
                                                datetime.now() - timedelta(days=365)
                                            ).date(),
                                            end_date=datetime.now().date(),
                                            display_format="DD/MM/YYYY",
                                            className="w-100",
                                        ),
                                        html.Div(
                                            id="date-range-display",
                                            className="text-muted mt-2 small",
                                        ),
                                        html.Label(
                                            "Filtre Spécial",
                                            className="form-label fw-bold mt-3",
                                        ),
                                        dbc.Checklist(
                                            options=[
                                                {
                                                    "label": "Afficher uniquement 'Virgule du 4'",
                                                    "value": 1,
                                                },
                                            ],
                                            value=[],
                                            id="virgule-filter",
                                            switch=True,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            # --- Carte de Profil (si highlight) ---
            html.Div(id="user-profile-card-container"),
            # --- Rubrique 1: Analyse Temporelle ---
            html.H2("Analyse Temporelle", className="h4 mt-5 mb-3"),
            html.Div(
                className="card shadow-sm mb-4",
                children=[
                    html.Div(
                        className="card-header d-flex justify-content-between align-items-center",
                        children=[
                            html.H5(
                                "Évolution de l'activité", className="card-title mb-0"
                            ),
                            dbc.RadioItems(
                                id="evolution-graph-selector",
                                options=[
                                    {"label": "Vue Cumulée", "value": "cumulative"},
                                    {"label": "Vue Mensuelle", "value": "monthly"},
                                ],
                                value="cumulative",
                                inline=True,
                                labelClassName="me-3",
                                inputClassName="me-1",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-body",
                        children=dcc.Loading(
                            dcc.Graph(id="evolution-graph", style={"height": "600px"}),
                            type="default",
                        ),
                    ),
                ],
            ),
            # --- Rubrique 2: Analyse des Messages ---
            html.H2("Analyse des Messages", className="h4 mt-5 mb-3"),
            html.Div(
                className="row",
                children=[
                    # Graphique de Longueur Médiane
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header",
                                        children=html.H5(
                                            "Longueur Médiane des Messages",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body",
                                        children=dcc.Loading(
                                            dcc.Graph(
                                                id="median-length-graph",
                                                style={"height": "500px"},
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                    # Graphique de Distribution (Heure/Jour/Mois/Année)
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header d-flex justify-content-between align-items-center",
                                        children=[
                                            html.H5(
                                                "Distribution (Top 5 vs Serveur)",
                                                className="card-title mb-0",
                                            ),
                                            dbc.RadioItems(
                                                id="distribution-time-unit",
                                                options=[
                                                    {"label": "Heure", "value": "hour"},
                                                    {
                                                        "label": "Jour",
                                                        "value": "weekday",
                                                    },
                                                    {"label": "Mois", "value": "month"},
                                                    {"label": "Année", "value": "year"},
                                                ],
                                                value="hour",
                                                inline=True,
                                                labelClassName="me-2 small",
                                                inputClassName="me-1",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="card-body",
                                        children=dcc.Loading(
                                            dcc.Graph(
                                                id="distribution-graph",
                                                style={"height": "500px"},
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            # --- Rubrique 3: Classements ---
            html.H2("Classements", className="h4 mt-5 mb-3"),
            html.Div(
                className="row",
                children=[
                    # Classements par Messages
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header bg-primary text-white",
                                        children=html.H5(
                                            "Champions par Nb. de Messages",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body p-0",
                                        children=[
                                            html.H6(
                                                "🏆 Champions Mensuels",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="monthly-leaderboard-msg")
                                            ),
                                            html.H6(
                                                "🥇 Champions Journaliers",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="daily-leaderboard-msg")
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                    # Classements par Caractères
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header bg-success text-white",
                                        children=html.H5(
                                            "Champions par Nb. de Caractères",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body p-0",
                                        children=[
                                            html.H6(
                                                "🏆 Champions Mensuels",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="monthly-leaderboard-char")
                                            ),
                                            html.H6(
                                                "🥇 Champions Journaliers",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="daily-leaderboard-char")
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
