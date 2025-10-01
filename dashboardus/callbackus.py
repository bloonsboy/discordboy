# dashboardus/callbackus.py

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def register_callbacks(app, df, role_colors_map, current_member_ids):
    def is_light_color(hex_color):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
        return luminance > 0.5

    @app.callback(
        Output("date-picker-range", "start_date"),
        Output("date-picker-range", "end_date"),
        Input("date-range-dropdown", "value"),
        State("date-picker-range", "min_date_allowed"),
        State("date-picker-range", "max_date_allowed"),
    )
    def update_date_picker(selected_period, min_date, max_date):
        today = datetime.now()
        if not selected_period or selected_period == "custom": return dash.no_update, dash.no_update
        elif selected_period == "all-time": return min_date, max_date
        elif selected_period == "current_year": return today.replace(month=1, day=1).date(), today.date()
        elif selected_period == "last_365": return (today - timedelta(days=365)).date(), today.date()
        elif selected_period == "last_6_months": return (today - timedelta(days=180)).date(), today.date()
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
        years, days = divmod(delta.days, 365)
        return f"Durée : {years} an(s) et {days} jour(s)" if years > 0 else f"Durée : {delta.days} jours"

    @app.callback(
        Output("cumulative-graph", "figure"), Output("monthly-graph", "figure"),
        Output("hourly-graph", "figure"), Output("monthly-leaderboard-container", "children"),
        Output("daily-leaderboard-container", "children"), Output("user-dropdown", "options"),
        Output("user-dropdown", "value"), Output("dynamic-styles", "children"),
        Output("weekday-graph", "figure"), Output("user-profile-card-container", "children"),
        Input("user-dropdown", "value"), Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"), Input("top-n-dropdown", "value"),
        Input("metric-selector", "value"),
    )
    def update_all(selected_users, start_date, end_date, top_n, metric_selected):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "date-picker-range"

        start_date_utc = pd.to_datetime(start_date, utc=True)
        end_date_utc = pd.to_datetime(end_date, utc=True).replace(hour=23, minute=59, second=59)
        dff = df[(df["timestamp"] >= start_date_utc) & (df["timestamp"] <= end_date_utc)].copy()
        
        dff["month_year"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.to_period("M").astype(str)
        dff["hour_of_day"] = dff["timestamp"].dt.tz_convert('Europe/Paris').dt.hour
        dff["weekday"] = dff["timestamp"].dt.day_name()

        if metric_selected == 'characters':
            user_counts_period = dff.groupby("author_name")['character_count'].sum().sort_values(ascending=False)
        else:
            user_counts_period = dff["author_name"].value_counts()

        user_counts_all_time = df["author_name"].value_counts()
        sorted_users_by_count = user_counts_all_time.index.tolist()

        user_value = selected_users
        if triggered_id != "user-dropdown":
            if top_n == "1000+":
                top_users_period = user_counts_period[user_counts_period >= 1000].index
                user_value = list(top_users_period)
            elif top_n != "custom":
                user_value = user_counts_period.nlargest(int(top_n)).index.tolist()

        user_id_map = df.drop_duplicates(subset=["author_name"]).set_index("author_name")["author_id"].to_dict()
        name_to_original_map = df.drop_duplicates(subset=["author_name"]).set_index("author_name")["original_author_name"].to_dict()

        user_options = [
            {
                "label": html.Div([
                    html.Span(user, style={
                        "color": "#6c757d" if user_id_map.get(user) not in current_member_ids else role_colors_map.get(str(user_id_map.get(user)), "#6c757d"),
                        "textDecoration": "line-through" if user_id_map.get(user) not in current_member_ids else "none",
                        "fontWeight": "bold",
                    }),
                    html.Span(name_to_original_map.get(user, user), style={'display': 'none'})
                ]),
                "value": user
            } for user in sorted_users_by_count
        ]
        
        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        server_hourly_counts = pd.DataFrame()
        if not dff.empty:
            agg_col = 'character_count' if metric_selected == 'characters' else 'author_id'
            agg_func = 'sum' if metric_selected == 'characters' else 'count'
            server_hourly_counts = dff.groupby("hour_of_day")[agg_col].agg(agg_func).reset_index()
            server_hourly_counts.rename(columns={agg_col: 'value'}, inplace=True)
            total_value_period = server_hourly_counts["value"].sum()
            server_hourly_counts["percentage"] = (server_hourly_counts["value"] / total_value_period) * 100 if total_value_period > 0 else 0
        
        style_rules = []
        for user in user_value:
            safe_user = user.replace('"', '\\"')
            user_id = user_id_map.get(user, "")
            is_member = user_id in current_member_ids

            bg_color = role_colors_map.get(str(user_id), "#6c757d") if is_member else "#f8f9fa"
            text_color = ("#000000" if is_light_color(bg_color) else "#FFFFFF") if is_member else "#6c757d"
            decoration = "none" if is_member else "line-through"

            rule = f""".Select-value[title="{safe_user}"] {{
                background-color: {bg_color} !important;
                color: {text_color} !important;
                border-radius: 4px;
                text-decoration: {decoration};
            }}"""
            style_rules.append(rule)
        
        final_styles = f"<style>{''.join(style_rules)}</style>"

        profile_card = []
        if len(user_value) == 1:
            profile_card = create_user_profile_card(user_value[0], dff, user_counts_period, metric_selected)
        
        empty_figure = go.Figure(layout={"template": "plotly_white", "annotations": [{"text": "Pas de données", "showarrow": False}]})
        empty_leaderboard = html.P("No data available for this period.", className="text-center text-muted p-4")

        if dff_filtered.empty:
            return empty_figure, empty_figure, create_hourly_graph(dff_filtered, {}, server_hourly_counts, metric_selected), empty_leaderboard, empty_leaderboard, user_options, user_value, final_styles, empty_figure, profile_card

        color_map = {user: role_colors_map.get(str(user_id_map.get(user)), "#6c757d") for user in user_value}
        
        fig_cumulative = create_cumulative_graph(dff_filtered, color_map, metric_selected)
        fig_monthly = create_monthly_graph(dff_filtered, color_map, metric_selected)
        fig_hourly = create_hourly_graph(dff_filtered, color_map, server_hourly_counts, metric_selected)
        monthly_leaderboard = create_leaderboard(dff_filtered, 'M', "Mois gagnés", "%B %Y", metric_selected)
        daily_leaderboard = create_leaderboard(dff_filtered, 'D', "Jours gagnés", "%d %B %Y", metric_selected)
        fig_weekday = create_weekday_graph(dff_filtered, metric_selected)

        return fig_cumulative, fig_monthly, fig_hourly, monthly_leaderboard, daily_leaderboard, user_options, user_value, final_styles, fig_weekday, profile_card

    def create_user_profile_card(user_name, dff, user_counts_period, metric_selected):
        user_df = dff[dff["author_name"] == user_name]
        if user_df.empty: return []
        
        if metric_selected == 'characters':
            total_val = user_df['character_count'].sum()
            total_server_val = dff['character_count'].sum()
            label = "Caractères sur la période"
        else:
            total_val = len(user_df)
            total_server_val = len(dff)
            label = "Messages sur la période"
            
        percent_server = (total_val / total_server_val) * 100 if total_server_val > 0 else 0
        fav_hour = user_df["hour_of_day"].mode()[0]
        fav_day = user_df["weekday"].mode()[0]
        rank = user_counts_period.index.get_loc(user_name) + 1 if user_name in user_counts_period.index else "N/A"
        days_fr = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi", "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}
        
        return html.Div(
            className="card shadow-sm mb-4 animate__animated animate__fadeIn",
            children=[
                html.Div(className="card-header fs-5", children=f"👤 Profil de {user_name}"),
                html.Div(className="card-body", children=html.Ul(
                    className="list-group list-group-flush",
                    children=[
                        html.Li(f"💬 {label} : {total_val:,.0f}".replace(',', ' '), className="list-group-item"),
                        html.Li(f"📈 Part de l'activité du serveur : {percent_server:.2f}%", className="list-group-item"),
                        html.Li(f"🏆 Classement sur la période : #{rank}", className="list-group-item"),
                        html.Li(f"🕒 Heure de pointe : {fav_hour}h - {fav_hour+1}h", className="list-group-item"),
                        html.Li(f"📅 Jour favori : {days_fr.get(fav_day, fav_day)}", className="list-group-item"),
                    ]
                ))
            ]
        )

    def create_weekday_graph(dff, metric_selected):
        if dff.empty: return go.Figure()
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_fr = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi", "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}
        
        if metric_selected == 'characters':
            weekday_values = dff.groupby("weekday")['character_count'].sum().reindex(days_order).fillna(0).rename(index=days_fr)
            y_label = "Nombre de caractères"
        else:
            weekday_values = dff.groupby("weekday").size().reindex(days_order).fillna(0).rename(index=days_fr)
            y_label = "Nombre de messages"
            
        fig = px.bar(weekday_values, x=weekday_values.index, y=weekday_values.values, template="plotly_white", labels={"x": "Jour de la semaine", "y": y_label})
        fig.update_traces(marker_color='#20c997')
        return fig

