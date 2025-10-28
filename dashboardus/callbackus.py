# dashboardus/callbackus.py

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re  # For mention parsing in content (fallback)


def register_callbacks(app, df, role_colors_map, member_data):

    # --- Dictionaries & Sets ---
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

    # Pre-calculate maps and sets for efficiency
    # Ensure df is not empty before trying to create maps
    if not df.empty:
        user_id_to_name_map = (
            df.drop_duplicates(subset=["author_id"])
            .set_index("author_id")["author_name"]
            .to_dict()
        )
        name_to_user_id_map = {
            v: k for k, v in user_id_to_name_map.items()
        }  # Reverse map
    else:
        user_id_to_name_map = {}
        name_to_user_id_map = {}

    virgule_role_name = "Virgule du 4'"
    virgule_member_ids = {
        int(user_id)
        for user_id, data in member_data.items()
        if virgule_role_name in data.get("roles", [])
    }
    virgule_author_names = {
        user_id_to_name_map[uid]
        for uid in virgule_member_ids
        if uid in user_id_to_name_map
    }
    current_member_ids_int = {
        int(id) for id in member_data.keys()
    }  # Set of current member IDs

    # --- Helpers ---
    def is_light_color(hex_color):
        try:  # Add error handling for invalid hex codes
            if not isinstance(hex_color, str):
                return True  # Default to light if not a string
            hex_color = hex_color.lstrip("#")
            if len(hex_color) != 6:
                return True  # Default to light if invalid length
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
            return luminance > 0.5
        except:
            return True  # Default to light on any parsing error

    # --- Main Callback ---
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
        Output("mentioned-users-graph", "figure"),  # New graph
        Output("top-reacted-messages", "children"),  # New component
        Input("user-dropdown", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("top-n-dropdown", "value"),
        Input("metric-selector", "value"),
        Input("evolution-graph-selector", "value"),
        Input("highlight-user-dropdown", "value"),
        Input("date-range-dropdown", "value"),
        Input("virgule-filter", "value"),
        Input("distribution-time-unit", "value"),
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

        # --- 1. Date Filter Logic ---
        new_top_n_value = top_n
        if triggered_id == "user-dropdown":
            new_top_n_value = "custom"

        new_date_range_period = date_range_period
        if triggered_id == "date-picker-range":
            new_date_range_period = "custom"

        output_start_date, output_end_date = start_date, end_date
        if triggered_id is None:
            today = datetime.now()
            output_start_date = (today - timedelta(days=365)).date()
            output_end_date = today.date()
            new_date_range_period = "last_365"
        elif triggered_id == "date-range-dropdown":
            today = datetime.now()
            if date_range_period == "all-time":
                # --- FIX 1: Use the global 'df' to get true min/max ---
                output_start_date = df["timestamp"].min().date()
                output_end_date = df["timestamp"].max().date()
                # --- End Fix ---
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

        # --- 2. Global Data Filtering (Date & Role) ---
        start_date_utc = pd.to_datetime(output_start_date, utc=True)
        end_date_utc = pd.to_datetime(output_end_date, utc=True).replace(
            hour=23, minute=59, second=59
        )

        if virgule_filter:
            df_filtered_by_role = df[df["author_name"].isin(virgule_author_names)]
        else:
            df_filtered_by_role = df

        dff = df_filtered_by_role[
            (df_filtered_by_role["timestamp"] >= start_date_utc)
            & (df_filtered_by_role["timestamp"] <= end_date_utc)
        ].copy()

        # Add time columns if dff is not empty
        if not dff.empty:
            dff["month_year"] = (
                dff["timestamp"]
                .dt.tz_convert("Europe/Paris")
                .dt.to_period("M")
                .astype(str)
            )
            dff["hour_of_day"] = dff["timestamp"].dt.tz_convert("Europe/Paris").dt.hour
            dff["weekday"] = dff["timestamp"].dt.day_name()
            dff["month_name"] = dff["timestamp"].dt.month_name()
            dff["year"] = dff["timestamp"].dt.year
        else:
            # Add empty columns if dff is empty to prevent errors later
            for col in ["month_year", "hour_of_day", "weekday", "month_name", "year"]:
                dff[col] = pd.NA

        # --- 3. User List Preparation ---
        if metric_selected == "characters" and not dff.empty:
            user_counts_period = (
                dff.groupby("author_name")["character_count"]
                .sum()
                .sort_values(ascending=False)
            )
        elif not dff.empty:
            user_counts_period = dff["author_name"].value_counts()
        else:
            user_counts_period = pd.Series(dtype="int64")  # Empty series if no data

        user_counts_all_time = df_filtered_by_role["author_name"].value_counts()
        sorted_users_by_count = user_counts_all_time.index.tolist()

        user_value = selected_users
        # Handle initial load or filter change for Top N
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
            if top_n != "custom" and not user_counts_period.empty:
                # Ensure top_n is an integer if possible
                try:
                    n = int(top_n)
                    user_value = user_counts_period.nlargest(n).index.tolist()
                except ValueError:
                    pass
            elif top_n != "custom" and user_counts_period.empty:
                user_value = []  # No users if no data in period

        # Fallback for selected_users if they become empty somehow
        if user_value is None:
            user_value = []

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
                        ),  # Hidden original name for search
                    ]
                ),
                "value": user,
            }
            for user in sorted_users_by_count
        ]

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        # --- 4. Common Data Prep (Colors, Styles, Profile) ---
        style_rules = []
        for user in user_value:
            safe_user = str(user).replace('"', '\\"')
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

        # --- 5. Empty State Handling ---
        empty_figure = go.Figure(
            layout={
                "template": "plotly_white",
                "annotations": [{"text": "No Data", "showarrow": False}],
            }
        )
        empty_leaderboard = html.P(
            "No data available for this period.", className="text-center text-muted p-4"
        )
        empty_list_component = html.Div(
            "No data available for this period.", className="text-center text-muted p-4"
        )

        if dff.empty:
            # Return empty states for all outputs
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
                empty_figure,
                empty_list_component,
            )

        # --- 6. Graph & Leaderboard Creation ---

        # Section 1: Temporal Analysis
        if evolution_view == 0:
            fig_evolution = create_cumulative_graph(
                dff_filtered, color_map, metric_selected, highlighted_user
            )
        else:
            fig_evolution = create_monthly_graph(
                dff_filtered, color_map, metric_selected, highlighted_user
            )

        # Section 2: Message Analysis
        fig_median_length = create_median_length_graph(dff_filtered, dff, color_map)
        fig_distribution = create_distribution_graph(
            dff_filtered,
            dff,
            user_counts_period,
            color_map,
            dist_time_unit,
            metric_selected,
        )
        fig_mentioned = create_most_mentioned_graph(dff, user_id_to_name_map, color_map)
        top_reactions_component = create_top_reactions_list(
            dff, user_id_map_full, role_colors_map, current_member_ids_int
        )

        # Section 3: Leaderboards
        monthly_leaderboard_msg = create_leaderboard(
            dff, "M", "Months Won", "%B %Y", "messages"
        )
        daily_leaderboard_msg = create_leaderboard(
            dff, "D", "Days Won", "%d %B %Y", "messages"
        )
        monthly_leaderboard_char = create_leaderboard(
            dff, "M", "Months Won", "%B %Y", "characters"
        )
        daily_leaderboard_char = create_leaderboard(
            dff, "D", "Days Won", "%d %B %Y", "characters"
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
            fig_mentioned,
            top_reactions_component,
        )

    # --- Graphing Functions ---

    def create_user_profile_card(user_name, dff, user_counts_period, metric_selected):
        user_df = dff[dff["author_name"] == user_name]
        if user_df.empty:
            return []

        if metric_selected == "characters":
            total_val = user_df["character_count"].sum()
            total_server_val = dff["character_count"].sum()
            label = "Characters (Period)"
        else:
            total_val = len(user_df)
            total_server_val = len(dff)
            label = "Messages (Period)"

        percent_server = (
            (total_val / total_server_val) * 100 if total_server_val > 0 else 0
        )
        fav_hour = (
            user_df["hour_of_day"].mode()[0]
            if not user_df["hour_of_day"].mode().empty
            else "N/A"
        )
        fav_day = (
            user_df["weekday"].mode()[0]
            if not user_df["weekday"].mode().empty
            else "N/A"
        )
        rank = (
            user_counts_period.index.get_loc(user_name) + 1
            if user_name in user_counts_period.index
            else "N/A"
        )

        return html.Div(
            className="card shadow-sm mb-4 animate__animated animate__fadeIn",
            children=[
                html.Div(
                    className="card-header fs-5", children=f"👤 Profile: {user_name}"
                ),
                html.Div(
                    className="card-body",
                    children=html.Ul(
                        className="list-group list-group-flush",
                        children=[
                            html.Li(
                                f"💬 {label}: {total_val:,.0f}".replace(",", " "),
                                className="list-group-item",
                            ),
                            html.Li(
                                f"📈 Share of Server Activity: {percent_server:.2f}%",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"🏆 Rank (Period): #{rank}",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"🕒 Peak Hour: {fav_hour}:00 - {int(fav_hour)+1 if fav_hour != 'N/A' else 'N/A'}:00",
                                className="list-group-item",
                            ),
                            html.Li(
                                f"📅 Favorite Day: {days_fr.get(fav_day, fav_day)}",
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
            y_label = "Cumulative Characters"
        else:
            daily_data = (
                dff_filtered.set_index("timestamp")
                .groupby("author_name")
                .resample("D")
                .size()
                .reset_index(name="daily_value")
            )
            y_label = "Cumulative Messages"

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
        ).update_layout(legend={"title": "Users"}, height=600)

        for trace in fig.data:
            trace_name_no_count = trace.name.split(" (")[0]
            if trace_name_no_count in period_totals:
                total_val = period_totals[trace_name_no_count]
                if "(" not in trace.name:
                    trace.name = f"{trace_name_no_count} ({total_val:,.0f})".replace(
                        ",", " "
                    )
            if trace_name_no_count == highlighted_user:
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
            y_label = "Character Count"
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
            y_label = "Message Count"

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
                labels={"month_year": "Month", "value": y_label},
                category_orders={"author_name": sorted_names},
            )
            .update_xaxes(categoryorder="category ascending")
            .update_layout(legend={"title": "Users"}, height=600)
        )

        for trace in fig.data:
            trace_name_no_count = trace.name.split(" (")[0]
            if trace_name_no_count in period_totals:
                total_val = period_totals[trace_name_no_count]
                if "(" not in trace.name:
                    trace.name = f"{trace_name_no_count} ({total_val:,.0f})".replace(
                        ",", " "
                    )
            if trace_name_no_count == highlighted_user:
                trace.line.width = 4
                trace.marker.size = 10

        return fig

    def create_median_length_graph(dff_filtered, dff, color_map):
        if dff_filtered.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {"text": "Select users to display", "showarrow": False}
                    ],
                }
            )

        dff_filtered["character_count"] = pd.to_numeric(
            dff_filtered["character_count"], errors="coerce"
        )
        dff["character_count"] = pd.to_numeric(dff["character_count"], errors="coerce")

        median_lengths = (
            dff_filtered.dropna(subset=["character_count"])
            .groupby("author_name")["character_count"]
            .median()
            .sort_values(ascending=True)
        )
        server_median = dff.dropna(subset=["character_count"])[
            "character_count"
        ].median()

        if median_lengths.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {
                            "text": "No valid message length data for selected users",
                            "showarrow": False,
                        }
                    ],
                }
            )

        colors = [color_map.get(name, "#6c757d") for name in median_lengths.index]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=median_lengths.index,
                x=median_lengths.values,
                orientation="h",
                marker=dict(color=colors),
                name="Median Length",
            )
        )

        if pd.notna(server_median):
            fig.add_shape(
                type="line",
                x0=server_median,
                x1=server_median,
                y0=-0.5,
                y1=len(median_lengths) - 0.5,
                line=dict(color="red", width=3, dash="dash"),
                name="Server Median",
            )
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="lines",
                    line=dict(color="red", width=3, dash="dash"),
                    name="Server Median",
                )
            )

        fig.update_layout(
            xaxis_title="Median Characters per Message",
            yaxis_title="User",
            template="plotly_white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        return fig

    def create_distribution_graph(
        dff_filtered, dff, user_counts_period, color_map, time_unit, metric_selected
    ):
        # --- THIS IS THE CORRECTED VERSION ---
        top_users = user_counts_period.nlargest(3).index.tolist()
        dff_top = dff_filtered[dff_filtered["author_name"].isin(top_users)]

        if dff.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [{"text": "No Data", "showarrow": False}],
                }
            )

        if time_unit == "hour":
            x_col, x_label = "hour_of_day", "Hour of Day"
            categories = list(range(24))
            dtick = 2
        elif time_unit == "weekday":
            x_col, x_label = "weekday", "Day of Week"
            categories = days_order
            dtick = 1
        elif time_unit == "month":
            x_col, x_label = "month_name", "Month of Year"
            categories = months_order
            dtick = 1
        else:  # year
            x_col, x_label = "year", "Year"
            categories = sorted(dff[x_col].dropna().unique())  # Dropna for safety
            dtick = 1

        dff_top["x_axis"] = dff_top[x_col]
        dff["x_axis"] = dff[x_col]

        # 1. Calculate server percentages
        if metric_selected == "characters":
            server_values = dff.groupby("x_axis")["character_count"].sum()
        else:
            server_values = dff.groupby("x_axis").size()

        server_values = server_values.reindex(categories).fillna(0)
        server_total = server_values.sum()
        server_percentage = (
            (server_values / server_total) * 100 if server_total > 0 else 0
        )

        # 2. Calculate user percentages individually (THE FIX)
        all_user_data = []
        for user in top_users:
            user_df = dff_top[dff_top["author_name"] == user]

            if metric_selected == "characters":
                user_values_single = user_df.groupby("x_axis")["character_count"].sum()
            else:
                user_values_single = user_df.groupby("x_axis").size()

            # Reindex based on the correct categories
            user_values_reindexed = user_values_single.reindex(categories).fillna(0)

            user_total = user_values_reindexed.sum()
            user_percentage = (
                (user_values_reindexed / user_total) * 100 if user_total > 0 else 0
            )

            user_percentage_df = user_percentage.reset_index()
            user_percentage_df.columns = ["x_axis", "percentage"]
            user_percentage_df["author_name"] = user
            all_user_data.append(user_percentage_df)

        if not all_user_data:
            user_values_final = pd.DataFrame(
                columns=["x_axis", "percentage", "author_name"]
            )
        else:
            user_values_final = pd.concat(all_user_data, ignore_index=True)

        # 3. Create the plot
        fig = px.line(
            user_values_final,
            x="x_axis",
            y="percentage",
            color="author_name",
            color_discrete_map=color_map,
            markers=True,
            template="plotly_white",
            labels={"x_axis": x_label, "percentage": "Activity Share (%)"},
        )

        fig.add_trace(
            go.Scatter(
                x=server_percentage.index,
                y=server_percentage.values,
                mode="lines",
                name="Server Average",
                line=dict(color="#d62728", width=4),
            )
        )

        fig.update_layout(xaxis={"dtick": dtick}, legend={"title": "Legend"})
        fig.update_xaxes(categoryorder="array", categoryarray=categories)
        return fig
        # --- END OF CORRECTED FUNCTION ---

    def create_leaderboard(dff, period, metric_name, date_format, metric_selected):
        if dff.empty:
            return html.P("No data.", className="text-center p-3")

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
            return html.P("Not enough data.", className="text-center p-3")

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

    def create_most_mentioned_graph(dff, user_id_map, color_map):
        if dff.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [{"text": "No Data", "showarrow": False}],
                }
            )

        mention_counts = {}

        # --- FIX 2: More robust counting ---
        # 1. Count Replies
        # Replace potential empty strings or other junk with NaN, then drop
        replies = dff["replied_to_author_id"].replace("", pd.NA).dropna()
        if not replies.empty:
            reply_counts = replies.astype(str).value_counts()
            for user_id, count in reply_counts.items():
                mention_counts[user_id] = mention_counts.get(user_id, 0) + count

        # 2. Count @ Mentions (from stored list)
        # Ensure the column contains lists, not NaNs or other types
        mentions_list = dff["mentioned_user_ids"].apply(
            lambda x: x if isinstance(x, list) else []
        )
        mention_df = mentions_list.explode().dropna()
        # --- End Fix ---

        if not mention_df.empty:
            mention_id_counts = mention_df.astype(str).value_counts()
            for user_id, count in mention_id_counts.items():
                mention_counts[user_id] = mention_counts.get(user_id, 0) + count

        if not mention_counts:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {"text": "No mentions or replies found", "showarrow": False}
                    ],
                }
            )

        mentions_final_df = pd.DataFrame(
            list(mention_counts.items()), columns=["user_id", "count"]
        )

        # Safely convert user_id to numeric, coercing errors to NaN
        mentions_final_df["user_id_int"] = pd.to_numeric(
            mentions_final_df["user_id"], errors="coerce"
        )
        mentions_final_df = mentions_final_df.dropna(
            subset=["user_id_int"]
        )  # Drop rows that couldn't be converted
        mentions_final_df["user_id_int"] = mentions_final_df["user_id_int"].astype(int)

        mentions_final_df["author_name"] = mentions_final_df["user_id_int"].map(
            user_id_map
        )

        mentions_final_df = mentions_final_df.dropna(subset=["author_name"])
        if mentions_final_df.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {"text": "No mentions for known users", "showarrow": False}
                    ],
                }
            )

        mentions_final_df = (
            mentions_final_df.groupby("author_name")["count"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
        )

        colors = [color_map.get(name, "#6c757d") for name in mentions_final_df.index]

        fig = go.Figure(
            data=[
                go.Bar(
                    y=mentions_final_df.index,
                    x=mentions_final_df.values,
                    orientation="h",
                    marker=dict(color=colors),
                )
            ]
        )

        fig.update_layout(
            xaxis_title="Number of Times Mentioned (Reply + @)",
            yaxis_title="User",
            yaxis={"categoryorder": "total ascending"},
            template="plotly_white",
            margin=dict(l=150),
        )
        return fig

    def create_top_reactions_list(
        dff, user_id_map_full, role_colors_map, current_member_ids_int
    ):
        if dff.empty or "reaction_count" not in dff.columns:
            return html.P(
                "No reaction data available for this period.",
                className="text-center text-muted p-4",
            )

        # Fill NaN with 0 before sorting
        dff["reaction_count"] = dff["reaction_count"].fillna(0)

        top_reacted = dff.sort_values(by="reaction_count", ascending=False).head(10)
        top_reacted = top_reacted[
            top_reacted["reaction_count"] > 0
        ]  # Only show messages with reactions

        if top_reacted.empty:
            return html.P(
                "No messages with reactions found.",
                className="text-center text-muted p-4",
            )

        list_items = []
        for index, row in top_reacted.iterrows():
            author_name = row["author_name"]
            author_id = user_id_map_full.get(author_name)
            is_member = author_id in current_member_ids_int
            author_color = (
                role_colors_map.get(str(author_id), "#6c757d")
                if is_member
                else "#6c757d"
            )

            message_content = row["content"]
            if len(message_content) > 200:  # Increased length
                message_content = message_content[:200] + "..."
            if not message_content:
                message_content = "[Message without text (e.g., image, embed)]"

            list_items.append(
                html.Li(
                    className="list-group-item d-flex justify-content-between align-items-start",
                    children=[
                        html.Div(
                            className="ms-2 me-auto",
                            children=[
                                html.Div(
                                    html.Strong(
                                        author_name, style={"color": author_color}
                                    ),
                                    className="fw-bold",
                                ),
                                html.P(
                                    message_content,
                                    className="mb-1",
                                    style={"whiteSpace": "pre-wrap"},
                                ),  # Preserve line breaks
                                html.A(
                                    "Go to message",
                                    href=row["jump_url"],
                                    target="_blank",
                                    className="small text-muted",
                                ),
                            ],
                        ),
                        html.Span(
                            f"{int(row['reaction_count'])} users",
                            className="badge bg-primary rounded-pill fs-6",
                        ),  # Made badge bigger
                    ],
                )
            )

        return html.Ul(list_items, className="list-group")
