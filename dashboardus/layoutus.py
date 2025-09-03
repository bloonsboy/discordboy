# dashboard/layouts.py

from dash import dcc, html

def create_layout(df):
    """
    Crée le layout du tableau de bord Dash en utilisant les données du DataFrame.
    """
    
    # Assure que le DataFrame n'est pas vide avant de continuer
    if df.empty:
        return html.Div("Aucune donnée disponible pour créer le tableau de bord.")

    # Récupère les données nécessaires
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()
    sorted_users = sorted(df["author_name"].unique())

    # Retourne le layout principal
    return html.Div(
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
                style={
                    "textAlign": "center",
                    "marginBottom": "30px",
                    "paddingTop": "20px",
                },
            ),
            html.Div(
                style={
                    "position": "sticky",
                    "top": "0",
                    "backgroundColor": "#F4F4F9",
                    "padding": "15px 20px",
                    "zIndex": "1000",
                    "borderBottom": "1px solid #ccc",
                },
                children=[
                    html.Div(
                        className="controls",
                        style={
                            "display": "flex",
                            "gap": "20px",
                            "flexWrap": "wrap",
                            "justifyContent": "center",
                        },
                        children=[
                            html.Div(
                                children=[
                                    html.Label("Top N", style={"color": "#666", "marginBottom": "5px"}),
                                    dcc.Dropdown(
                                        id="top-n-dropdown",
                                        options=[
                                            {"label": "Top 5", "value": 5},
                                            {"label": "Top 10", "value": 10},
                                            {"label": "Top 20", "value": 20},
                                            {"label": ">= 1000 messages", "value": "1000+"},
                                            {"label": "Tous", "value": "all"},
                                        ],
                                        value=5,
                                        clearable=False,
                                    ),
                                ],
                                style={"flex": "1 1 100px", "minWidth": "100px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label("Utilisateurs", style={"color": "#666", "marginBottom": "5px"}),
                                    dcc.Dropdown(
                                        id="user-dropdown",
                                        options=[{"label": user, "value": user} for user in sorted_users],
                                        value=[],
                                        multi=True,
                                    ),
                                ],
                                style={"flex": "1 1 300px", "minWidth": "250px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label("Période", style={"color": "#666", "marginBottom": "5px"}),
                                    dcc.Dropdown(
                                        id="date-range-dropdown",
                                        options=[
                                            {"label": "Personnalisé", "value": "custom"},
                                            {"label": "Année en cours", "value": "current_year"},
                                            {"label": "Derniers 365 jours", "value": "last_365"},
                                            {"label": "Derniers 6 mois", "value": "last_6_months"},
                                        ],
                                        value="custom",
                                        clearable=False,
                                    ),
                                ],
                                style={"flex": "1 1 150px", "minWidth": "150px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label("Plage de dates", style={"color": "#666", "marginBottom": "5px"}),
                                    dcc.DatePickerRange(
                                        id="date-picker-range",
                                        min_date_allowed=min_date,
                                        max_date_allowed=max_date,
                                        start_date=min_date,
                                        end_date=max_date,
                                        display_format="DD/MM/YYYY",
                                    ),
                                ],
                                style={"flex": "1 1 300px", "minWidth": "250px"},
                            ),
                        ],
                    )
                ],
            ),
            html.Div(
                id="graphs-container",
                style={"padding": "20px"},
                children=[
                    create_graph_section("📈 Messages Cumulés au Fil du Temps (par jour)", "cumulative", "cumulative-graph"),
                    create_graph_section("📅 Messages par Mois", "monthly", "monthly-graph"),
                    create_graph_section("⏰ Distribution des messages par heure (%)", "hourly", "hourly-graph"),
                    html.Div(
                        style={"display": "flex", "flexDirection": "column", "gap": "20px", "marginTop": "40px"},
                        children=[
                            create_leaderboard_section("🏆 Champion mensuel du nombre de messages", "monthly-leaderboard-container"),
                            create_leaderboard_section("🏆 Champion journalier du nombre de messages", "daily-leaderboard-container"),
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
        className="graph-section",
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "gap": "10px"},
                children=[
                    html.H2(title, style={"textAlign": "center", "marginTop": "20px"}),
                    html.Button(
                        "Afficher/Masquer",
                        id=f"toggle-{id_prefix}",
                        n_clicks=0,
                        style={"fontSize": "0.8em", "padding": "5px 15px", "border": "1px solid #ccc", "borderRadius": "5px", "backgroundColor": "#fff", "cursor": "pointer", "transition": "background-color 0.3s ease", "&:hover": {"backgroundColor": "#e0e0e0"}},
                    ),
                ],
            ),
            dcc.Graph(id=graph_id, style={"height": "50vh", "minHeight": "400px"}),
        ],
    )

def create_leaderboard_section(title, container_id):
    """
    Crée une section de classement réutilisable.
    """
    return html.Div(
        style={"flex": "1 1 45%", "border": "1px solid #ddd", "borderRadius": "8px", "padding": "20px"},
        children=[
            html.H2(title, style={"textAlign": "center"}),
            html.Div(id=container_id, style={"textAlign": "center", "padding": "20px"}),
        ],
    )