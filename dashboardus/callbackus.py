import calendar
import json
from datetime import datetime, timedelta
from typing import Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from dataus.constant import EXCLUDED_CHANNEL_IDS, MIN_MESSAGE_COUNT


def create_most_replied_graph(
    dff: pd.DataFrame,
    color_map: dict,
    user_id_to_name_map: dict,
    name_to_user_id_map: dict,
    user_id_to_color_map: dict,
) -> go.Figure:
    if dff.empty or "reply_to_user_id" not in dff.columns:
        return go.Figure(
            layout={
                "template": "plotly_white",
                "annotations": [{"text": "No Data", "showarrow": False}],
            }
        )

    reply_counts = {}
    reply_user_ids = dff["reply_to_user_id"].dropna().astype(str)
    if not reply_user_ids.empty:
        reply_id_counts = reply_user_ids.value_counts()
        for user_id, count in reply_id_counts.items():
            reply_counts[user_id] = reply_counts.get(user_id, 0) + count

    if not reply_counts:
        return go.Figure(
            layout={
                "template": "plotly_white",
                "annotations": [{"text": "No replies found", "showarrow": False}],
            }
        )

    replies_df = pd.DataFrame(list(reply_counts.items()), columns=["id", "count"])
    replies_df["name"] = replies_df["id"].apply(lambda uid: user_id_to_name_map.get(int(uid), f"ID: {uid}"))
    replies_df = replies_df.dropna(subset=["name"])

    if replies_df.empty:
        return go.Figure(
            layout={
                "template": "plotly_white",
                "xaxis": {"visible": False},
                "yaxis": {"visible": False},
                "annotations": [
                    {
                        "text": "No replies for known users",
                        "showarrow": False,
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                        "font": {"size": 16},
                    }
                ],
            }
        )

    replies_final = (
        replies_df.groupby("name")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )

    colors = [user_id_to_color_map.get(str(name_to_user_id_map.get(name, "")), "#6c757d") for name in replies_final.index]

    fig = go.Figure(
        data=[
            go.Bar(
                y=replies_final.index,
                x=replies_final.values,
                orientation="h",
                marker=dict(color=colors),
            )
        ]
    )
    fig.update_layout(
        xaxis_title="Number of Replies Received",
        yaxis_title=None,
        yaxis={"categoryorder": "total ascending"},
        template="plotly_white",
        margin=dict(l=150),
    )
    return fig
import calendar
import json
from datetime import datetime, timedelta
from typing import Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from dataus.constant import EXCLUDED_CHANNEL_IDS, MIN_MESSAGE_COUNT


def create_table_from_figure(fig: go.Figure) -> html.Div:
    if not fig or not fig.data:
        return html.P("No data available", className="text-muted")
    
    rows = []
    headers = []
    
    for trace in fig.data:
        if hasattr(trace, 'x') and hasattr(trace, 'y'):
            trace_name = trace.name if trace.name else "Value"
            if not headers:
                headers = ["X", trace_name]
                rows = [[x, y] for x, y in zip(trace.x, trace.y)]
            else:
                headers.append(trace_name)
                for i, (x, y) in enumerate(zip(trace.x, trace.y)):
                    if i < len(rows):
                        rows[i].append(y)
    
    if not rows:
        return html.P("No data to display", className="text-muted")
    
    table_header = [html.Thead(html.Tr([html.Th(h) for h in headers]))]
    table_body = [html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows])]
    
    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        striped=True,
        responsive=True,
        className="table-sm",
        style={"maxHeight": "500px", "overflowY": "auto"}
    )


def render_view(content, view_slider: int, is_figure: bool = True):
    """
    Render content as graph or table based on slider value.
    view_slider: 0 = Graph, 1 = Table
    """
    if view_slider == 1 and is_figure:
        return create_table_from_figure(content)
    elif view_slider == 0 and is_figure:
        return dcc.Graph(figure=content, style={"height": "600px"})
    else:
        return content

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "24rem",
    "padding": "2rem 1rem",
    "backgroundColor": "#f8f9fa",
    "overflowY": "auto",
    "transition": "all 0.3s",
}

SIDEBAR_HIDDEN = {
    **SIDEBAR_STYLE,
    "left": "-24rem",
}

CONTENT_STYLE = {
    "marginLeft": "24rem",
    "padding": "2rem 1rem",
    "transition": "all 0.3s",
}

