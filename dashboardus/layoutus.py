from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

from .callbackus import CONTENT_STYLE_FULL, HEADER_STYLE_FULL, SIDEBAR_HIDDEN


def create_layout(df: pd.DataFrame) -> html.Div:
    if df.empty:
        min_date = datetime.now().date()
        max_date = datetime.now().date()
    else:
        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()

    sidebar = html.Div(
        [
            html.Div(
                [
                    html.H2("Filters", className="h4 mb-3", style={"fontWeight": "300"}),
                ],
            ),
            html.Hr(style={"borderColor": "#e0e0e0"}),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            html.Label("Top Users", className="form-label", style={"fontSize": "0.9rem", "color": "#666"}),
                            dcc.Dropdown(
                                id="top-n-dropdown",
                                options=[
                                    {"label": "Top 5", "value": 5},
                                    {"label": "Top 10", "value": 10},
                                    {"label": "Top 20", "value": 20},
                                    {"label": "Top 50", "value": 50},
                                    {"label": "Top 100", "value": 100},
                                ],
                                value=10,
                                clearable=False,
                                style={"fontSize": "0.9rem"},
                            ),
                            html.Div(className="mb-3"),
                            html.Label("Select Specific Users", className="form-label mt-3", style={"fontSize": "0.9rem", "color": "#666"}),
                            dcc.Dropdown(
                                id="user-dropdown",
                                multi=True,
                                placeholder="Search users...",
                                style={"fontSize": "0.9rem"},
                            ),
                            html.Div(className="mb-3"),
                            html.Label("Highlight User", className="form-label mt-3", style={"fontSize": "0.9rem", "color": "#666"}),
                            dcc.Dropdown(
                                id="highlight-user-dropdown",
                                multi=False,
                                placeholder="Highlight a user...",
                                style={"fontSize": "0.9rem"},
                            ),
                        ],
                        title="Users Selection",
                        item_id="users",
                    ),
                    dbc.AccordionItem(
                        [
                            html.Label("Time Period", className="form-label", style={"fontSize": "0.9rem", "color": "#666"}),
                            dcc.Dropdown(
                                id="date-range-dropdown",
                                options=[
                                    {"label": "Custom", "value": "custom"},
                                    {"label": "Current Year", "value": "current_year"},
                                    {"label": "Last 365 Days", "value": "last_365"},
                                    {"label": "Last 6 Months", "value": "last_6_months"},
                                    {"label": "Last 3 Months", "value": "last_3_months"},
                                    {"label": "All-time", "value": "all-time"},
                                ],
                                value="all-time",
                                clearable=False,
                                style={"fontSize": "0.9rem"},
                            ),
                            html.Div(className="mb-3"),
                            html.Label("Custom Date Range", className="form-label mt-3", style={"fontSize": "0.9rem", "color": "#666"}),
                            dcc.DatePickerRange(
                                id="date-picker-range",
                                min_date_allowed=min_date,
                                max_date_allowed=max_date,
                                start_date=(datetime.now() - timedelta(days=365)).date(),
                                end_date=datetime.now().date(),
                                display_format="DD/MM/YYYY",
                                className="w-100",
                            ),
                            html.Div(id="date-range-display", className="text-muted small mt-2"),
                        ],
                        title="Time Period",
                        item_id="time",
                    ),
                    dbc.AccordionItem(
                        [
                            html.Label("Role Filter", className="form-label", style={"fontSize": "0.9rem", "color": "#666"}),
                            dbc.RadioItems(
                                id="virgule-filter",
                                options=[
                                    {"label": "Everyone", "value": "everyone"},
                                    {"label": "Virgule Only", "value": "virgule_only"},
                                    {"label": "No Virgule", "value": "no_virgule"},
                                ],
                                value="everyone",
                                className="mb-3",
                            ),
                            html.Label("Channel Options", className="form-label mt-3", style={"fontSize": "0.9rem", "color": "#666"}),
                            dbc.Switch(
                                id="mudae-filter-switch",
                                label="Include Mudae Channels",
                                value=False,
                            ),
                        ],
                        title="Options & Filters",
                        item_id="options",
                    ),
                ],
                start_collapsed=False,
                always_open=True,
                flush=True,
            ),
        ],
        id="filter-sidebar",
        style=SIDEBAR_HIDDEN,
    )

    header = html.Div(
        [
            dbc.Button(
                "☰",
                id="open-filter-sidebar",
                n_clicks=0,
                className="btn-sm",
                style={
                    "background": "white",
                    "border": "1px solid #ddd",
                    "color": "#333",
                    "fontSize": "1.5rem",
                    "padding": "0.25rem 0.75rem",
                    "marginRight": "1rem",
                },
            ),
            html.H1(
                "Discord Activity Dashboard",
                style={
                    "fontWeight": "200",
                    "fontSize": "1.75rem",
                    "margin": "0",
                    "color": "#333",
                    "display": "inline-block",
                },
            ),
        ],
        id="page-header",
        style={
            **HEADER_STYLE_FULL,
            "background": "white",
            "borderBottom": "1px solid #e0e0e0",
            "padding": "1rem 2rem",
            "marginBottom": "0",
        },
    )

    content = html.Div(
        [
            dcc.Store(id="sidebar-state-store", data=False),
            dcc.Store(id="metric-store", data="messages"),
            dcc.Store(id="aggregation-store", data="cumulative"),
            dcc.Markdown(id="dynamic-styles", style={"display": "none"}),
            html.Div(id="user-profile-card-container"),
            
            # Temporal Analysis Section
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(
                                "Temporal Analysis",
                                style={
                                    "fontWeight": "300",
                                    "fontSize": "1.5rem",
                                    "marginBottom": "0.5rem",
                                    "color": "#333",
                                },
                            ),
                            # Interactive metric/aggregation dropdowns
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span("Showing ", style={"color": "#333", "fontSize": "1rem", "fontWeight": "500", "marginRight": "0.5rem"}),
                                            dcc.Dropdown(
                                                id="metric-dropdown",
                                                options=[
                                                    {"label": "Messages", "value": "messages"},
                                                    {"label": "Characters", "value": "characters"},
                                                ],
                                                value="messages",
                                                clearable=False,
                                                style={"width": "150px", "display": "inline-block"},
                                            ),
                                        ],
                                        style={"display": "inline-flex", "alignItems": "center", "marginRight": "1rem"},
                                    ),
                                    html.Div(
                                        [
                                            html.Span(" by ", style={"color": "#333", "fontSize": "1rem", "fontWeight": "500", "marginRight": "0.5rem"}),
                                            dcc.Dropdown(
                                                id="aggregation-dropdown",
                                                options=[
                                                    {"label": "Cumulative", "value": "cumulative"},
                                                    {"label": "Monthly", "value": "monthly"},
                                                ],
                                                value="cumulative",
                                                clearable=False,
                                                style={"width": "150px", "display": "inline-block"},
                                            ),
                                        ],
                                        style={"display": "inline-flex", "alignItems": "center"},
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center", "marginBottom": "1.5rem"},
                            ),
                        ],
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="evolution-view-slider",
                                        min=0,
                                        max=1,
                                        step=1,
                                        value=0,
                                        marks={0: "Graph", 1: "Table"},
                                        className="mb-3",
                                    ),
                                ],
                                style={"width": "200px", "marginBottom": "1rem"},
                            ),
                            dcc.Loading(
                                html.Div(id="evolution-container"),
                                type="circle",
                                color="#007bff",
                            ),
                        ],
                        style={
                            "background": "white",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "8px",
                            "padding": "1.5rem",
                            "marginBottom": "2rem",
                        },
                    ),
                ],
            ),
            
            # Message & Interaction Analysis
            html.Div(
                [
                    html.H2(
                        "Message & Interaction Analysis",
                        style={
                            "fontWeight": "300",
                            "fontSize": "1.5rem",
                            "marginBottom": "1.5rem",
                            "color": "#333",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span("Time granularity: ", style={"color": "#333", "fontSize": "1rem", "fontWeight": "500", "marginRight": "0.5rem"}),
                                            dcc.Dropdown(
                                                id="distribution-time-unit",
                                                options=[
                                                    {"label": "Hour of Day", "value": "hour"},
                                                    {"label": "Day of Week", "value": "day"},
                                                    {"label": "Month", "value": "month"},
                                                    {"label": "Year", "value": "year"},
                                                ],
                                                value="hour",
                                                clearable=False,
                                                style={"width": "180px", "display": "inline-block"},
                                            ),
                                        ],
                                        style={"display": "inline-flex", "alignItems": "center", "marginBottom": "1rem"},
                                    ),
                                    html.Div(
                                        [
                                            dcc.Slider(
                                                id="distribution-view-slider",
                                                min=0,
                                                max=1,
                                                step=1,
                                                value=0,
                                                marks={0: "Graph", 1: "Table"},
                                                className="mb-3",
                                            ),
                                        ],
                                        style={"width": "200px", "marginBottom": "1rem"},
                                    ),
                                ],
                            ),
                            dcc.Loading(
                                html.Div(id="distribution-container"),
                                type="circle",
                                color="#007bff",
                            ),
                        ],
                        style={
                            "background": "white",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "8px",
                            "padding": "1.5rem",
                            "marginBottom": "2rem",
                        },
                    ),
                    
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        html.H4("Message Length", style={"fontWeight": "300", "fontSize": "1.1rem", "marginBottom": "1rem"}),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.Span("Type: ", style={"color": "#333", "fontSize": "0.9rem", "fontWeight": "500", "marginRight": "0.5rem"}),
                                                        dcc.Dropdown(
                                                            id="length-chart-type-dropdown",
                                                            options=[
                                                                {"label": "Bar Chart", "value": "bar"},
                                                                {"label": "Box Plot", "value": "box"},
                                                            ],
                                                            value="bar",
                                                            clearable=False,
                                                            style={"width": "120px", "display": "inline-block", "marginRight": "1rem"},
                                                        ),
                                                        html.Span("Aggregation: ", style={"color": "#333", "fontSize": "0.9rem", "fontWeight": "500", "marginRight": "0.5rem"}),
                                                        dcc.Dropdown(
                                                            id="length-aggregation-dropdown",
                                                            options=[
                                                                {"label": "Median", "value": "median"},
                                                                {"label": "Mean", "value": "mean"},
                                                            ],
                                                            value="median",
                                                            clearable=False,
                                                            style={"width": "120px", "display": "inline-block"},
                                                        ),
                                                    ],
                                                    style={"display": "inline-flex", "alignItems": "center", "marginBottom": "1rem"},
                                                ),
                                                dcc.Slider(
                                                    id="median-length-view-slider",
                                                    min=0,
                                                    max=1,
                                                    step=1,
                                                    value=0,
                                                    marks={0: "Graph", 1: "Table"},
                                                    className="mb-3",
                                                ),
                                            ],
                                            style={"width": "200px", "marginBottom": "1rem"},
                                        ),
                                        dcc.Loading(html.Div(id="median-length-container")),
                                    ],
                                    style={
                                        "background": "white",
                                        "border": "1px solid #e0e0e0",
                                        "borderRadius": "8px",
                                        "padding": "1.5rem",
                                    },
                                ),
                                md=6,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.H4("Most Mentioned Users", style={"fontWeight": "300", "fontSize": "1.1rem", "marginBottom": "1rem"}),
                                        html.Div(
                                            [
                                                dcc.Slider(
                                                    id="mentioned-users-view-slider",
                                                    min=0,
                                                    max=1,
                                                    step=1,
                                                    value=0,
                                                    marks={0: "Graph", 1: "Table"},
                                                    className="mb-3",
                                                ),
                                            ],
                                            style={"width": "200px", "marginBottom": "1rem"},
                                        ),
                                        dcc.Loading(html.Div(id="mentioned-users-container")),
                                    ],
                                    style={
                                        "background": "white",
                                        "border": "1px solid #e0e0e0",
                                        "borderRadius": "8px",
                                        "padding": "1.5rem",
                                    },
                                ),
                                md=6,
                            ),
                        ],
                        className="mb-4",
                    ),
                    
                    html.Div(
                        [
                            html.H4("Top 10 Reacted Messages", style={"fontWeight": "300", "fontSize": "1.1rem", "marginBottom": "1rem"}),
                            dcc.Loading(html.Div(id="top-reacted-messages")),
                        ],
                        style={
                            "background": "white",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "8px",
                            "padding": "1.5rem",
                            "marginBottom": "2rem",
                        },
                    ),
                ],
            ),
            
            # Leaderboards
            html.Div(
                [
                    html.H2(
                        "Leaderboards",
                        style={
                            "fontWeight": "300",
                            "fontSize": "1.5rem",
                            "marginBottom": "1.5rem",
                            "color": "#333",
                        },
                    ),
                    
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        html.H4("Monthly Champions", style={"fontWeight": "300", "fontSize": "1.1rem", "marginBottom": "1rem"}),
                                        dcc.Loading(html.Div(id="monthly-leaderboard-msg")),
                                    ],
                                    style={
                                        "background": "white",
                                        "border": "1px solid #e0e0e0",
                                        "borderRadius": "8px",
                                        "padding": "1.5rem",
                                    },
                                ),
                                md=6,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.H4("Daily Champions", style={"fontWeight": "300", "fontSize": "1.1rem", "marginBottom": "1rem"}),
                                        dcc.Loading(html.Div(id="daily-leaderboard-msg-container")),
                                    ],
                                    style={
                                        "background": "white",
                                        "border": "1px solid #e0e0e0",
                                        "borderRadius": "8px",
                                        "padding": "1.5rem",
                                    },
                                ),
                                md=6,
                            ),
                        ],
                        className="mb-4",
                    ),
                ],
            ),
        ],
        id="page-content",
        style={**CONTENT_STYLE_FULL, "background": "#f8f9fa", "padding": "2rem"},
    )

    return html.Div([dcc.Location(id="url"), sidebar, header, content])
