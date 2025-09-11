# dashboardus/callbackus.py

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def register_callbacks(app, df, user_id_to_name_map, role_colors_map):
    """
    Enregistre toutes les fonctions de callback pour le tableau de bord Dash.
    """

    def is_light_color(hex_color):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
        return luminance > 0.5 # Seuil ajusté pour un meilleur contraste

    @app.callback(
        Output("date-picker-range", "start_date"),
        Output("date-picker-range", "end_date"),
        Input("date-range-dropdown", "value"),
        State("date-picker-range", "min_date_allowed"),
        State("date-picker-range", "max_date_allowed"),
    )
    def update_date_picker(selected_period, min_date, max_date):
        today = datetime.now()
        if not selected_period or selected_period == "custom":
            return dash.no_update, dash.no_update
        elif selected_period == "all-time":
            return min_date, max_date
        elif selected_period == "current_year":
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
        Output("date-range-display", "children"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
    )
    def display_date_range_duration(start_date, end_date):
        if not start_date or not end_date: return ""
        start = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
        end = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
        delta = end - start
        if delta.days < 365:
            return f"Durée : {delta.days} jours"
        else:
            years = delta.days // 365
            remaining_days = delta.days % 365
            return f"Durée : {years} an(s) et {remaining_days} jour(s)"

    @app.callback(
        Output("cumulative-graph", "figure"),
        Output("monthly-graph", "figure"),
        Output("hourly-graph", "figure"),
        Output("monthly-leaderboard-container", "children"),
        Output("daily-leaderboard-container", "children"),
        Output("user-dropdown", "options"),
        Output("user-dropdown", "value"),
        Output("dynamic-styles", "children"),
        Input("user-dropdown", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("top-n-dropdown", "value"),
    )
    def update_all(selected_users, start_date, end_date, top_n):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "date-picker-range"

        start_date_utc = pd.to_datetime(start_date, utc=True)
        end_date_utc = pd.to_datetime(end_date, utc=True).replace(hour=23, minute=59, second=59)
        dff = df[(df["timestamp"] >= start_date_utc) & (df["timestamp"] <= end_date_utc)].copy()

        dff["month_year"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.to_period("M").astype(str)
        dff["hour_of_day"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.hour

        user_counts_all_time = df["author_name"].value_counts()
        sorted_users_by_count = user_counts_all_time.index.tolist()

        user_value = selected_users
        if triggered_id == "top-n-dropdown":
            if top_n == "1000+":
                user_value = user_counts_all_time[user_counts_all_time >= 1000].index.tolist()
            elif top_n != "custom":
                user_value = user_counts_all_time.nlargest(int(top_n)).index.tolist()

        user_id_map = df.drop_duplicates(subset=["author_name"]).set_index("author_name")["author_id"].to_dict()
        user_options = []
        for user in sorted_users_by_count:
            user_id = str(user_id_map.get(user, ""))
            color = role_colors_map.get(user_id, "#6c757d")
            text_style = {"color": color, "fontWeight": "bold", "textShadow": "1px 1px 2px rgba(0,0,0,0.2)" if is_light_color(color) else "none"}
            user_options.append({"label": html.Span(user, style=text_style), "value": user})

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        # --- Génération des styles CSS dynamiques pour les sélections d'utilisateurs ---
        dynamic_style_rules = ""
        if user_value:
            for user in user_value:
                user_id = str(user_id_map.get(user, ""))
                bg_color = role_colors_map.get(user_id, "#6c757d")
                text_color = "#FFFFFF" if not is_light_color(bg_color) else "#000000"
                user_selector = user.replace('"', '\\"')
                dynamic_style_rules += f""".Select-value[title="{user_selector}"] {{
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                    border-radius: 4px;
                }}"""

        empty_figure = go.Figure(layout={"template": "plotly_white"}).update_layout(
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Pas de données à afficher", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 16}}]
        )
        empty_leaderboard = html.P("Pas de données pour cette période.", className="text-center text-muted p-4")

        if dff_filtered.empty:
            return empty_figure, empty_figure, empty_figure, empty_leaderboard, empty_leaderboard, user_options, user_value, dynamic_style_rules

        color_map = {user: role_colors_map.get(str(user_id_map.get(user)), "#6c757d") for user in user_value}
        
        fig_cumulative = create_cumulative_graph(dff_filtered, color_map)
        fig_monthly = create_monthly_graph(dff_filtered, color_map)
        fig_hourly = create_hourly_graph(dff_filtered, color_map)
        monthly_leaderboard = create_leaderboard(dff_filtered, 'M', "Mois gagnés", "%B %Y")
        daily_leaderboard = create_leaderboard(dff_filtered, 'D', "Jours gagnés", "%d %B %Y")

        return fig_cumulative, fig_monthly, fig_hourly, monthly_leaderboard, daily_leaderboard, user_options, user_value, dynamic_style_rules

def create_base_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "x": 0.5, "font": {"size": 18}},
        template="plotly_white",
        legend={"title": "Utilisateurs"},
        margin=dict(l=40, r=40, t=60, b=40),
        font=dict(family="Inter, sans-serif")
    )
    return fig

def create_cumulative_graph(dff_filtered, color_map):
    fig = create_base_figure(None)
    cumulative_data = dff_filtered.set_index("timestamp").groupby("author_name").resample("D").size().reset_index(name="daily_count")
    cumulative_data["cumulative_messages"] = cumulative_data.groupby("author_name")["daily_count"].cumsum()
    return px.line(
        cumulative_data, x="timestamp", y="cumulative_messages", color="author_name",
        color_discrete_map=color_map, template="plotly_white",
        labels={"timestamp": "Date", "cumulative_messages": "Messages cumulés"}
    ).update_layout(legend={"title": "Utilisateurs"})

def create_monthly_graph(dff_filtered, color_map):
    monthly_counts = dff_filtered.groupby(["author_name", "month_year"]).size().reset_index(name="count")
    fig = px.line(
        monthly_counts, x="month_year", y="count", color="author_name",
        color_discrete_map=color_map, markers=True, template="plotly_white",
        labels={"month_year": "Mois", "count": "Nombre de messages"}
    )
    fig.update_xaxes(categoryorder="category ascending")
    return fig.update_layout(legend={"title": "Utilisateurs"})

def create_hourly_graph(dff_filtered, color_map):
    hourly_counts = dff_filtered.groupby(["author_name", "hour_of_day"]).size().reset_index(name="count")
    hourly_counts["total_per_user"] = hourly_counts.groupby("author_name")["count"].transform("sum")
    hourly_counts["percentage"] = (hourly_counts["count"] / hourly_counts["total_per_user"]) * 100
    fig = px.line(
        hourly_counts, x="hour_of_day", y="percentage", color="author_name",
        color_discrete_map=color_map, markers=True, template="plotly_white",
        labels={"hour_of_day": "Heure de la journée", "percentage": "Pourcentage de messages (%)"},
    )
    return fig.update_layout(xaxis={"dtick": 1}, legend={"title": "Utilisateurs"})

def create_leaderboard(dff, period, metric_name, date_format):
    resampled = dff.groupby([dff["timestamp"].dt.to_period(period), "author_name"]).size().reset_index(name="count")
    if resampled.empty:
        return html.P("Pas assez de données pour ce classement.", className="text-center p-3")
    
    winners = resampled.loc[resampled.groupby("timestamp")["count"].idxmax()]
    wins_df = winners.groupby("author_name")["timestamp"].agg(list).reset_index()
    wins_df[metric_name] = wins_df["timestamp"].apply(len)
    wins_df = wins_df.sort_values(metric_name, ascending=False).head(10)
    
    items = []
    for i, row in wins_df.iterrows():
        rank = len(items) + 1
        tooltip_text = ", ".join([d.strftime(date_format) for d in row["timestamp"]])
        item = html.Li(
            className="list-group-item d-flex justify-content-between align-items-center leaderboard-item",
            title=tooltip_text,
            children=[
                html.Div([
                    html.Span(f"{rank}.", className="leaderboard-rank"),
                    html.Span(row['author_name']),
                ]),
                html.Span(f"{row[metric_name]}", className="badge rounded-pill"),
            ]
        )
        items.append(item)

    return html.Ul(items, className="list-group list-group-flush")