CONTENT_STYLE_FULL = {
    "marginLeft": "0rem",
    "padding": "2rem 1rem",
    "transition": "all 0.3s",
}

HEADER_STYLE = {
    "marginLeft": "24rem",
    "transition": "all 0.3s",
}

HEADER_STYLE_FULL = {
    "marginLeft": "0rem",
    "transition": "all 0.3s",
}


def resolve_mentions(text: str, user_id_to_name_map: dict, role_map: dict) -> str:
    """
    Convert Discord mentions (<@USER_ID> and <@&ROLE_ID>) to readable names.
    """
    import re
    
    # Replace user mentions <@USER_ID>
    def replace_user_mention(match):
        user_id = int(match.group(1))
        user_name = user_id_to_name_map.get(user_id, f"Unknown User ({user_id})")
        return f"@{user_name}"
    
    # Replace role mentions <@&ROLE_ID>
    def replace_role_mention(match):
        role_id = match.group(1)
        role_name = role_map.get(role_id, {}).get("name", f"Unknown Role ({role_id})")
        return f"@{role_name}"
    
    # Apply user mention replacement
    text = re.sub(r'<@!?(\d+)>', replace_user_mention, text)
    
    # Apply role mention replacement
    text = re.sub(r'<@&(\d+)>', replace_role_mention, text)
    
    return text


