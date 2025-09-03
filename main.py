import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta

import dash
import discord
import pandas as pd
import plotly.express as px
import pyarrow
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dotenv import load_dotenv

# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Chargement et Configuration ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CACHE_FILENAME = "discord_messages_cache.parquet"
ROLE_COLORS_FILENAME = "role_colors.json"

# ==============================================================================
#  CONFIGURATION DES DONNÉES
# ==============================================================================
IDS_TO_EXCLUDE = [456226577798135808]
ID_MERGE_MAP = {"183303146955735040": "lupoticha"}
NAME_MERGE_MAP = {"iwantdog": ".redhot_"}
# ==============================================================================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
user_id_to_name_map = {}


async def fetch_and_save_role_colors(guild):
    logging.info("Récupération des couleurs de rôle...")
    role_colors = {}
    await guild.chunk()
    for member in guild.members:
        if not member.bot:
            color = str(member.color)
            if color != "#000000":
                role_colors[str(member.id)] = color
    with open(ROLE_COLORS_FILENAME, "w") as f:
        json.dump(role_colors, f, indent=4)
    logging.info(f"Couleurs de rôle sauvegardées.")


async def fetch_channel_messages_as_df(channel, after_date=None):
    messages = []
    if "mudae" in channel.name.lower() or "log" in channel.name.lower():
        return pd.DataFrame()
    log_message = f"[DÉBUT] Récupération de #{channel.name}"
    if after_date:
        log_message += f" (après le {after_date.strftime('%Y-%m-%d %H:%M')})"
    logging.info(log_message)
    start_time = time.time()
    try:
        async for message in channel.history(limit=None, after=after_date):
            if not message.author.bot:
                messages.append(
                    {
                        "timestamp": message.created_at,
                        "author_id": message.author.id,
                        "author_name": str(message.author),
                        "channel_id": channel.id,
                    }
                )
        return pd.DataFrame(messages)
    except Exception as e:
        logging.error(f"Erreur dans #{channel.name}: {e}")
        return pd.DataFrame()


