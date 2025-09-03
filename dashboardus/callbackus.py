# dashboard/callbacks.py

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

def register_callbacks(app, df, user_id_to_name_map, role_colors_map):
    """
    Enregistre toutes les fonctions de callback pour le tableau de bord Dash.
    """
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
        selected_users, start_date, end_date, top_n, cumulative_clicks, monthly_clicks, hourly_clicks, cumulative_style, monthly_style, hourly_style
    ):
        ctx = dash.callback_context
        triggered_id = (ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None)

        if triggered_id == "toggle-cumulative":
            cumulative_style = {"display": "none"} if cumulative_style.get("display") != "none" else {"height": "50vh", "minHeight": "400px"}
        if triggered_id == "toggle-monthly":
            monthly_style = {"display": "none"} if monthly_style.get("display") != "none" else {"height": "50vh", "minHeight": "400px"}
        if triggered_id == "toggle-hourly":
            hourly_style = {"display": "none"} if hourly_style.get("display") != "none" else {"height": "50vh", "minHeight": "400px"}

        start_date_utc, end_date_utc = pd.to_datetime(start_date, utc=True), pd.to_datetime(end_date, utc=True)
        dff = df[(df["timestamp"] >= start_date_utc) & (df["timestamp"] <= end_date_utc)].copy()

        # SOLUTION : Créer les colonnes à l'intérieur de la callback
        dff["month_year"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.to_period("M").astype(str)
        dff["hour_of_day"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.hour

        # Logique de filtrage par le nombre de messages ou le Top N
        # On détermine si l'utilisateur a changé le Top N ou la sélection d'utilisateurs
        top_n_changed = triggered_id == "top-n-dropdown"
        user_dropdown_changed = triggered_id == "user-dropdown"

        if top_n_changed:
            # Si le Top N a changé, on applique la nouvelle sélection
            if top_n == "1000+":
                user_counts = dff["author_name"].value_counts()
                top_users = user_counts[user_counts >= 1000].index.tolist()
                user_options = [{"label": user, "value": user} for user in sorted(top_users)]
                user_value = top_users
            elif top_n != "all":
                top_users = dff["author_name"].value_counts().nlargest(top_n).index.tolist()
                user_options = [{"label": user, "value": user} for user in sorted(top_users)]
                user_value = top_users
            else: # top_n == "all"
                top_users = sorted(dff["author_name"].unique())
                user_options = [{"label": user, "value": user} for user in top_users]
                user_value = top_users

        elif user_dropdown_changed:
            # Si l'utilisateur a modifié la liste des pseudos, on respecte sa sélection
            top_users = sorted(dff["author_name"].unique())
            user_options = [{"label": user, "value": user} for user in top_users]
            user_value = selected_users

        else:
            # Sinon, on utilise la valeur par défaut du Top N
            if top_n == "1000+":
                user_counts = dff["author_name"].value_counts()
                top_users = user_counts[user_counts >= 1000].index.tolist()
                user_options = [{"label": user, "value": user} for user in sorted(top_users)]
                user_value = top_users
            elif top_n != "all":
                top_users = dff["author_name"].value_counts().nlargest(top_n).index.tolist()
                user_options = [{"label": user, "value": user} for user in sorted(top_users)]
                user_value = top_users
            else:
                top_users = sorted(dff["author_name"].unique())
                user_options = [{"label": user, "value": user} for user in top_users]
                user_value = selected_users if selected_users else top_users

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        if dff_filtered.empty:
            return {}, {}, {}, [], [], user_options, user_value, cumulative_style, monthly_style, hourly_style

        # Logique de couleurs (inchangée)
        color_map, colors_in_use = {}, {}
        default_color = "#666666"
        user_id_map = df.drop_duplicates(subset=["author_name"]).set_index("author_name")["author_id"].to_dict()

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
                users.sort(key=lambda u: dff_filtered["author_name"].value_counts().get(u, 0), reverse=True)
                for i in range(1, len(users)):
                    color_map[users[i]] = fallback_colors[fallback_idx % len(fallback_colors)]
                    fallback_idx += 1

        # Génération des graphiques (inchangée)
        fig_cumulative = create_cumulative_graph(dff_filtered, color_map)
        fig_monthly = create_monthly_graph(dff_filtered, color_map)
        fig_hourly = create_hourly_graph(dff_filtered, color_map)
        monthly_leaderboard_children = create_monthly_leaderboard(dff_filtered)
        daily_leaderboard_children = create_daily_leaderboard(dff_filtered)

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

def create_cumulative_graph(dff_filtered, color_map):
    """Crée le graphique cumulatif."""
    cumulative_data = dff_filtered.set_index("timestamp").groupby("author_name").resample("D").size().reset_index(name="daily_count")
    cumulative_data["cumulative_messages"] = cumulative_data.groupby("author_name")["daily_count"].cumsum()
    return px.line(
        cumulative_data,
        x="timestamp",
        y="cumulative_messages",
        color="author_name",
        color_discrete_map=color_map,
        title="Évolution du nombre total de messages envoyés",
        template="plotly",
    )

def create_monthly_graph(dff_filtered, color_map):
    """Crée le graphique mensuel."""
    monthly_counts = dff_filtered.groupby(["author_name", "month_year"]).size().reset_index(name="count")
    fig = px.line(
        monthly_counts,
        x="month_year",
        y="count",
        color="author_name",
        color_discrete_map=color_map,
        markers=True,
        title="Nombre de messages envoyés chaque mois",
        template="plotly",
    )
    fig.update_xaxes(categoryorder="category ascending")
    return fig

def create_hourly_graph(dff_filtered, color_map):
    """Crée le graphique horaire."""
    hourly_counts = dff_filtered.groupby(["author_name", "hour_of_day"]).size().reset_index(name="count")
    hourly_counts["total_per_user"] = hourly_counts.groupby("author_name")["count"].transform("sum")
    hourly_counts["percentage"] = (hourly_counts["count"] / hourly_counts["total_per_user"]) * 100
    fig = px.line(
        hourly_counts,
        x="hour_of_day",
        y="percentage",
        color="author_name",
        color_discrete_map=color_map,
        markers=True,
        title="Distribution des messages par heure de la journée (%)",
        labels={"hour_of_day": "Heure de la journée", "percentage": "Pourcentage de messages (%)"},
        template="plotly",
    )
    fig.update_layout(xaxis={"dtick": 1})
    return fig

def create_monthly_leaderboard(dff_filtered):
    """Crée le classement mensuel."""
    monthly_messages = dff_filtered.groupby([dff_filtered["timestamp"].dt.to_period("M"), "author_name"]).size().reset_index(name="count")
    if monthly_messages.empty:
        return [html.P("Pas assez de données pour le classement mensuel.")]
    monthly_winners = monthly_messages.loc[monthly_messages.groupby("timestamp")["count"].idxmax()]
    monthly_wins_df = monthly_winners.groupby("author_name")["timestamp"].agg(list).reset_index()
    monthly_wins_df["Mois gagnés"] = monthly_wins_df["timestamp"].apply(len)
    monthly_wins_df = monthly_wins_df.sort_values("Mois gagnés", ascending=False)
    monthly_wins_df["titre"] = monthly_wins_df["timestamp"].apply(lambda dates: ", ".join([d.strftime("%Y-%m") for d in dates]))
    
    return [
        html.P("Ce classement montre le nombre de fois où chaque utilisateur a été le champion du mois en termes de messages."),
        html.Ul(
            [
                html.Li(html.Span(f"{rank+1}. {row['author_name']} : {row['Mois gagnés']} mois gagnés", title=row["titre"]), style={"fontSize": "1.2em", "margin": "10px 0"})
                for rank, row in monthly_wins_df.iterrows()
            ],
            style={"listStyleType": "none", "padding": "0"},
        ),
    ]

def create_daily_leaderboard(dff_filtered):
    """Crée le classement journalier."""
    daily_messages = dff_filtered.groupby([dff_filtered["timestamp"].dt.date, "author_name"]).size().reset_index(name="count")
    if daily_messages.empty:
        return [html.P("Pas assez de données pour le classement journalier.")]
    daily_winners = daily_messages.loc[daily_messages.groupby("timestamp")["count"].idxmax()]
    daily_wins_df = daily_winners.groupby("author_name")["timestamp"].agg(list).reset_index()
    daily_wins_df["Jours gagnés"] = daily_wins_df["timestamp"].apply(len)
    daily_wins_df = daily_wins_df.sort_values("Jours gagnés", ascending=False)
    daily_wins_df["titre"] = daily_wins_df["timestamp"].apply(lambda dates: ", ".join([d.strftime("%Y-%m-%d") for d in dates]))

    return [
        html.P("Ce classement montre le nombre de fois où chaque utilisateur a été le champion du jour en termes de messages."),
        html.Ul(
            [
                html.Li(html.Span(f"{rank+1}. {row['author_name']} : {row['Jours gagnés']} jours gagnés", title=row["titre"]), style={"fontSize": "1.2em", "margin": "10px 0"})
                for rank, row in daily_wins_df.iterrows()
            ],
            style={"listStyleType": "none", "padding": "0"},
        ),
    ]