def create_cumulative_graph(dff_filtered, color_map, metric_selected):
    if dff_filtered.empty: return go.Figure()
    
    if metric_selected == 'characters':
        cumulative_data = dff_filtered.set_index("timestamp").groupby("author_name").resample("D")['character_count'].sum().reset_index(name="daily_value")
        y_label = "Caractères cumulés"
    else:
        cumulative_data = dff_filtered.set_index("timestamp").groupby("author_name").resample("D").size().reset_index(name="daily_value")
        y_label = "Messages cumulés"
        
    cumulative_data["cumulative_value"] = cumulative_data.groupby("author_name")["daily_value"].cumsum()
    return px.line(
        cumulative_data, x="timestamp", y="cumulative_value", color="author_name",
        color_discrete_map=color_map, template="plotly_white",
        labels={"timestamp": "Date", "cumulative_value": y_label}
    ).update_layout(legend={"title": "Utilisateurs"})

def create_monthly_graph(dff_filtered, color_map, metric_selected):
    if dff_filtered.empty: return go.Figure()

    if metric_selected == 'characters':
        monthly_values = dff_filtered.groupby(["author_name", "month_year"])['character_count'].sum().reset_index(name="value")
        y_label = "Nombre de caractères"
    else:
        monthly_values = dff_filtered.groupby(["author_name", "month_year"]).size().reset_index(name="value")
        y_label = "Nombre de messages"
        
    fig = px.line(
        monthly_values, x="month_year", y="value", color="author_name",
        color_discrete_map=color_map, markers=True, template="plotly_white",
        labels={"month_year": "Mois", "value": y_label}
    )
    return fig.update_xaxes(categoryorder="category ascending").update_layout(legend={"title": "Utilisateurs"})