async def fetch_messages_with_cache(guild):
    global user_id_to_name_map
    df_cache = pd.DataFrame()
    latest_timestamps = {}
    if os.path.exists(CACHE_FILENAME):
        df_cache = pd.read_parquet(CACHE_FILENAME)
        df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"])
        if not df_cache.empty:
            df_known_users = df_cache[
                df_cache["author_name"] != "Deleted User#0000"
            ].drop_duplicates(subset=["author_id"], keep="last")
            user_id_to_name_map = pd.Series(
                df_known_users.author_name.values, index=df_known_users.author_id
            ).to_dict()
            latest_timestamps = (
                df_cache.loc[df_cache.groupby("channel_id")["timestamp"].idxmax()]
                .set_index("channel_id")["timestamp"]
                .to_dict()
            )

    tasks = [
        asyncio.create_task(
            fetch_channel_messages_as_df(c, after_date=latest_timestamps.get(c.id))
        )
        for c in guild.text_channels
        if c.permissions_for(guild.me).read_message_history
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    new_dfs = [
        res for res in results if isinstance(res, pd.DataFrame) and not res.empty
    ]
    df_new = pd.concat(new_dfs, ignore_index=True) if new_dfs else pd.DataFrame()
    if not df_new.empty:
        df_new_known = df_new[
            df_new["author_name"] != "Deleted User#0000"
        ].drop_duplicates(subset=["author_id"], keep="last")
        user_id_to_name_map.update(
            pd.Series(
                df_new_known.author_name.values, index=df_new_known.author_id
            ).to_dict()
        )

    final_df = pd.concat([df_cache, df_new], ignore_index=True)
    final_df = final_df[~final_df["author_id"].isin(IDS_TO_EXCLUDE)]
    final_df.to_parquet(CACHE_FILENAME)

    final_df["author_name"] = final_df["author_id"].map(user_id_to_name_map)
    unknown_mask = final_df["author_name"].isnull()
    final_df.loc[unknown_mask, "author_name"] = "ID: " + final_df.loc[
        unknown_mask, "author_id"
    ].astype(str)

    if ID_MERGE_MAP:
        for old_id, new_name in ID_MERGE_MAP.items():
            final_df.loc[final_df["author_id"] == int(old_id), "author_name"] = new_name

    if NAME_MERGE_MAP:
        for old_name, new_name in NAME_MERGE_MAP.items():
            final_df.loc[final_df["author_name"] == old_name, "author_name"] = new_name

    return final_df.drop(columns=["channel_id"], errors="ignore")


def process_and_save_stats(df):
    if df.empty:
        return pd.DataFrame()
    df_copy = df.copy()
    df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"])
    df_copy["year"] = df_copy["timestamp"].dt.year
    yearly_counts = (
        df_copy.groupby(["author_name", "year"]).size().unstack(fill_value=0)
    )
    yearly_counts["total_messages"] = yearly_counts.sum(axis=1)
    final_csv_df = yearly_counts.reset_index().sort_values(
        "total_messages", ascending=False
    )
    count_cols = [col for col in final_csv_df.columns if col not in ["author_name"]]
    final_csv_df[count_cols] = final_csv_df[count_cols].astype(int)
    final_csv_df.to_csv("discord_server_stats.csv", index=False)
    return df


def create_and_run_dashboard(df):
    if df.empty:
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["month_year"] = df["timestamp"].dt.to_period("M").astype(str)
    df["hour_of_day"] = df["timestamp"].dt.hour

    if os.path.exists(ROLE_COLORS_FILENAME):
        with open(ROLE_COLORS_FILENAME, "r") as f:
            role_colors_map = json.load(f)
    else:
        role_colors_map = {}

    user_message_counts = df["author_name"].value_counts().to_dict()
    user_id_map = (
        df.drop_duplicates(subset=["author_name"])
        .set_index("author_name")["author_id"]
        .to_dict()
    )

    app = dash.Dash(__name__, title="Statistiques Discord")
    app.layout = html.Div(
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
                                    html.Label(
                                        "Top N",
                                        style={"color": "#666", "marginBottom": "5px"},
                                    ),
                                    dcc.Dropdown(
                                        id="top-n-dropdown",
                                        options=[
                                            {"label": "Top 5", "value": 5},
                                            {"label": "Top 10", "value": 10},
                                            {"label": "Top 20", "value": 20},
                                            {
                                                "label": ">= 1000 messages",
                                                "value": "1000+",
                                            },
                                            {"label": "Tous", "value": "all"},
                                        ],
                                        value=5,
                                        clearable=False,
                                        style={
                                            "backgroundColor": "#fff",
                                            "color": "#333",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
                                    ),
                                ],
                                style={"flex": "1 1 100px", "minWidth": "100px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label(
                                        "Utilisateurs",
                                        style={"color": "#666", "marginBottom": "5px"},
                                    ),
                                    dcc.Dropdown(
                                        id="user-dropdown",
                                        options=[
                                            {"label": user, "value": user}
                                            for user in sorted(
                                                df["author_name"].unique()
                                            )
                                        ],
                                        value=[],
                                        multi=True,
                                        style={
                                            "backgroundColor": "#fff",
                                            "color": "#333",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
                                    ),
                                ],
                                style={"flex": "1 1 300px", "minWidth": "250px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label(
                                        "Période",
                                        style={"color": "#666", "marginBottom": "5px"},
                                    ),
                                    dcc.Dropdown(
                                        id="date-range-dropdown",
                                        options=[
                                            {
                                                "label": "Personnalisé",
                                                "value": "custom",
                                            },
                                            {
                                                "label": "Année en cours",
                                                "value": "current_year",
                                            },
                                            {
                                                "label": "Derniers 365 jours",
                                                "value": "last_365",
                                            },
                                            {
                                                "label": "Derniers 6 mois",
                                                "value": "last_6_months",
                                            },
                                        ],
                                        value="custom",
                                        clearable=False,
                                        style={
                                            "backgroundColor": "#fff",
                                            "color": "#333",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
                                    ),
                                ],
                                style={"flex": "1 1 150px", "minWidth": "150px"},
                            ),
                            html.Div(
                                children=[
                                    html.Label(
                                        "Plage de dates",
                                        style={"color": "#666", "marginBottom": "5px"},
                                    ),
                                    dcc.DatePickerRange(
                                        id="date-picker-range",
                                        min_date_allowed=df["timestamp"].min().date(),
                                        max_date_allowed=df["timestamp"].max().date(),
                                        start_date=df["timestamp"].min().date(),
                                        end_date=df["timestamp"].max().date(),
                                        display_format="DD/MM/YYYY",
                                        style={
                                            "backgroundColor": "#fff",
                                            "color": "#333",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                        },
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
                    # Graphique 1
                    html.Div(
                        className="graph-section",
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "gap": "10px",
                                },
                                children=[
                                    html.H2(
                                        "📈 Messages Cumulés au Fil du Temps (par jour)",
                                        style={
                                            "textAlign": "center",
                                            "marginTop": "20px",
                                        },
                                    ),
                                    html.Button(
                                        "Afficher/Masquer",
                                        id="toggle-cumulative",
                                        n_clicks=0,
                                        style={
                                            "fontSize": "0.8em",
                                            "padding": "5px 15px",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                            "backgroundColor": "#fff",
                                            "cursor": "pointer",
                                            "transition": "background-color 0.3s ease",
                                            "&:hover": {"backgroundColor": "#e0e0e0"},
                                        },
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="cumulative-graph",
                                style={"height": "50vh", "minHeight": "400px"},
                            ),
                        ],
                    ),
                    # Graphique 2
                    html.Div(
                        className="graph-section",
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "gap": "10px",
                                },
                                children=[
                                    html.H2(
                                        "📅 Messages par Mois",
                                        style={
                                            "textAlign": "center",
                                            "marginTop": "20px",
                                        },
                                    ),
                                    html.Button(
                                        "Afficher/Masquer",
                                        id="toggle-monthly",
                                        n_clicks=0,
                                        style={
                                            "fontSize": "0.8em",
                                            "padding": "5px 15px",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                            "backgroundColor": "#fff",
                                            "cursor": "pointer",
                                            "transition": "background-color 0.3s ease",
                                            "&:hover": {"backgroundColor": "#e0e0e0"},
                                        },
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="monthly-graph",
                                style={"height": "50vh", "minHeight": "400px"},
                            ),
                        ],
                    ),
                    # Graphique 3
                    html.Div(
                        className="graph-section",
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "gap": "10px",
                                },
                                children=[
                                    html.H2(
                                        "⏰ Distribution des messages par heure (%)",
                                        style={
                                            "textAlign": "center",
                                            "marginTop": "20px",
                                        },
                                    ),
                                    html.Button(
                                        "Afficher/Masquer",
                                        id="toggle-hourly",
                                        n_clicks=0,
                                        style={
                                            "fontSize": "0.8em",
                                            "padding": "5px 15px",
                                            "border": "1px solid #ccc",
                                            "borderRadius": "5px",
                                            "backgroundColor": "#fff",
                                            "cursor": "pointer",
                                            "transition": "background-color 0.3s ease",
                                            "&:hover": {"backgroundColor": "#e0e0e0"},
                                        },
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="hourly-graph",
                                style={"height": "50vh", "minHeight": "400px"},
                            ),
                        ],
                    ),
                    # Conteneur pour les classements
                    html.Div(
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "gap": "20px",
                            "marginTop": "40px",
                        },
                        children=[
                            # Classement mensuel
                            html.Div(
                                style={
                                    "flex": "1 1 45%",
                                    "border": "1px solid #ddd",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                },
                                children=[
                                    html.H2(
                                        "🏆 Champion mensuel du nombre de messages",
                                        style={"textAlign": "center"},
                                    ),
                                    html.Div(
                                        id="monthly-leaderboard-container",
                                        style={
                                            "textAlign": "center",
                                            "padding": "20px",
                                        },
                                    ),
                                ],
                            ),
                            # Classement journalier
                            html.Div(
                                style={
                                    "flex": "1 1 45%",
                                    "border": "1px solid #ddd",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                },
                                children=[
                                    html.H2(
                                        "🏆 Champion journalier du nombre de messages",
                                        style={"textAlign": "center"},
                                    ),
                                    html.Div(
                                        id="daily-leaderboard-container",
                                        style={
                                            "textAlign": "center",
                                            "padding": "20px",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("date-picker-range", "start_date"),
        Output("date-picker-range", "end_date"),
        Input("date-range-dropdown", "value"),
    )
    def update_date_picker(selected_period):
        today = datetime.now()
        if selected_period == "current_year":
            start_date = today.replace(month=1, day=1)
            return start_date.date(), today.date()
        elif selected_period == "last_365":
            start_date = today - timedelta(days=365)
            return start_date.date(), today.date()
        elif selected_period == "last_6_months":
            start_date = today - timedelta(days=180)
            return start_date.date(), today.date()
        return dash.no_update, dash.no_update

    @app.callback(
        [
            Output("cumulative-graph", "figure"),
            Output("monthly-graph", "figure"),
            Output("hourly-graph", "figure"),
            Output("monthly-leaderboard-container", "children"),
            Output("daily-leaderboard-container", "children"),
            Output("user-dropdown", "options"),
            Output("user-dropdown", "value"),
            Output("cumulative-graph", "style"),
            Output("monthly-graph", "style"),
            Output("hourly-graph", "style"),
        ],
        [
            Input("user-dropdown", "value"),
            Input("date-picker-range", "start_date"),
            Input("date-picker-range", "end_date"),
            Input("top-n-dropdown", "value"),
            Input("toggle-cumulative", "n_clicks"),
            Input("toggle-monthly", "n_clicks"),
            Input("toggle-hourly", "n_clicks"),
        ],
        [
            State("cumulative-graph", "style"),
            State("monthly-graph", "style"),
            State("hourly-graph", "style"),
        ],
    )
    def update_graphs(
        selected_users,
        start_date,
        end_date,
        top_n,
        cumulative_clicks,
        monthly_clicks,
        hourly_clicks,
        cumulative_style,
        monthly_style,
        hourly_style,
    ):
        ctx = dash.callback_context
        triggered_id = (
            ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        )

        if triggered_id == "toggle-cumulative":
            cumulative_style = (
                {"display": "none"}
                if cumulative_style.get("display") != "none"
                else {"height": "50vh", "minHeight": "400px"}
            )
        if triggered_id == "toggle-monthly":
            monthly_style = (
                {"display": "none"}
                if monthly_style.get("display") != "none"
                else {"height": "50vh", "minHeight": "400px"}
            )
        if triggered_id == "toggle-hourly":
            hourly_style = (
                {"display": "none"}
                if hourly_style.get("display") != "none"
                else {"height": "50vh", "minHeight": "400px"}
            )

        start_date_utc, end_date_utc = pd.to_datetime(
            start_date, utc=True
        ), pd.to_datetime(end_date, utc=True)
        dff = df[
            (df["timestamp"] >= start_date_utc) & (df["timestamp"] <= end_date_utc)
        ]

        # Logique de filtrage par le nombre de messages ou le Top N
        if top_n == "1000+":
            user_counts = dff["author_name"].value_counts()
            top_users = user_counts[user_counts >= 1000].index.tolist()
            dff = dff[dff["author_name"].isin(top_users)]
            user_options = [
                {"label": user, "value": user}
                for user in sorted(dff["author_name"].unique())
            ]
            user_value = top_users
        elif top_n != "all":
            top_users = dff["author_name"].value_counts().nlargest(top_n).index.tolist()
            dff = dff[dff["author_name"].isin(top_users)]
            user_options = [
                {"label": user, "value": user}
                for user in sorted(dff["author_name"].unique())
            ]
            user_value = top_users
        else:
            top_users = sorted(dff["author_name"].unique())
            user_options = [{"label": user, "value": user} for user in top_users]
            user_value = selected_users if selected_users else top_users

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        if dff_filtered.empty:
            return (
                {},
                {},
                {},
                [],
                [],
                user_options,
                user_value,
                cumulative_style,
                monthly_style,
                hourly_style,
            )

        color_map, colors_in_use = {}, {}
        default_color = "#666666"

        for user in user_value:
            user_id = str(user_id_map.get(user, ""))
            color = role_colors_map.get(user_id, default_color)
            color_map[user] = color
            if color not in colors_in_use:
                colors_in_use[color] = []
            colors_in_use[color].append(user)
        fallback_colors, fallback_idx = px.colors.qualitative.Plotly, 0
        for color, users in colors_in_use.items():
            if len(users) > 1:
                users.sort(
                    key=lambda u: dff_filtered["author_name"].value_counts().get(u, 0),
                    reverse=True,
                )
                for i in range(1, len(users)):
                    color_map[users[i]] = fallback_colors[
                        fallback_idx % len(fallback_colors)
                    ]
                    fallback_idx += 1

        cumulative_data = (
            dff_filtered.set_index("timestamp")
            .groupby("author_name")
            .resample("D")
            .size()
            .reset_index(name="daily_count")
        )
        cumulative_data["cumulative_messages"] = cumulative_data.groupby("author_name")[
            "daily_count"
        ].cumsum()

        template = "plotly"

        fig_cumulative = px.line(
            cumulative_data,
            x="timestamp",
            y="cumulative_messages",
            color="author_name",
            color_discrete_map=color_map,
            title="Évolution du nombre total de messages envoyés",
            template=template,
        )

        monthly_counts = (
            dff_filtered.groupby(["author_name", "month_year"])
            .size()
            .reset_index(name="count")
        )
        fig_monthly = px.line(
            monthly_counts,
            x="month_year",
            y="count",
            color="author_name",
            color_discrete_map=color_map,
            markers=True,
            title="Nombre de messages envoyés chaque mois",
            template=template,
        )
        fig_monthly.update_xaxes(categoryorder="category ascending")

        hourly_counts = (
            dff_filtered.groupby(["author_name", "hour_of_day"])
            .size()
            .reset_index(name="count")
        )
        hourly_counts["total_per_user"] = hourly_counts.groupby("author_name")[
            "count"
        ].transform("sum")
        hourly_counts["percentage"] = (
            hourly_counts["count"] / hourly_counts["total_per_user"]
        ) * 100

        fig_hourly = px.line(
            hourly_counts,
            x="hour_of_day",
            y="percentage",
            color="author_name",
            color_discrete_map=color_map,
            markers=True,
            title="Distribution des messages par heure de la journée (%)",
            labels={
                "hour_of_day": "Heure de la journée",
                "percentage": "Pourcentage de messages (%)",
            },
            template=template,
        )
        fig_hourly.update_layout(xaxis={"dtick": 1})

        # Logique pour le classement mensuel
        monthly_messages = (
            dff_filtered.groupby(
                [dff_filtered["timestamp"].dt.to_period("M"), "author_name"]
            )
            .size()
            .reset_index(name="count")
        )
        if not monthly_messages.empty:
            monthly_winners = monthly_messages.loc[
                monthly_messages.groupby("timestamp")["count"].idxmax()
            ]
            # Créer un DataFrame pour les dates gagnantes et les comptes
            monthly_wins_df = (
                monthly_winners.groupby("author_name")["timestamp"]
                .agg(list)
                .reset_index()
            )
            monthly_wins_df["Mois gagnés"] = monthly_wins_df["timestamp"].apply(len)
            monthly_wins_df = monthly_wins_df.sort_values(
                "Mois gagnés", ascending=False
            )

            # Formater les dates pour le survol
            monthly_wins_df["titre"] = monthly_wins_df["timestamp"].apply(
                lambda dates: ", ".join([d.strftime("%Y-%m") for d in dates])
            )

            monthly_leaderboard_children = [
                html.P(
                    "Ce classement montre le nombre de fois où chaque utilisateur a été le champion du mois en termes de messages."
                ),
                html.Ul(
                    [
                        html.Li(
                            html.Span(
                                f"{rank+1}. {row['author_name']} : {row['Mois gagnés']} mois gagnés",
                                title=row["titre"],
                            ),
                            style={"fontSize": "1.2em", "margin": "10px 0"},
                        )
                        for rank, row in monthly_wins_df.iterrows()
                    ],
                    style={"listStyleType": "none", "padding": "0"},
                ),
            ]
        else:
            monthly_leaderboard_children = [
                html.P("Pas assez de données pour le classement mensuel.")
            ]

        # Logique pour le classement journalier
        daily_messages = (
            dff_filtered.groupby([dff_filtered["timestamp"].dt.date, "author_name"])
            .size()
            .reset_index(name="count")
        )
        if not daily_messages.empty:
            daily_winners = daily_messages.loc[
                daily_messages.groupby("timestamp")["count"].idxmax()
            ]
            # Créer un DataFrame pour les dates gagnantes et les comptes
            daily_wins_df = (
                daily_winners.groupby("author_name")["timestamp"]
                .agg(list)
                .reset_index()
            )
            daily_wins_df["Jours gagnés"] = daily_wins_df["timestamp"].apply(len)
            daily_wins_df = daily_wins_df.sort_values("Jours gagnés", ascending=False)

            # Formater les dates pour le survol
            daily_wins_df["titre"] = daily_wins_df["timestamp"].apply(
                lambda dates: ", ".join([d.strftime("%Y-%m-%d") for d in dates])
            )

            daily_leaderboard_children = [
                html.P(
                    "Ce classement montre le nombre de fois où chaque utilisateur a été le champion du jour en termes de messages."
                ),
                html.Ul(
                    [
                        html.Li(
                            html.Span(
                                f"{rank+1}. {row['author_name']} : {row['Jours gagnés']} jours gagnés",
                                title=row["titre"],
                            ),
                            style={"fontSize": "1.2em", "margin": "10px 0"},
                        )
                        for rank, row in daily_wins_df.iterrows()
                    ],
                    style={"listStyleType": "none", "padding": "0"},
                ),
            ]
        else:
            daily_leaderboard_children = [
                html.P("Pas assez de données pour le classement journalier.")
            ]

        return (
            fig_cumulative,
            fig_monthly,
            fig_hourly,
            monthly_leaderboard_children,
            daily_leaderboard_children,
            user_options,
            user_value,
            cumulative_style,
            monthly_style,
            hourly_style,
        )

    logging.info(f"Lancement du serveur web Dash sur http://<VOTRE_IP>:8050/")
    app.run(host="0.0.0.0", port=8050, debug=False)


@client.event
async def on_ready():
    logging.info(f"{client.user} s'est connecté à Discord !")
    if not client.guilds:
        await client.close()
        return
    guild = client.guilds[0]
    await fetch_and_save_role_colors(guild)
    main_df = await fetch_messages_with_cache(guild)
    dashboard_df = process_and_save_stats(main_df)
    logging.info("La collecte de données est terminée. Fermeture du client Discord.")
    await client.close()
    if not dashboard_df.empty:
        create_and_run_dashboard(dashboard_df)
    else:
        logging.info("Aucune donnée à afficher.")


if __name__ == "__main__":
    if DISCORD_TOKEN:
        client.run(DISCORD_TOKEN)
    else:
        logging.error("Le DISCORD_TOKEN n'est pas défini !")
