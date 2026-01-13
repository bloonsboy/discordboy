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
                    html.H2(
                        [html.I(className="fas fa-filter me-2"), "Filters"],
                        className="display-6 mb-0",
                    ),
                    html.P(
                        "Customize your analysis", className="text-muted small mb-3"
                    ),
                ],
            ),
            html.Hr(),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            html.Label("Top Users", className="form-label"),
                            dcc.Dropdown(
                                id="top-n-dropdown",
                                options=[
                                    {"label": "🏆 Top 5", "value": 5},
                                    {"label": "🏆 Top 10", "value": 10},
                                    {"label": "🏆 Top 20", "value": 20},
                                    {"label": "🏆 Top 50", "value": 50},
                                    {"label": "🏆 Top 100", "value": 100},
                                ],
                                value=10,
                                clearable=False,
                            ),
                            html.Div(className="mb-3"),
                            html.Label(
                                "Select Specific Users", className="form-label mt-3"
                            ),
                            dcc.Dropdown(
                                id="user-dropdown",
                                multi=True,
                                placeholder="🔍 Search users...",
                            ),
                            html.Div(className="mb-3"),
                            html.Label("Highlight User", className="form-label mt-3"),
                            dcc.Dropdown(
                                id="highlight-user-dropdown",
                                multi=False,
                                placeholder="✨ Highlight a user...",
                            ),
                        ],
                        title="👥 Users Selection",
                        item_id="users",
                    ),
                    dbc.AccordionItem(
                        [
                            html.Label("Time Period", className="form-label"),
                            dcc.Dropdown(
                                id="date-range-dropdown",
                                options=[
                                    {"label": "📅 Custom", "value": "custom"},
                                    {
                                        "label": "📆 Current Year",
                                        "value": "current_year",
                                    },
                                    {"label": "📊 Last 365 Days", "value": "last_365"},
                                    {
                                        "label": "📊 Last 6 Months",
                                        "value": "last_6_months",
                                    },
                                    {
                                        "label": "📊 Last 3 Months",
                                        "value": "last_3_months",
                                    },
                                    {"label": "♾️ All-time", "value": "all-time"},
                                ],
                                value="all-time",
                                clearable=False,
                            ),
                            html.Div(className="mb-3"),
                            html.Label(
                                "Custom Date Range", className="form-label mt-3"
                            ),
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
                                className="text-muted small mt-2",
                            ),
                        ],
                        title="📅 Time Period",
                        item_id="time",
                    ),
                    dbc.AccordionItem(
                        [
                            html.Label("Analysis Metric", className="form-label"),
                            dbc.RadioItems(
                                id="metric-selector",
                                options=[
                                    {"label": "💬 Message Count", "value": "messages"},
                                    {
                                        "label": "📝 Character Count",
                                        "value": "characters",
                                    },
                                ],
                                value="messages",
                                className="mb-3",
                            ),
                            html.Label("Role Filter", className="form-label mt-3"),
                            dbc.RadioItems(
                                id="virgule-filter",
                                options=[
                                    {"label": "👥 Everyone", "value": "everyone"},
                                    {
                                        "label": "⭐ Virgule Only",
                                        "value": "virgule_only",
                                    },
                                    {"label": "🚫 No Virgule", "value": "no_virgule"},
                                ],
                                value="everyone",
                                className="mb-3",
                            ),
                            html.Label("Channel Options", className="form-label mt-3"),
                            dbc.Switch(
                                id="mudae-filter-switch",
                                label="🎮 Include Mudae Channels",
                                value=False,
                            ),
                        ],
                        title="⚙️ Options & Filters",
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
                                dbc.Row([
                                    dbc.Col([
                                        dcc.Slider(
                                            id="evolution-graph-selector",
                                            min=0,
                                            max=1,
                                            step=None,
                                            marks={0: "Cumulative", 1: "Monthly"},
                                            value=0,
                                            className="mb-4",
                                        ),
                                    ], width=10),
                                    dbc.Col([
                                        dbc.RadioItems(
                                            id="evolution-view-toggle",
                                            options=[
                                                {"label": "📊 Graph", "value": "graph"},
                                                {"label": "📋 Table", "value": "table"},
                                            ],
                                            value="graph",
                                            inline=True,
                                            className="text-end",
                                        ),
                                    ], width=2),
                                ]),
                                dcc.Loading(
                                    html.Div(id="evolution-container")
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
                                dbc.Row([
                                    dbc.Col([
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
                                    ], width=10),
                                    dbc.Col([
                                        dbc.RadioItems(
                                            id="distribution-view-toggle",
                                            options=[
                                                {"label": "📊 Graph", "value": "graph"},
                                                {"label": "📋 Table", "value": "table"},
                                            ],
                                            value="graph",
                                            inline=True,
                                            className="text-end",
                                        ),
                                    ], width=2),
                                ]),
                                dcc.Loading(html.Div(id="distribution-container")),
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
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H5(
                                                        "Median Message Length (Characters)",
                                                        className="card-title",
                                                    ),
                                                ], width=8),
                                                dbc.Col([
                                                    dbc.RadioItems(
                                                        id="median-length-view-toggle",
                                                        options=[
                                                            {"label": "📊", "value": "graph"},
                                                            {"label": "📋", "value": "table"},
                                                        ],
                                                        value="graph",
                                                        inline=True,
                                                        className="text-end",
                                                    ),
                                                ], width=4),
                                            ]),
                                            dcc.Loading(
                                                html.Div(id="median-length-container")
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
                                            dbc.Row([
                                                dbc.Col([
                                                    html.H5(
                                                        "Most Mentioned Users (@)",
                                                        className="card-title",
                                                    ),
                                                ], width=8),
                                                dbc.Col([
                                                    dbc.RadioItems(
                                                        id="mentioned-users-view-toggle",
                                                        options=[
                                                            {"label": "📊", "value": "graph"},
                                                            {"label": "📋", "value": "table"},
                                                        ],
                                                        value="graph",
                                                        inline=True,
                                                        className="text-end",
                                                    ),
                                                ], width=4),
                                            ]),
                                            dcc.Loading(
                                                html.Div(id="mentioned-users-container")
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