def register_callbacks(
    app: dash.Dash, df: pd.DataFrame, server_data_map: dict, mudae_channel_ids: list
) -> None:
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

    mudae_ids_set = set(int(id_str) for id_str in mudae_channel_ids)

    author_map = server_data_map.get("members", {})
    role_map = server_data_map.get("roles", {})

    user_id_to_name_map = {int(k): v["name"] for k, v in author_map.items()}
    user_id_to_original_name_map = {
        int(k): v["original_name"] for k, v in author_map.items()
    }
    name_to_user_id_map = {v["name"]: int(k) for k, v in author_map.items()}
    user_id_to_color_map = {k: v["top_role_color"] for k, v in author_map.items()}
    role_names_map = {k: v["name"] for k, v in role_map.items()}

    virgule_role_name = "Virgule du 4'"
    virgule_role_ids = {
        id for id, data in role_map.items() if data["name"] == virgule_role_name
    }

    virgule_author_ids = set()
    non_virgule_author_ids = set()
    current_member_ids_int = set()

    for uid, data in author_map.items():
        user_id_int = int(uid)
        current_member_ids_int.add(user_id_int)
        user_roles = set(str(r) for r in data.get("roles", []))

        if not virgule_role_ids.isdisjoint(user_roles):
            virgule_author_ids.add(user_id_int)
        else:
            non_virgule_author_ids.add(user_id_int)

    def is_light_color(hex_color: str) -> bool:
        try:
            if not isinstance(hex_color, str):
                return True
            hex_color = hex_color.lstrip("#")
            if len(hex_color) != 6:
                return True
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
            return luminance > 0.5
        except (ValueError, TypeError):
            return True

    @app.callback(
        Output("filter-sidebar", "style"),
        Output("page-content", "style"),
        Output("page-header", "style"),
        Output("sidebar-state-store", "data"),
        Input("open-filter-sidebar", "n_clicks"),
        State("sidebar-state-store", "data"),
    )
    def toggle_sidebar(n: int, is_open: bool) -> tuple:
        if n:
            is_open = not is_open

        if is_open:
            sidebar_style = SIDEBAR_STYLE
            content_style = CONTENT_STYLE
            header_style = HEADER_STYLE
        else:
            sidebar_style = SIDEBAR_HIDDEN
            content_style = CONTENT_STYLE_FULL
            header_style = HEADER_STYLE_FULL

        return sidebar_style, content_style, header_style, is_open

    @app.callback(
        Output("date-range-display", "children"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
    )
    def display_date_range_duration(start_date: str, end_date: str) -> str:
        if not start_date or not end_date:
            return ""
        start = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
        end = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
        delta = end - start
        years, days = divmod(delta.days, 365)
        return (
            f"{years} year(s), {days} day(s)" if years > 0 else f"{delta.days} day(s)"
        )

    @app.callback(
        Output("metric-store", "data"),
        Input("metric-dropdown", "value"),
    )
    def update_metric(metric: str) -> str:
        return metric

    @app.callback(
        Output("aggregation-store", "data"),
        Input("aggregation-dropdown", "value"),
    )
    def update_aggregation(aggregation: str) -> str:
        return aggregation

    @app.callback(
        Output("evolution-container", "children"),
        Output("user-dropdown", "options"),
        Output("user-dropdown", "value"),
        Output("dynamic-styles", "children"),
        Output("user-profile-card-container", "children"),
        Output("highlight-user-dropdown", "options"),
        Output("top-n-dropdown", "value"),
        Output("date-range-dropdown", "value"),
        Output("date-picker-range", "start_date"),
        Output("date-picker-range", "end_date"),
        Output("median-length-container", "children"),
        Output("distribution-container", "children"),
        Output("monthly-leaderboard-msg", "children"),
        Output("daily-leaderboard-msg-container", "children"),
        Output("mentioned-users-container", "children"),
        Output("replied-users-container", "children"),
        Output("top-reacted-messages", "children"),
        Input("user-dropdown", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("top-n-dropdown", "value"),
        Input("metric-store", "data"),
        Input("aggregation-store", "data"),
        Input("highlight-user-dropdown", "value"),
        Input("date-range-dropdown", "value"),
        Input("virgule-filter", "value"),
        Input("distribution-time-unit", "value"),
        Input("mudae-filter-switch", "value"),
        Input("evolution-view-slider", "value"),
        Input("distribution-view-slider", "value"),
        Input("median-length-view-slider", "value"),
        Input("mentioned-users-view-slider", "value"),
        Input("replied-users-view-slider", "value"),
        Input("length-aggregation-dropdown", "value"),
        Input("length-chart-type-dropdown", "value"),
        State("date-picker-range", "min_date_allowed"),
        State("date-picker-range", "max_date_allowed"),
    )
    def update_all(
        selected_user_names: list[str],
        start_date: str,
        end_date: str,
        top_n: int,
        metric_selected: str,
        aggregation_type: str,
        highlighted_user_name: str,
        date_range_period: str,
        virgule_filter: str,
        dist_time_unit: str,
        mudae_switch_value: bool,
        evolution_view_slider: int,
        distribution_view_slider: int,
        median_length_view_slider: int,
        mentioned_users_view_slider: int,
        replied_users_view_slider: int,
        length_aggregation: str,
        length_chart_type: str,
        min_date_allowed: str,
        max_date_allowed: str,
    ) -> tuple:
        ctx = dash.callback_context
        triggered_id = (
            ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        )
        
        print(f"[DEBUG] Callback triggered by: {triggered_id}")
        print(f"[DEBUG] DataFrame shape: {df.shape}")
        print(f"[DEBUG] selected_user_names: {selected_user_names}")
        print(f"[DEBUG] top_n: {top_n}")

        # S'assurer que les timestamps sont en UTC
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")

        if not mudae_switch_value:
            base_df = df[~df["channel_id"].isin(mudae_ids_set)].copy()
        else:
            base_df = df.copy()

        if virgule_filter == "virgule_only":
            author_id_pool = virgule_author_ids
        elif virgule_filter == "no_virgule":
            author_id_pool = non_virgule_author_ids
        else:
            author_id_pool = None

        if author_id_pool is not None:
            base_df = base_df[base_df["author_id"].isin(author_id_pool)]
        base_df["author_name"] = base_df["author_id"].map(user_id_to_name_map)
        base_df = base_df.dropna(subset=["author_name"])

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
                output_start_date = base_df["timestamp"].min().date()
                output_end_date = base_df["timestamp"].max().date()
            elif date_range_period == "current_year":
                output_start_date, output_end_date = (
                    today.replace(month=1, day=1).date(),
                    today.date(),
                )
            elif date_range_period == "last_365":
                output_start_date, output_end_date = (
                    (today - timedelta(days=365)).date(),
                    today.date(),
                )
            elif date_range_period == "last_6_months":
                output_start_date, output_end_date = (
                    (today - timedelta(days=180)).date(),
                    today.date(),
                )
            elif date_range_period == "last_3_months":
                output_start_date, output_end_date = (
                    (today - timedelta(days=90)).date(),
                    today.date(),
                )

        start_date_utc = pd.to_datetime(output_start_date, utc=True)
        end_date_utc = pd.to_datetime(output_end_date, utc=True).replace(
            hour=23, minute=59, second=59
        )

        dff = base_df[
            (base_df["timestamp"] >= start_date_utc)
            & (base_df["timestamp"] <= end_date_utc)
        ].copy()

        if not dff.empty:
            # Convert to Europe/Paris timezone for all temporal columns
            paris_timestamp = dff["timestamp"].dt.tz_convert("Europe/Paris")
            
            # Use string format instead of to_period to avoid timezone warning
            dff["month_year"] = paris_timestamp.dt.strftime("%Y-%m")
            dff["hour_of_day"] = paris_timestamp.dt.hour
            dff["weekday"] = paris_timestamp.dt.day_name()
            dff["month_name"] = paris_timestamp.dt.month_name()
            dff["year"] = paris_timestamp.dt.year
        else:
            for col in ["month_year", "hour_of_day", "weekday", "month_name", "year"]:
                dff[col] = pd.NA

        if metric_selected == "characters" and not dff.empty:
            user_counts_period = (
                dff.groupby("author_name")["len_content"]
                .sum()
                .sort_values(ascending=False)
            )
        elif not dff.empty:
            user_counts_period = dff["author_name"].value_counts()
        else:
            user_counts_period = pd.Series(dtype="int64")

        user_counts_all_time = base_df["author_name"].value_counts()
        sorted_users_by_count = user_counts_all_time.index.tolist()
        
        print(f"[DEBUG] base_df shape after filters: {base_df.shape}")
        print(f"[DEBUG] user_counts_all_time length: {len(user_counts_all_time)}")
        print(f"[DEBUG] Top 5 users: {user_counts_all_time.head().to_dict()}")

        # Au chargement initial ou changement de filtre, définir les utilisateurs par défaut
        if triggered_id is None or triggered_id in [
            "top-n-dropdown",
            "date-picker-range",
            "metric-store",
            "aggregation-store",
            "date-range-dropdown",
            "virgule-filter",
            "mudae-filter-switch",
        ]:
            if top_n != "custom":
                try:
                    n = int(top_n)
                    # Utiliser d'abord la période, sinon all-time
                    if not user_counts_period.empty:
                        user_value = user_counts_period.nlargest(n).index.tolist()
                    else:
                        user_value = user_counts_all_time.nlargest(n).index.tolist()
                except (ValueError, AttributeError):
                    user_value = user_counts_all_time.nlargest(10).index.tolist() if not user_counts_all_time.empty else []
            else:
                user_value = selected_user_names if selected_user_names else []
        else:
            # L'utilisateur a modifié la sélection manuellement
            user_value = selected_user_names if selected_user_names else []
        
        print(f"[DEBUG] Final user_value: {user_value}")
        
        user_options = []
        for author_name in sorted_users_by_count:
            message_count = user_counts_all_time.get(author_name, 0)
            if message_count < MIN_MESSAGE_COUNT:
                continue
                
            author_id = name_to_user_id_map.get(author_name)
            if not author_id:
                continue

            is_member = author_id in current_member_ids_int
            color = (
                user_id_to_color_map.get(str(author_id), "#6c757d")
                if is_member
                else "#6c757d"
            )

            user_options.append(
                {
                    "label": html.Div(
                        [
                            html.Span(
                                author_name,
                                style={
                                    "color": color,
                                    "textDecoration": (
                                        "line-through" if not is_member else "none"
                                    ),
                                    "fontWeight": "bold",
                                },
                            ),
                            html.Span(
                                user_id_to_original_name_map.get(
                                    author_id, author_name
                                ),
                                style={"display": "none"},
                            ),
                        ]
                    ),
                    "value": author_name,
                }
            )

        dff_filtered = dff[dff["author_name"].isin(user_value)] if user_value else dff

        style_rules = []
        for user in user_value:
            safe_user = str(user).replace('"', '\\"')
            user_id = name_to_user_id_map.get(user, "")
            is_member = user_id in current_member_ids_int

            bg_color = (
                user_id_to_color_map.get(str(user_id), "#6c757d")
                if is_member
                else "#f8f9fa"
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
        if highlighted_user_name:
            profile_card = create_user_profile_card(
                highlighted_user_name, dff, user_counts_period, metric_selected
            )

        highlight_options = [{"label": user, "value": user} for user in user_value]
        color_map = {
            user: user_id_to_color_map.get(
                str(name_to_user_id_map.get(user)), "#6c757d"
            )
            for user in user_value
        }

        empty_figure = go.Figure(
            layout={
                "template": "plotly_white",
                "annotations": [{"text": "No Data", "showarrow": False}],
            }
        )
        empty_leaderboard = html.P(
            "No data available for this period.",
            className="text-center text-muted p-4",
        )
        empty_list_component = html.Div(
            "No data available for this period.",
            className="text-center text-muted p-4",
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
                empty_figure,
                empty_figure,
                empty_figure,
                empty_list_component,
            )

        if aggregation_type == "cumulative":
            fig_evolution = create_cumulative_graph(
                dff_filtered, color_map, metric_selected, highlighted_user_name
            )
        else:
            fig_evolution = create_monthly_graph(
                dff_filtered, color_map, metric_selected, highlighted_user_name
            )

        fig_median_length = create_median_length_graph(dff_filtered, dff, color_map, length_aggregation, length_chart_type)
        fig_distribution = create_distribution_graph(
            dff_filtered,
            dff,
            user_counts_period,
            color_map,
            dist_time_unit,
            metric_selected,
        )
        fig_mentioned = create_most_mentioned_graph(
            dff,
            color_map,
            user_id_to_name_map,
            role_names_map,
            name_to_user_id_map,
            user_id_to_color_map,
        )
        fig_replied = create_most_replied_graph(
            dff,
            color_map,
            user_id_to_name_map,
            name_to_user_id_map,
            user_id_to_color_map,
        )
        top_reactions_component = create_top_reactions_list(
            dff, user_id_to_color_map, current_member_ids_int
        )

        # Use metric_selected to determine which leaderboards to show
        monthly_leaderboard = create_leaderboard(
            dff, "ME", "Months Won", "%B %Y", metric_selected
        )
        daily_leaderboard = create_daily_leaderboard(
            dff, metric_selected, start_date_utc, end_date_utc, color_map
        )

        evolution_content = render_view(fig_evolution, evolution_view_slider, True)
        distribution_content = render_view(fig_distribution, distribution_view_slider, True)
        median_length_content = render_view(fig_median_length, median_length_view_slider, True)
        mentioned_users_content = render_view(fig_mentioned, mentioned_users_view_slider, True)
        replied_users_content = render_view(fig_replied, replied_users_view_slider, True)

        return (
            evolution_content,
            user_options,
            user_value,
            final_styles,
            profile_card,
            highlight_options,
            new_top_n_value,
            new_date_range_period,
            output_start_date,
            output_end_date,
            median_length_content,
            distribution_content,
            monthly_leaderboard,
            daily_leaderboard,
            mentioned_users_content,
            replied_users_content,
            top_reactions_component,
        )

    def create_user_profile_card(
        user_name: str,
        dff: pd.DataFrame,
        user_counts_period: pd.Series,
        metric_selected: str,
    ) -> html.Div:
        user_df = dff[dff["author_name"] == user_name]
        if user_df.empty:
            return []

        if metric_selected == "characters":
            total_val = user_df["len_content"].sum()
            total_server_val = dff["len_content"].sum()
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
        dff_filtered: pd.DataFrame,
        color_map: dict,
        metric_selected: str,
        highlighted_user: str,
    ) -> go.Figure:
        if dff_filtered.empty:
            return go.Figure()

        if metric_selected == "characters":
            daily_data = (
                dff_filtered.set_index("timestamp")
                .groupby("author_name")
                .resample("D")["len_content"]
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
                dff_filtered.groupby(["author_name", "month_year"])["len_content"]
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

    def create_median_length_graph(
        dff_filtered: pd.DataFrame, dff: pd.DataFrame, color_map: dict, aggregation: str = "median", chart_type: str = "bar"
    ) -> go.Figure:
        if dff_filtered.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [
                        {"text": "Select users to display", "showarrow": False}
                    ],
                }
            )

        if chart_type == "box":
            # Box plot showing distribution of message lengths
            fig = go.Figure()
            
            users = dff_filtered["author_name"].unique()
            for user in users:
                user_data = dff_filtered[dff_filtered["author_name"] == user]["len_content"].dropna()
                if not user_data.empty:
                    fig.add_trace(
                        go.Box(
                            y=[user],
                            x=user_data.values,
                            orientation="h",
                            name=user,
                            marker=dict(color=color_map.get(user, "#6c757d")),
                            showlegend=False,
                        )
                    )
            
            fig.update_layout(
                xaxis_title="Message Length (characters)",
                yaxis_title="User",
                template="plotly_white",
                showlegend=False,
            )
            return fig
        
        # Bar chart mode
        if aggregation == "mean":
            length_values = (
                dff_filtered.dropna(subset=["len_content"])
                .groupby("author_name")["len_content"]
                .mean()
                .sort_values(ascending=True)
            )
            title_text = "Mean Characters per Message"
            trace_name = "Mean Length"
        else:
            length_values = (
                dff_filtered.dropna(subset=["len_content"])
                .groupby("author_name")["len_content"]
                .median()
                .sort_values(ascending=True)
            )
            title_text = "Median Characters per Message"
            trace_name = "Median Length"

        if length_values.empty:
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

        colors = [color_map.get(name, "#6c757d") for name in length_values.index]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=length_values.index,
                x=length_values.values,
                orientation="h",
                marker=dict(color=colors),
                name=trace_name,
            )
        )

        fig.update_layout(
            xaxis_title=title_text,
            yaxis_title="User",
            template="plotly_white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        return fig

    def create_distribution_graph(
        dff_filtered: pd.DataFrame,
        dff: pd.DataFrame,
        user_counts_period: pd.Series,
        color_map: dict,
        time_unit: str,
        metric_selected: str,
    ) -> go.Figure:
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
        elif time_unit == "day":
            x_col, x_label = "weekday", "Day of Week"
            categories = days_order
            dtick = 1
        elif time_unit == "month":
            x_col, x_label = "month_name", "Month of Year"
            categories = months_order
            dtick = 1
        else:
            x_col, x_label = "year", "Year"
            categories = sorted(dff[x_col].dropna().unique())
            dtick = 1

        dff_top = dff_top.copy()
        dff = dff.copy()
        dff_top["x_axis"] = dff_top[x_col]
        dff["x_axis"] = dff[x_col]

        if metric_selected == "characters":
            server_values = dff.groupby("x_axis")["len_content"].sum()
        else:
            server_values = dff.groupby("x_axis").size()

        server_values = server_values.reindex(categories).fillna(0)
        server_total = server_values.sum()
        server_percentage = (
            (server_values / server_total) * 100 if server_total > 0 else 0
        )

        all_user_data = []
        for user in top_users:
            user_df = dff_top[dff_top["author_name"] == user]

            if metric_selected == "characters":
                user_values_single = user_df.groupby("x_axis")["len_content"].sum()
            else:
                user_values_single = user_df.groupby("x_axis").size()

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

    def create_leaderboard(
        dff: pd.DataFrame,
        period: str,
        metric_name: str,
        date_format: str,
        metric_selected: str,
    ) -> html.Ul:
        if dff.empty:
            return html.P("No data.", className="text-center p-3")

        # Convert to Paris timezone before grouping
        dff_paris = dff.copy()
        dff_paris["timestamp_paris"] = dff_paris["timestamp"].dt.tz_convert("Europe/Paris")

        if metric_selected == "characters":
            resampled = (
                dff_paris.groupby([pd.Grouper(key="timestamp_paris", freq=period), "author_name"])[
                    "len_content"
                ]
                .sum()
                .reset_index(name="value")
            )
            resampled.rename(columns={"timestamp_paris": "timestamp"}, inplace=True)
        else:
            resampled = (
                dff_paris.groupby([pd.Grouper(key="timestamp_paris", freq=period), "author_name"])
                .size()
                .reset_index(name="value")
            )
            resampled.rename(columns={"timestamp_paris": "timestamp"}, inplace=True)

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

    def create_daily_leaderboard(
        dff: pd.DataFrame,
        metric_selected: str,
        start_date_utc: pd.Timestamp,
        end_date_utc: pd.Timestamp,
        color_map: dict,
    ) -> html.Div:
        if dff.empty:
            return html.P("No data.", className="text-center p-3")

        # Convert to Paris timezone before grouping by day
        dff_paris = dff.copy()
        dff_paris["timestamp_paris"] = dff_paris["timestamp"].dt.tz_convert("Europe/Paris")

        if metric_selected == "characters":
            resampled = (
                dff_paris.groupby([pd.Grouper(key="timestamp_paris", freq="D"), "author_name"])[
                    "len_content"
                ]
                .sum()
                .reset_index(name="value")
            )
            resampled.rename(columns={"timestamp_paris": "timestamp"}, inplace=True)
        else:
            resampled = (
                dff_paris.groupby([pd.Grouper(key="timestamp_paris", freq="D"), "author_name"])
                .size()
                .reset_index(name="value")
            )
            resampled.rename(columns={"timestamp_paris": "timestamp"}, inplace=True)

        if resampled.empty:
            return html.P("Not enough data.", className="text-center p-3")

        winners = resampled.loc[resampled.groupby("timestamp")["value"].idxmax()]

        # Always show calendar view now
        winners = winners.copy()
        winners["date"] = winners["timestamp"].dt.date
        winner_map = winners.set_index("date")["author_name"].to_dict()

        color_winner_map = {
            date: color_map.get(name, "#6c757d")
            for date, name in winner_map.items()
        }

        return html.Div(
            generate_calendars(
                start_date_utc, end_date_utc, winner_map, color_winner_map
            ),
            style={"maxHeight": "500px", "overflowY": "auto"},
        )

    def generate_calendars(
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        winner_map: dict,
        color_map: dict,
    ) -> list:
        start = start_date.date()
        end = end_date.date()

        if (end - start).days > 730:
            return html.P(
                "Calendar view is not available for periods longer than 2 years.",
                className="text-center text-danger",
            )

        months = []
        current_date = datetime(start.year, start.month, 1).date()

        while current_date <= end:
            month_html = [
                html.H6(current_date.strftime("%B %Y"), className="text-center")
            ]
            cal = calendar.monthcalendar(current_date.year, current_date.month)

            header = html.Tr(
                [
                    html.Th(day, style={"width": "14.28%"})
                    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                ]
            )
            weeks = []

            for week in cal:
                week_html = []
                for day in week:
                    if day == 0:
                        week_html.append(html.Td("", className="calendar-day empty"))
                    else:
                        date_obj = datetime(
                            current_date.year, current_date.month, day
                        ).date()
                        winner = winner_map.get(date_obj)

                        if date_obj < start or date_obj > end:
                            week_html.append(
                                html.Td(str(day), className="calendar-day disabled")
                            )
                        elif winner:
                            cell_color = color_map.get(date_obj, "#f8f9fa")
                            cell_style = {
                                "backgroundColor": cell_color,
                                "color": (
                                    "black" if is_light_color(cell_color) else "white"
                                ),
                                "fontWeight": "bold",
                                "overflow": "hidden",
                                "textOverflow": "ellipsis",
                                "fontSize": "0.8rem",
                                "padding": "2px",
                            }
                            week_html.append(
                                html.Td(
                                    [
                                        html.Div(day, className="day-number"),
                                        html.Div(winner),
                                    ],
                                    className="calendar-day winner",
                                    style=cell_style,
                                    title=f"{date_obj.strftime('%d %B')}: {winner}",
                                )
                            )
                        else:
                            week_html.append(
                                html.Td(str(day), className="calendar-day")
                            )
                weeks.append(html.Tr(week_html))

            month_table = html.Div(
                [
                    *month_html,
                    dbc.Table(
                        children=[html.Thead(header), html.Tbody(weeks)],
                        bordered=True,
                        size="sm",
                        className="calendar-table",
                    ),
                ]
            )
            months.append(month_table)

            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1).date()
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1).date()

        return months

    def create_most_mentioned_graph(
        dff: pd.DataFrame,
        color_map: dict,
        user_id_to_name_map: dict,
        role_names_map: dict,
        name_to_user_id_map: dict,
        user_id_to_color_map: dict,
    ) -> go.Figure:
        if dff.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [{"text": "No Data", "showarrow": False}],
                }
            )

        mention_counts = {}

        user_mentions_list = dff["mentions"].apply(
            lambda x: (
                json.loads(x)
                if isinstance(x, str)
                else (x if isinstance(x, list) else [])
            )
        )
        user_mention_df = user_mentions_list.explode().dropna()
        if not user_mention_df.empty:
            user_mention_id_counts = user_mention_df.astype(str).value_counts()
            for user_id, count in user_mention_id_counts.items():
                mention_counts[f"user_{user_id}"] = (
                    mention_counts.get(f"user_{user_id}", 0) + count
                )

        role_mentions_list = dff["mentioned_role_ids"].apply(
            lambda x: (
                json.loads(x)
                if isinstance(x, str)
                else (x if isinstance(x, list) else [])
            )
        )
        role_mention_df = role_mentions_list.explode().dropna()
        if not role_mention_df.empty:
            role_mention_id_counts = role_mention_df.astype(str).value_counts()
            for role_id, count in role_mention_id_counts.items():
                mention_counts[f"role_{role_id}"] = (
                    mention_counts.get(f"role_{role_id}", 0) + count
                )

        if not mention_counts:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "annotations": [{"text": "No mentions found", "showarrow": False}],
                }
            )

        mentions_df = pd.DataFrame(
            list(mention_counts.items()), columns=["id", "count"]
        )

        def map_name(id_str: str) -> Optional[str]:
            type_str, id_val = id_str.split("_", 1)
            if type_str == "user":
                try:
                    return user_id_to_name_map.get(int(id_val))
                except (ValueError, TypeError):
                    return None
            elif type_str == "role":
                name = role_names_map.get(id_val)
                return f"@{name}" if name else None
            return None

        mentions_df["name"] = mentions_df["id"].apply(map_name)
        mentions_df = mentions_df.dropna(subset=["name"])

        if mentions_df.empty:
            return go.Figure(
                layout={
                    "template": "plotly_white",
                    "xaxis": {"visible": False},
                    "yaxis": {"visible": False},
                    "annotations": [
                        {
                            "text": "No mentions for known users/roles",
                            "showarrow": False,
                            "xref": "paper",
                            "yref": "paper",
                            "x": 0.5,
                            "y": 0.5,
                            "font": {"size": 16},
                        }
                    ],
                }
            )

        mentions_final = (
            mentions_df.groupby("name")["count"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
        )

        colors = []
        for name in mentions_final.index:
            if name.startswith("@"):
                colors.append("#7289da")
            else:
                user_id = name_to_user_id_map.get(name)
                colors.append(user_id_to_color_map.get(str(user_id), "#6c757d"))

        fig = go.Figure(
            data=[
                go.Bar(
                    y=mentions_final.index,
                    x=mentions_final.values,
                    orientation="h",
                    marker=dict(color=colors),
                )
            ]
        )

        fig.update_layout(
            xaxis_title="Number of @ Mentions (Users & Roles)",
            yaxis_title=None,
            yaxis={"categoryorder": "total ascending"},
            template="plotly_white",
            margin=dict(l=150),
        )
        return fig

    def create_top_reactions_list(
        dff: pd.DataFrame, user_id_to_color_map: dict, current_member_ids_int: set
    ) -> html.Ul:
        if dff.empty or "total_reaction_count" not in dff.columns:
            return html.P(
                "No reaction data available for this period.",
                className="text-center text-muted p-4",
            )

        top_reacted = dff.sort_values(by="total_reaction_count", ascending=False).head(
            10
        )
        top_reacted = top_reacted[top_reacted["total_reaction_count"] > 0]

        if top_reacted.empty:
            return html.P(
                "No messages with reactions found.",
                className="text-center text-muted p-4",
            )

        list_items = []
        for index, row in top_reacted.iterrows():
            author_id = row["author_id"]
            author_name = user_id_to_name_map.get(author_id, f"ID: {author_id}")
            is_member = author_id in current_member_ids_int
            author_color = (
                user_id_to_color_map.get(str(author_id), "#6c757d")
                if is_member
                else "#6c757d"
            )

            message_content = row["content"]
            # Resolve mentions in message content
            message_content = resolve_mentions(message_content, user_id_to_name_map, role_map)
            if len(message_content) > 200:
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
                                ),
                                html.A(
                                    "Go to message",
                                    href=row["jump_url"],
                                    target="_blank",
                                    className="small text-muted",
                                ),
                            ],
                        ),
                        html.Span(
                            [
                                html.Span(
                                    (
                                        row.get("top_reaction_emoji", "")
                                        if row.get("top_reaction_emoji", "")
                                        and ":"
                                        not in str(row.get("top_reaction_emoji", ""))
                                        else ""
                                    ),
                                    className="me-2",
                                    style={"fontSize": "1.2em"},
                                ),
                                f"{int(row['total_reaction_count'])} reactions",
                            ],
                            className="badge bg-primary rounded-pill fs-6",
                        ),
                    ],
                )
            )

        return html.Ul(list_items, className="list-group")
