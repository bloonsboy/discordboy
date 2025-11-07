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
            html.H2("Filters", className="display-6"),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Top Users", className="form-label fw-bold"),
                            dcc.Dropdown(
                                id="top-n-dropdown",
                                options=[
                                    {"label": "Top 5", "value": 5},
                                    {"label": "Top 10", "value": 10},
                                    {"label": "Top 20", "value": 20},
                                    {"label": "Top 50", "value": 50},
                                    {"label": "Top 100", "value": 100},
                                    {"label": "Custom", "value": "custom"},
                                ],
                                value=5,
                                clearable=False,
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Users", className="form-label fw-bold"),
                            dcc.Dropdown(
                                id="user-dropdown",
                                multi=True,
                                placeholder="Select users...",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Highlight User", className="form-label fw-bold"
                            ),
                            dcc.Dropdown(
                                id="highlight-user-dropdown",
                                multi=False,
                                placeholder="Select a user to highlight...",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Time Period", className="form-label fw-bold"),
                            dcc.Dropdown(
                                id="date-range-dropdown",
                                options=[
                                    {"label": "Custom", "value": "custom"},
                                    {
                                        "label": "Current Year",
                                        "value": "current_year",
                                    },
                                    {
                                        "label": "Last 365 Days",
                                        "value": "last_365",
                                    },
                                    {
                                        "label": "Last 6 Months",
                                        "value": "last_6_months",
                                    },
                                    {
                                        "label": "Last 3 Months",
                                        "value": "last_3_months",
                                    },
                                    {"label": "All-time", "value": "all-time"},
                                ],
                                value="last_365",
                                clearable=False,
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Date Range", className="form-label fw-bold"),
                            dcc.DatePickerRange(
                                id="date-picker-range",
                                min_date_allowed=min_date,
                                max_date_allowed=max_date,
                                start_date=(
                                    datetime.now() - timedelta(days=365)
                                ).date(),
                                end_date=datetime.now().date(),
                                display_format="DD/MM/YYYY",
                                className="w-100",
                            ),
                            html.Div(
                                id="date-range-display",
                                className="text-muted small mt-1",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Analysis Metric", className="form-label fw-bold"
                            ),
                            dbc.RadioItems(
                                id="metric-selector",
                                options=[
                                    {"label": "Message Count", "value": "messages"},
                                    {
                                        "label": "Character Count",
                                        "value": "characters",
                                    },
                                ],
                                value="messages",
                                inline=True,
                                labelClassName="me-3",
                                inputClassName="me-1",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Special Filter (Role)", className="form-label fw-bold"
                            ),
                            dbc.RadioItems(
                                id="virgule-filter",
                                options=[
                                    {"label": "Everyone", "value": "everyone"},
                                    {"label": "Virgule Only", "value": "virgule_only"},
                                    {"label": "No Virgule", "value": "no_virgule"},
                                ],
                                value="everyone",
                                inline=True,
                                labelClassName="me-3",
                                inputClassName="me-1",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Channel Filter", className="form-label fw-bold"
                            ),
                            dbc.Switch(
                                id="mudae-filter-switch",
                                label="Include Mudae Channels",
                                value=False,
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
        ],
        id="filter-sidebar",
        style=SIDEBAR_HIDDEN,
    )

    header = dbc.Navbar(
        dbc.Container(
            [
                dbc.Button(
                    html.I(className="fas fa-bars"),
                    id="open-filter-sidebar",
                    n_clicks=0,
                    className="me-2",
                    color="light",
                ),
                html.A(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.I(
                                    className="fab fa-discord",
                                    style={"color": "white", "fontSize": "30px"},
                                )
                            ),
                            dbc.Col(
                                dbc.NavbarBrand(
                                    "Discord Activity Dashboard", className="ms-2"
                                )
                            ),
                        ],
                        align="center",
                        className="g-0",
                    ),
                    href="#",
                    style={"textDecoration": "none"},
                ),
            ]
        ),
        id="page-header",
        style=HEADER_STYLE_FULL,
        color="dark",
        dark=True,
        className="mb-4",
    )

    content = html.Div(
        [
            dcc.Store(id="sidebar-state-store", data=False),
            dcc.Markdown(id="dynamic-styles", style={"display": "none"}),
            html.Div(id="user-profile-card-container"),
            html.Div(
                [
                    html.H3("Temporal Analysis"),
                    html.Hr(),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dcc.Slider(
                                    id="evolution-graph-selector",
                                    min=0,
                                    max=1,
                                    step=None,
                                    marks={0: "Cumulative", 1: "Monthly"},
                                    value=0,
                                    className="mb-4",
                                ),
                                dcc.Loading(
                                    dcc.Graph(
                                        id="evolution-graph",
                                        style={"height": "600px"},
                                    )
                                ),
                            ]
                        ),
                        className="shadow-sm mb-4",
                    ),
                ],
                className="mb-5",
            ),
            html.Div(
                [
                    html.H3("Message & Interaction Analysis"),
                    html.Hr(),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.RadioItems(
                                    id="distribution-time-unit",
                                    options=[
                                        {"label": "Hour of Day", "value": "hour"},
                                        {"label": "Day of Week", "value": "weekday"},
                                        {"label": "Month", "value": "month"},
                                        {"label": "Year", "value": "year"},
                                    ],
                                    value="hour",
                                    inline=True,
                                    className="mb-3",
                                ),
                                dcc.Loading(dcc.Graph(id="distribution-graph")),
                            ]
                        ),
                        className="shadow-sm mb-4",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                "Median Message Length (Characters)",
                                                className="card-title",
                                            ),
                                            dcc.Loading(
                                                dcc.Graph(id="median-length-graph")
                                            ),
                                        ]
                                    ),
                                    className="shadow-sm h-100",
                                ),
                                md=6,
                                className="mb-4",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                "Most Mentioned Users (@)",
                                                className="card-title",
                                            ),
                                            dcc.Loading(
                                                dcc.Graph(id="mentioned-users-graph")
                                            ),
                                        ]
                                    ),
                                    className="shadow-sm h-100",
                                ),
                                md=6,
                                className="mb-4",
                            ),
                        ],
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5(
                                    "Top 10 Reacted Messages (Total Reactions)",
                                    className="card-title",
                                ),
                                dcc.Loading(html.Div(id="top-reacted-messages")),
                            ]
                        ),
                        className="shadow-sm mb-4",
                    ),
                ],
                className="mb-5",
            ),
            html.Div(
                [
                    html.H3("Leaderboards"),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "Daily Champions View Mode",
                                        className="form-label fw-bold",
                                    ),
                                    dbc.RadioItems(
                                        id="daily-leaderboard-toggle",
                                        options=[
                                            {"label": "List", "value": "list"},
                                            {"label": "Calendar", "value": "calendar"},
                                        ],
                                        value="list",
                                        inline=True,
                                        className="mb-3",
                                    ),
                                ],
                                width=12,
                            )
                        ]
                    ),
                    dcc.Tabs(
                        id="leaderboard-tabs",
                        className="mb-3",
                        children=[
                            dbc.Tab(
                                label="By Message Count",
                                tab_id="msg",
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Card(
                                                    [
                                                        dbc.CardHeader(
                                                            html.H5(
                                                                "Daily Champions (Messages)",
                                                                className="card-title mb-0",
                                                            )
                                                        ),
                                                        dbc.CardBody(
                                                            dcc.Loading(
                                                                html.Div(
                                                                    id="daily-leaderboard-msg-container"
                                                                )
                                                            )
                                                        ),
                                                    ],
                                                    className="shadow-sm h-100",
                                                ),
                                                md=6,
                                                className="mb-4",
                                            ),
                                            dbc.Col(
                                                create_leaderboard_card(
                                                    "Monthly Champions (Messages)",
                                                    "monthly-leaderboard-msg",
                                                ),
                                                md=6,
                                                className="mb-4",
                                            ),
                                        ]
                                    )
                                ],
                            ),
                            dbc.Tab(
                                label="By Character Count",
                                tab_id="char",
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Card(
                                                    [
                                                        dbc.CardHeader(
                                                            html.H5(
                                                                "Daily Champions (Characters)",
                                                                className="card-title mb-0",
                                                            )
                                                        ),
                                                        dbc.CardBody(
                                                            dcc.Loading(
                                                                html.Div(
                                                                    id="daily-leaderboard-char-container"
                                                                )
                                                            )
                                                        ),
                                                    ],
                                                    className="shadow-sm h-100",
                                                ),
                                                md=6,
                                                className="mb-4",
                                            ),
                                            dbc.Col(
                                                create_leaderboard_card(
                                                    "Monthly Champions (Characters)",
                                                    "monthly-leaderboard-char",
                                                ),
                                                md=6,
                                                className="mb-4",
                                            ),
                                        ]
                                    )
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        id="page-content",
        style=CONTENT_STYLE_FULL,
    )

    return html.Div(
        [
            dcc.Location(id="url"),
            header,
            sidebar,
            content,
        ]
    )


def create_leaderboard_card(title: str, container_id: str) -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.H5(title, className="card-title mb-0")),
            dbc.CardBody(dcc.Loading(html.Div(id=container_id))),
        ],
        className="shadow-sm h-100",
    )
