# dashboardus/callbackus.py

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


def register_callbacks(app, df, role_colors_map, member_data):

    # --- Dictionnaires pour les traductions et l'ordre ---
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    days_fr = {
        "Monday": "Lundi",
        "Tuesday": "Mardi",
        "Wednesday": "Mercredi",
        "Thursday": "Jeudi",
        "Friday": "Vendredi",
        "Saturday": "Samedi",
        "Sunday": "Dimanche",
    }
    months_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    months_fr = {
        "January": "Janvier",
        "February": "Février",
        "March": "Mars",
        "April": "Avril",
        "May": "Mai",
        "June": "Juin",
        "July": "Juillet",
        "August": "Août",
        "September": "Septembre",
        "October": "Octobre",
        "November": "Novembre",
        "December": "Décembre",
    }

    # --- Helpers ---
    def is_light_color(hex_color):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return True  # Couleur par défaut si invalide
        try:
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
            return luminance > 0.5
        except ValueError:
            return True  # Par défaut sur clair en cas d'erreur

    # Pré-calculer les IDs des membres "Virgule"
    virgule_member_ids = {
        int(user_id)
        for user_id, data in member_data.items()
        if "Virgule du 4" in data.get("roles", [])
    }
    user_id_to_name_map = (
        df.drop_duplicates(subset=["author_id"])
        .set_index("author_id")["author_name"]
        .to_dict()
    )
    virgule_author_names = {
        user_id_to_name_map[uid]
        for uid in virgule_member_ids
        if uid in user_id_to_name_map
    }

    # --- Callbacks ---
    @app.callback(
        Output("date-range-display", "children"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
    )
    def display_date_range_duration(start_date, end_date):
        if not start_date or not end_date:
            return ""
        start = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
        end = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
        delta = end - start
        years, days = divmod(delta.days, 365)
        return (
            f"Durée : {years} an(s) et {days} jour(s)"
            if years > 0
            else f"Durée : {delta.days} jours"
        )

    @app.callback(
        Output("evolution-graph", "figure"),
        Output("user-dropdown", "options"),
        Output("user-dropdown", "value"),
        Output("dynamic-styles", "children"),
        Output("user-profile-card-container", "children"),
        Output("highlight-user-dropdown", "options"),
        Output("top-n-dropdown", "value"),
        Output("date-range-dropdown", "value"),
        Output("date-picker-range", "start_date"),
        Output("date-picker-range", "end_date"),
        Output("median-length-graph", "figure"),
        Output("distribution-graph", "figure"),
        Output("monthly-leaderboard-msg", "children"),
        Output("daily-leaderboard-msg", "children"),
        Output("monthly-leaderboard-char", "children"),
        Output("daily-leaderboard-char", "children"),
        Input("user-dropdown", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("top-n-dropdown", "value"),
        Input("metric-selector", "value"),
        Input("evolution-graph-selector", "value"),
        Input("highlight-user-dropdown", "value"),
        Input("date-range-dropdown", "value"),
        Input("virgule-filter", "value"),  # New Input
        Input("distribution-time-unit", "value"),  # New Input
        State("date-picker-range", "min_date_allowed"),
        State("date-picker-range", "max_date_allowed"),
    )
    def update_all(
        selected_users,
        start_date,
        end_date,
        top_n,
        metric_selected,
        evolution_view,
        highlighted_user,
        date_range_period,
        virgule_filter,
        dist_time_unit,
        min_date_allowed,
        max_date_allowed,
    ):

        ctx = dash.callback_context
        triggered_id = (
            ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        )

        # --- 1. GESTION DES FILTRES DE DATE ---
        new_top_n_value = top_n
        if triggered_id == "user-dropdown":
            new_top_n_value = "custom"

        new_date_range_period = date_range_period
        if triggered_id == "date-picker-range":
            new_date_range_period = "custom"

        output_start_date, output_end_date = start_date, end_date
        if triggered_id is None:  # Premier chargement
            today = datetime.now()
            output_start_date = (today - timedelta(days=365)).date()
            output_end_date = today.date()
            new_date_range_period = "last_365"
        elif triggered_id == "date-range-dropdown":
            today = datetime.now()
            if date_range_period == "all-time":
                output_start_date, output_end_date = min_date_allowed, max_date_allowed
            elif date_range_period == "current_year":
                output_start_date, output_end_date = (
                    today.replace(month=1, day=1).date(),
                    today.date(),
                )
            elif date_range_period == "last_365":
                output_start_date, output_end_date = (
                    today - timedelta(days=365)
                ).date(), today.date()
            elif date_range_period == "last_6_months":
                output_start_date, output_end_date = (
                    today - timedelta(days=180)
                ).date(), today.date()

        # --- 2. FILTRAGE GLOBAL DES DONNÉES (Date & Rôle) ---
        start_date_utc = pd.to_datetime(output_start_date, utc=True)
        end_date_utc = pd.to_datetime(output_end_date, utc=True).replace(
            hour=23, minute=59, second=59
        )

        # Appliquer le filtre de rôle si activé
        if virgule_filter:  # Le filtre est une liste, True si non vide
            df_filtered_by_role = df[df["author_name"].isin(virgule_author_names)]
        else:
            df_filtered_by_role = df

        dff = df_filtered_by_role[
            (df_filtered_by_role["timestamp"] >= start_date_utc)
            & (df_filtered_by_role["timestamp"] <= end_date_utc)
        ].copy()

        dff["month_year"] = (
            dff["timestamp"].dt.tz_convert("Europe/Paris").dt.to_period("M").astype(str)
        )
        dff["hour_of_day"] = dff["timestamp"].dt.tz_convert("Europe/Paris").dt.hour
        dff["weekday"] = dff["timestamp"].dt.day_name()
        dff["month_name"] = dff["timestamp"].dt.month_name()
        dff["year"] = dff["timestamp"].dt.year

        # --- 3. PRÉPARATION DES LISTES D'UTILISATEURS ---
        if metric_selected == "characters":
            user_counts_period = (
                dff.groupby("author_name")["character_count"]
                .sum()
                .sort_values(ascending=False)
            )
        else:
            user_counts_period = dff["author_name"].value_counts()

        # La liste de tous les utilisateurs (pour le dropdown) est basée sur le filtre de rôle
        user_counts_all_time = df_filtered_by_role["author_name"].value_counts()
        sorted_users_by_count = user_counts_all_time.index.tolist()

        user_value = selected_users
        if (
            triggered_id
            in [
                "top-n-dropdown",
                "date-picker-range",
                "metric-selector",
                "date-range-dropdown",
                "virgule-filter",
            ]
            or triggered_id is None
        ):
            if top_n != "custom":
                user_value = user_counts_period.nlargest(int(top_n)).index.tolist()

        user_id_map_full = (
            df.drop_duplicates(subset=["author_name"])
            .set_index("author_name")["author_id"]
            .to_dict()
        )
        name_to_original_map = (
            df.drop_duplicates(subset=["author_name"])
            .set_index("author_name")["original_author_name"]
            .to_dict()
        )
        current_member_ids_int = {int(id) for id in member_data.keys()}

        user_options = [
            {
                "label": html.Div(
                    [
                        html.Span(
                            user,
                            style={
                                "color": (
                                    "#6c757d"
                                    if user_id_map_full.get(user)
                                    not in current_member_ids_int
                                    else role_colors_map.get(
                                        str(user_id_map_full.get(user)), "#6c757d"
                                    )
                                ),
                                "textDecoration": (
                                    "line-through"
                                    if user_id_map_full.get(user)
                                    not in current_member_ids_int
                                    else "none"
                                ),
                                "fontWeight": "bold",
                            },
                        ),
                        html.Span(
                            name_to_original_map.get(user, user),
                            style={"display": "none"},
                        ),
                    ]
                ),
                "value": user,
            }
            for user in sorted_users_by_count
        ]

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        # --- 4. PRÉPARATION DES DONNÉES COMMUNES (Couleurs, Styles, Profil) ---
        style_rules = []
        for user in user_value:
            safe_user = user.replace('"', '\\"')
            user_id = user_id_map_full.get(user, "")
            is_member = user_id in current_member_ids_int

            bg_color = (
                role_colors_map.get(str(user_id), "#6c757d") if is_member else "#f8f9fa"
            )
            text_color = (
                ("#000000" if is_light_color(bg_color) else "#FFFFFF")
                if is_member
                else "#6c757d"
            )
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
        if highlighted_user:
            profile_card = create_user_profile_card(
                highlighted_user, dff, user_counts_period, metric_selected
            )

        highlight_options = [{"label": user, "value": user} for user in user_value]
        color_map = {
            user: role_colors_map.get(str(user_id_map_full.get(user)), "#6c757d")
            for user in user_value
        }

        # --- 5. GESTION DES ÉTATS VIDES ---
        empty_figure = go.Figure(
            layout={
                "template": "plotly_white",
                "annotations": [{"text": "Pas de données", "showarrow": False}],
            }
        )
        empty_leaderboard = html.P(
            "No data available for this period.", className="text-center text-muted p-4"
        )

        if dff.empty:
            return (
                empty_figure,
                user_options,
                user_value,
                final_styles,
                profile_card,
                highlight_options,
                new_top_n_value,
                new_date_range_period,
                output_start_date,
                output_end_date,
                empty_figure,
                empty_figure,
                empty_leaderboard,
                empty_leaderboard,
                empty_leaderboard,
                empty_leaderboard,
            )

        # --- 6. CRÉATION DES GRAPHIQUES & CLASSEMENTS ---

        # Rubrique 1: Analyse Temporelle
        if evolution_view == "cumulative":
            fig_evolution = create_cumulative_graph(
                dff_filtered, color_map, metric_selected, highlighted_user
            )
        else:  # 'monthly'
            fig_evolution = create_monthly_graph(
                dff_filtered, color_map, metric_selected, highlighted_user
            )

        # Rubrique 2: Analyse des Messages
        fig_median_length = create_median_length_graph(dff_filtered, dff, color_map)
        fig_distribution = create_distribution_graph(
            dff_filtered,
            dff,
            user_counts_period,
            color_map,
            dist_time_unit,
            metric_selected,
        )

        # Rubrique 3: Classements (Génère les 4)
        monthly_leaderboard_msg = create_leaderboard(
            dff, "M", "Mois gagnés", "%B %Y", "messages"
        )
        daily_leaderboard_msg = create_leaderboard(
            dff, "D", "Jours gagnés", "%d %B %Y", "messages"
        )
        monthly_leaderboard_char = create_leaderboard(
            dff, "M", "Mois gagnés", "%B %Y", "characters"
        )
        daily_leaderboard_char = create_leaderboard(
            dff, "D", "Jours gagnés", "%d %B %Y", "characters"
        )

        return (
            fig_evolution,
            user_options,
            user_value,
            final_styles,
            profile_card,
            highlight_options,
            new_top_n_value,
            new_date_range_period,
            output_start_date,
            output_end_date,
            fig_median_length,
            fig_distribution,
            monthly_leaderboard_msg,
            daily_leaderboard_msg,
            monthly_leaderboard_char,
            daily_leaderboard_char,
        )

    # --- Fonctions de création de graphiques ---

    def create_user_profile_card(user_name, dff, user_counts_period, metric_selected):
        user_df = dff[dff["author_name"] == user_name]
        if user_df.empty:
            return []

        if metric_selected == "characters":
            total_val = user_df["character_count"].sum()
            total_server_val = dff["character_count"].sum()
            label = "Caractères sur la période"
        else:
            total_val = len(user_df)
            total_server_val = len(dff)
            label = "Messages sur la période"

        percent_server = (
            (total_val / total_server_val) * 100 if total_server_val > 0 else 0
        )
        fav_hour = user_df["hour_of_day"].mode()[0]
        fav_day = user_df["weekday"].mode()[0]
        rank = (
            user_counts_period.index.get_loc(user_name) + 1
            if user_name in user_counts_period.index
            else "N/A"
        )

        return html.Div(
            className="card shadow-sm mb-4 animate__animated animate__fadeIn",
            children=[
                html.Div(
                    className="card-header fs-5", children=f"👤 Profil de {user_name}"
                ),
                html.Div(
                    className="card-body",
                    children=html.Ul(
                        className="list-group list-group-flush",
                        children=[
                            html.Li(
                                f"💬 {label} : {total_val:,.0f}".replace(",", " "),
                                className="list-group-item",
                            ),
                            html.Li(
                                f"📈 Part de l'activité du serveur : {percent_server:.2f}%",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"🏆 Classement sur la période : #{rank}",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"🕒 Heure de pointe : {fav_hour}h - {fav_hour+1}h",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"📅 Jour favori : {days_fr.get(fav_day, fav_day)}",
                                className="list-group-item",
                            ),
                        ],
                    ),
                ),
            ],
        )

    def create_cumulative_graph(
        dff_filtered, color_map, metric_selected, highlighted_user
    ):
        if dff_filtered.empty:
            return go.Figure()

        if metric_selected == "characters":
            daily_data = (
                dff_filtered.set_index("timestamp")
                .groupby("author_name")
                .resample("D")["character_count"]
                .sum()
                .reset_index(name="daily_value")
            )
            y_label = "Caractères cumulés"
        else:
            daily_data = (
                dff_filtered.set_index("timestamp")
                .groupby("author_name")
                .resample("D")
                .size()
                .reset_index(name="daily_value")
            )
            y_label = "Messages cumulés"

        daily_data["cumulative_value"] = daily_data.groupby("author_name")[
            "daily_value"
        ].cumsum()

        period_totals = (
            daily_data.groupby("author_name")["daily_value"]
            .sum()
            .sort_values(ascending=False)
        )
        sorted_names = period_totals.index.tolist()

        fig = px.line(
            daily_data,
            x="timestamp",
            y="cumulative_value",
            color="author_name",
            color_discrete_map=color_map,
            template="plotly_white",
            labels={"timestamp": "Date", "cumulative_value": y_label},
            category_orders={"author_name": sorted_names},
        ).update_layout(legend={"title": "Utilisateurs"}, height=600)

        for trace in fig.data:
            total_val = period_totals.get(trace.name, 0)
            trace.name = f"{trace.name} ({total_val:,.0f})".replace(",", " ")
            if highlighted_user and trace.name.startswith(highlighted_user):
                trace.line.width = 4

        return fig

    def create_monthly_graph(
        dff_filtered, color_map, metric_selected, highlighted_user
    ):
        if dff_filtered.empty:
            return go.Figure()

        if metric_selected == "characters":
            monthly_values = (
                dff_filtered.groupby(["author_name", "month_year"])["character_count"]
                .sum()
                .reset_index(name="value")
            )
            period_totals = (
                monthly_values.groupby("author_name")["value"]
                .sum()
                .sort_values(ascending=False)
            )
            y_label = "Nombre de caractères"
        else:
            monthly_values = (
                dff_filtered.groupby(["author_name", "month_year"])
                .size()
                .reset_index(name="value")
            )
            period_totals = (
                monthly_values.groupby("author_name")["value"]
                .sum()
                .sort_values(ascending=False)
            )
            y_label = "Nombre de messages"

        sorted_names = period_totals.index.tolist()

        fig = (
            px.line(
                monthly_values,
                x="month_year",
                y="value",
                color="author_name",
                color_discrete_map=color_map,
                markers=True,
                template="plotly_white",
                labels={"month_year": "Mois", "value": y_label},
                category_orders={"author_name": sorted_names},
            )
            .update_xaxes(categoryorder="category ascending")
            .update_layout(legend={"title": "Utilisateurs"}, height=600)
        )

        for trace in fig.data:
            total_val = period_totals.get(trace.name, 0)
            trace.name = f"{trace.name} ({total_val:,.0f})".replace(",", " ")
            if highlighted_user and trace.name.startswith(highlighted_user):
                trace.line.width = 4
                trace.marker.size = 10

        return fig

    def create_median_length_graph(dff_filtered, dff, color_map):
        if dff_filtered.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {"text": "Sélectionnez des utilisateurs", "showarrow": False}
                    ],
                }
            )

        median_lengths = (
            dff_filtered.groupby("author_name")["character_count"]
            .median()
            .sort_values(ascending=True)
        )
        server_median = dff["character_count"].median()
        colors = [color_map.get(name, "#6c757d") for name in median_lengths.index]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=median_lengths.index,
                x=median_lengths.values,
                orientation="h",
                marker=dict(color=colors),
                text=median_lengths.values,
                texttemplate="%{x:.0f}",
                textposition="outside",
            )
        )

        fig.add_shape(
            type="line",
            x0=server_median,
            x1=server_median,
            y0=-0.5,
            y1=len(median_lengths) - 0.5,
            line=dict(color="red", width=3, dash="dash"),
        )

        fig.update_layout(
            xaxis_title="Nombre de caractères (médian)",
            yaxis_title=None,
            template="plotly_white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color="red", width=3, dash="dash"),
                name=f"Médiane Serveur ({server_median:.0f})",
            )
        )
        return fig

    def create_distribution_graph(
        dff_filtered, dff, user_counts_period, color_map, time_unit, metric_selected
    ):
        top_5_users = user_counts_period.nlargest(5).index.tolist()
        dff_top5 = dff_filtered[dff_filtered["author_name"].isin(top_5_users)]

        if dff.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [{"text": "Pas de données", "showarrow": False}],
                }
            )

        if time_unit == "hour":
            x_col, x_label = "hour_of_day", "Heure de la journée"
            categories = list(range(24))
            dff_top5["x_axis"] = dff_top5[x_col]
            dff["x_axis"] = dff[x_col]
            dtick = 2
        elif time_unit == "weekday":
            x_col, x_label = "weekday", "Jour de la semaine"
            categories = [days_fr[d] for d in days_order]
            dff_top5["x_axis"] = dff_top5[x_col].map(days_fr)
            dff["x_axis"] = dff[x_col].map(days_fr)
            dtick = 1
        elif time_unit == "month":
            x_col, x_label = "month_name", "Mois de l'année"
            categories = [months_fr[m] for m in months_order]
            dff_top5["x_axis"] = dff_top5[x_col].map(months_fr)
            dff["x_axis"] = dff[x_col].map(months_fr)
            dtick = 1
        else:  # year
            x_col, x_label = "year", "Année"
            categories = sorted(dff[x_col].unique())
            dff_top5["x_axis"] = dff_top5[x_col]
            dff["x_axis"] = dff[x_col]
            dtick = 1

        if metric_selected == "characters":
            user_values = (
                dff_top5.groupby(["author_name", "x_axis"])["character_count"]
                .sum()
                .reset_index(name="value")
            )
            server_values = (
                dff.groupby("x_axis")["character_count"].sum().reset_index(name="value")
            )
        else:
            user_values = (
                dff_top5.groupby(["author_name", "x_axis"])
                .size()
                .reset_index(name="value")
            )
            server_values = dff.groupby("x_axis").size().reset_index(name="value")

        user_totals = user_values.groupby("author_name")["value"].transform("sum")
        user_values["percentage"] = (user_values["value"] / user_totals) * 100

        server_total = server_values["value"].sum()
        server_values["percentage"] = (server_values["value"] / server_total) * 100

        # Pivoter pour combler les vides et assurer l'ordre
        user_values_pivot = (
            user_values.pivot_table(
                index="x_axis", columns="author_name", values="percentage"
            )
            .reindex(categories)
            .fillna(0)
        )
        user_values = user_values_pivot.melt(
            ignore_index=False, var_name="author_name", value_name="percentage"
        ).reset_index()

        server_values = (
            server_values.set_index("x_axis")
            .reindex(categories)
            .reset_index()
            .fillna(0)
        )

        fig = px.line(
            user_values,
            x="x_axis",
            y="percentage",
            color="author_name",
            color_discrete_map=color_map,
            markers=True,
            template="plotly_white",
            labels={"x_axis": x_label, "percentage": "Pourcentage de l'activité (%)"},
        )

        fig.add_trace(
            go.Scatter(
                x=server_values["x_axis"],
                y=server_values["percentage"],
                mode="lines",
                name="Moyenne du Serveur",
                line=dict(color="#d62728", width=4),
            )
        )

        fig.update_layout(xaxis={"dtick": dtick}, legend={"title": "Légende"})
        fig.update_xaxes(categoryorder="array", categoryarray=categories)
        return fig

    def create_leaderboard(dff, period, metric_name, date_format, metric_selected):
        if dff.empty:
            return html.P("Pas de données.", className="text-center p-3")

        if metric_selected == "characters":
            resampled = (
                dff.groupby([dff["timestamp"].dt.to_period(period), "author_name"])[
                    "character_count"
                ]
                .sum()
                .reset_index(name="value")
            )
        else:
            resampled = (
                dff.groupby([dff["timestamp"].dt.to_period(period), "author_name"])
                .size()
                .reset_index(name="value")
            )

        if resampled.empty:
            return html.P("Pas assez de données.", className="text-center p-3")

        winners = resampled.loc[resampled.groupby("timestamp")["value"].idxmax()]
        wins_df = winners.groupby("author_name")["timestamp"].agg(list).reset_index()
        wins_df[metric_name] = wins_df["timestamp"].apply(len)
        wins_df = wins_df.sort_values(metric_name, ascending=False).head(10)

        items = [
            html.Li(
                className="list-group-item d-flex justify-content-between align-items-center leaderboard-item",
                title=", ".join([d.strftime(date_format) for d in row["timestamp"]]),
                children=[
                    html.Div(
                        [
                            html.Span(f"{i + 1}.", className="leaderboard-rank"),
                            html.Span(row["author_name"]),
                        ]
                    ),
                    html.Span(f"{row[metric_name]}", className="badge rounded-pill"),
                ],
            )
            for i, row in wins_df.iterrows()
        ]
        return html.Ul(items, className="list-group list-group-flush")