def create_hourly_graph(dff_filtered, color_map, server_average_df, metric_selected):
    if not dff_filtered.empty:
        if metric_selected == 'characters':
            hourly_values = dff_filtered.groupby(["author_name", "hour_of_day"])['character_count'].sum().reset_index(name="value")
        else:
            hourly_values = dff_filtered.groupby(["author_name", "hour_of_day"]).size().reset_index(name="value")
        hourly_values["total_per_user"] = hourly_values.groupby("author_name")["value"].transform("sum")
        hourly_values["percentage"] = (hourly_values["value"] / hourly_values["total_per_user"]) * 100 if hourly_values["total_per_user"].sum() > 0 else 0
    else:
        hourly_values = pd.DataFrame(columns=["hour_of_day", "percentage", "author_name"])

    fig = px.line(
        hourly_values, x="hour_of_day", y="percentage", color="author_name",
        color_discrete_map=color_map, markers=True, template="plotly_white",
        labels={"hour_of_day": "Heure de la journée", "percentage": "Pourcentage de l'activité (%)"},
    )
    if not server_average_df.empty:
        fig.add_trace(go.Scatter(
            x=server_average_df["hour_of_day"], y=server_average_df["percentage"],
            mode='lines', name='Moyenne du Serveur', line=dict(color='#d62728', width=4),
        ))
    return fig.update_layout(xaxis={"dtick": 1}, legend={"title": "Légende"})

def create_leaderboard(dff, period, metric_name, date_format, metric_selected):
    if dff.empty: return html.P("Pas de données.", className="text-center p-3")
    
    if metric_selected == 'characters':
        resampled = dff.groupby([dff["timestamp"].dt.to_period(period), "author_name"])['character_count'].sum().reset_index(name="value")
    else:
        resampled = dff.groupby([dff["timestamp"].dt.to_period(period), "author_name"]).size().reset_index(name="value")
        
    if resampled.empty: return html.P("Pas assez de données.", className="text-center p-3")
    
    winners = resampled.loc[resampled.groupby("timestamp")["value"].idxmax()]
    wins_df = winners.groupby("author_name")["timestamp"].agg(list).reset_index()
    wins_df[metric_name] = wins_df["timestamp"].apply(len)
    wins_df = wins_df.sort_values(metric_name, ascending=False).head(10)
    
    items = [
        html.Li(
            className="list-group-item d-flex justify-content-between align-items-center leaderboard-item",
            title=", ".join([d.strftime(date_format) for d in row["timestamp"]]),
            children=[
                html.Div([html.Span(f"{i + 1}.", className="leaderboard-rank"), html.Span(row['author_name'])]),
                html.Span(f"{row[metric_name]}", className="badge rounded-pill"),
            ]
        ) for i, row in wins_df.iterrows()
    ]
    return html.Ul(items, className="list-group list-group-flush")

