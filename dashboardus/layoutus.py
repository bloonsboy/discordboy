# dashboardus/layoutus.py

from dash import dcc, html

def create_layout(df):
    """
    Crée le layout moderne du tableau de bord Dash.
    """
    if df.empty:
        return html.Div("Aucune donnée disponible pour créer le tableau de bord.")

    user_counts_all_time = df["author_name"].value_counts()
    initial_users = user_counts_all_time.nlargest(5).index.tolist()
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    return html.Div(
        className="container-fluid py-4",
        children=[
            # --- En-tête ---
            html.Header(
                className="text-center mb-4",
                children=[
                    html.H1(
                        "📊 Tableau de Bord des Messages Discord",
                        className="main-title"
                    ),
                    html.P(
                        "Analysez l'activité de votre serveur en quelques clics.",
                        className="lead text-muted"
                    )
                ]
            ),

            # --- Panneau de filtres ---
            html.Div(
                id="filter-panel", # Ajout d'un ID pour le ciblage CSS
                className="card shadow-sm mb-4",
                children=[
                    html.Div(className="card-header", children="⚙️ Filtres"),
                    html.Div(
                        className="card-body",
                        children=[
                            html.Div(
                                className="row g-3 align-items-end",
                                children=[
                                    create_filter_column("Top Utilisateurs", "top-n-dropdown", dcc.Dropdown(
                                        id="top-n-dropdown",
                                        options=[
                                            {"label": "Top 5", "value": 5},
                                            {"label": "Top 10", "value": 10},
                                            {"label": "Top 20", "value": 20},
                                            {"label": "+ 1000 messages", "value": "1000+"},
                                            {"label": "Personnalisé", "value": "custom"},
                                        ],
                                        value=5, clearable=False
                                    )),
                                    create_filter_column("Utilisateurs", "user-dropdown", dcc.Dropdown(
                                        id="user-dropdown",
                                        value=initial_users, multi=True
                                    ), width=4),
                                    create_filter_column("Période Prédéfinie", "date-range-dropdown", dcc.Dropdown(
                                        id="date-range-dropdown",
                                        options=[
                                            {"label": "Personnalisé", "value": "custom"},
                                            {"label": "Année en cours", "value": "current_year"},
                                            {"label": "365 derniers jours", "value": "last_365"},
                                            {"label": "6 derniers mois", "value": "last_6_months"},
                                            {"label": "Depuis le début", "value": "all-time"},
                                        ],
                                        value="last_365", clearable=False
                                    )),
                                    html.Div(
                                        className="col-md-3",
                                        children=[
                                            html.Label("Plage de dates", className="form-label fw-bold"),
                                            dcc.DatePickerRange(
                                                id="date-picker-range",
                                                min_date_allowed=min_date,
                                                max_date_allowed=max_date,
                                                start_date=min_date,
                                                end_date=max_date,
                                                display_format="DD/MM/YYYY",
                                                className="form-control"
                                            ),
                                            html.Div(id="date-range-display", className="text-muted mt-2 small")
                                        ]
                                    ),
                                ]
                            )
                        ]
                    )
                ]
            ),

            # --- Sections de Graphiques ---
            create_graph_card("📈 Messages Cumulés", "cumulative-graph"),
            create_graph_card("📅 Messages par Mois", "monthly-graph"),
            create_graph_card("⏰ Distribution Horaire (%)", "hourly-graph"),

            # --- Section des Classements ---
            html.Div(
                className="row mt-4 g-4",
                children=[
                    create_leaderboard_card("🏆 Champions Mensuels", "monthly-leaderboard-container"),
                    create_leaderboard_card("🥇 Champions Journaliers", "daily-leaderboard-container"),
                ]
            ),
            
            # On cache le conteneur du Markdown pour ne pas afficher le code CSS
            html.Div(
                dcc.Markdown(id='dynamic-styles'),
                style={'display': 'none'}
            )
        ]
    )

def create_filter_column(label, element_id, element, width=2):
    """Crée une colonne de filtre réutilisable."""
    return html.Div(
        className=f"col-md-{width}",
        children=[
            html.Label(label, htmlFor=element_id, className="form-label fw-bold"),
            element
        ]
    )

def create_graph_card(title, graph_id):
    """Crée une carte réutilisable pour un graphique."""
    return html.Div(
        className="card shadow-sm mb-4",
        children=[
            html.Div(className="card-header", children=title),
            html.Div(className="card-body", children=dcc.Graph(id=graph_id, config={'displayModeBar': False}))
        ]
    )

def create_leaderboard_card(title, container_id):
    """Crée une carte réutilisable pour un classement."""
    return html.Div(
        className="col-lg-6",
        children=[
            html.Div(
                className="card shadow-sm h-100",
                children=[
                    html.Div(className="card-header", children=title),
                    html.Div(id=container_id, className="card-body p-0")
                ]
            )
        ]
    )

