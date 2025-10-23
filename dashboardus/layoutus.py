# dashboardus/layoutus.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import pandas as pd


def create_layout(df):
    if df.empty:
        return html.Div("No data available to display.")
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    return html.Div(
        className="container-fluid bg-light",
        style={"fontFamily": "Inter, sans-serif"},
        children=[
            dcc.Markdown(id="dynamic-styles", style={"display": "none"}),
            # --- Header ---
            html.Header(
                className="bg-white shadow-sm mb-4",
                children=html.Div(
                    className="container-xxl d-flex align-items-center py-3",
                    children=[
                        html.I(
                            className="fab fa-discord me-3",
                            style={"fontSize": "2rem", "color": "#5865F2"},
                        ),
                        html.H1("Discord Activity Dashboard", className="h3 mb-0"),
                    ],
                ),
            ),
            # --- Filters Panel ---
            html.Div(
                id="filter-panel",
                className="card shadow-sm mb-4",
                children=html.Div(
                    className="card-body",
                    children=[
                        html.H5("Filters", className="card-title mb-4"),
                        html.Div(
                            className="row g-4",
                            children=[
                                # --- Column 1: Selection ---
                                html.Div(
                                    className="col-md-5",
                                    children=[
                                        html.H6("Selection", className="text-muted"),
                                        html.Label(
                                            "Top Users", className="form-label small"
                                        ),
                                        dcc.Dropdown(
                                            id="top-n-dropdown",
                                            options=[
                                                {"label": "Top 5", "value": 5},
                                                {"label": "Top 10", "value": 10},
                                                {"label": "Top 20", "value": 20},
                                                {"label": "Top 50", "value": 50},
                                                {"label": "Custom", "value": "custom"},
                                            ],
                                            value=10,
                                            clearable=False,
                                        ),
                                        html.Label(
                                            "Users", className="form-label small mt-3"
                                        ),
                                        dcc.Dropdown(id="user-dropdown", multi=True),
                                        html.Label(
                                            "Highlight User",
                                            className="form-label small mt-3",
                                        ),
                                        dcc.Dropdown(
                                            id="highlight-user-dropdown",
                                            clearable=True,
                                            placeholder="Select a user to highlight...",
                                        ),
                                    ],
                                ),
                                # --- Column 2: Time ---
                                html.Div(
                                    className="col-md-4",
                                    children=[
                                        html.H6("Time", className="text-muted"),
                                        html.Label(
                                            "Period", className="form-label small"
                                        ),
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
                                                    "label": "All-time",
                                                    "value": "all-time",
                                                },
                                            ],
                                            value="last_365",
                                            clearable=False,
                                        ),
                                        html.Label(
                                            "Date Range",
                                            className="form-label small mt-3",
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
                                            className="text-muted mt-2 small",
                                        ),
                                    ],
                                ),
                                # --- Column 3: Analysis ---
                                html.Div(
                                    className="col-md-3",
                                    children=[
                                        html.H6("Analysis", className="text-muted"),
                                        html.Label(
                                            "Analyze by:", className="form-label small"
                                        ),
                                        dbc.RadioItems(
                                            id="metric-selector",
                                            options=[
                                                {
                                                    "label": "Message Count",
                                                    "value": "messages",
                                                },
                                                {
                                                    "label": "Character Count",
                                                    "value": "characters",
                                                },
                                            ],
                                            value="messages",
                                            labelClassName="me-3",
                                            inputClassName="me-1",
                                        ),
                                        html.Label(
                                            "Special Filter",
                                            className="form-label small fw-bold mt-4",
                                        ),
                                        dbc.Checklist(
                                            options=[
                                                {
                                                    "label": "Show 'Virgule du 4' Only",
                                                    "value": 1,
                                                },
                                            ],
                                            value=[],
                                            id="virgule-filter",
                                            switch=True,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            html.Div(id="user-profile-card-container"),
            # --- Section 1: Temporal Analysis ---
            html.H2("Temporal Analysis", className="h4 mt-5 mb-3"),
            html.Div(
                className="card shadow-sm mb-4",
                children=[
                    html.Div(
                        className="card-header d-flex justify-content-between align-items-center",
                        children=[
                            html.H5("Activity Evolution", className="card-title mb-0"),
                            dcc.Slider(
                                id="evolution-graph-selector",
                                min=0,
                                max=1,
                                value=0,
                                marks={0: "Cumulative", 1: "Monthly"},
                                step=None,
                                className="w-25",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-body",
                        children=dcc.Loading(
                            dcc.Graph(id="evolution-graph", style={"height": "600px"}),
                            type="default",
                        ),
                    ),
                ],
            ),
            # --- Section 2: Message Analysis ---
            html.H2("Message Analysis", className="h4 mt-5 mb-3"),
            html.Div(
                className="row",
                children=[
                    html.Div(
                        className="col-lg-12 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header d-flex justify-content-between align-items-center",
                                        children=[
                                            html.H5(
                                                "Distribution (Top 3 vs Server)",
                                                className="card-title mb-0",
                                            ),
                                            dbc.RadioItems(
                                                id="distribution-time-unit",
                                                options=[
                                                    {"label": "Hour", "value": "hour"},
                                                    {
                                                        "label": "Day",
                                                        "value": "weekday",
                                                    },
                                                    {
                                                        "label": "Month",
                                                        "value": "month",
                                                    },
                                                    {"label": "Year", "value": "year"},
                                                ],
                                                value="hour",
                                                inline=True,
                                                labelClassName="me-2 small",
                                                inputClassName="me-1",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="card-body",
                                        children=dcc.Loading(
                                            dcc.Graph(
                                                id="distribution-graph",
                                                style={"height": "500px"},
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            html.Div(
                className="row",
                children=[
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header",
                                        children=html.H5(
                                            "Median Message Length",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body",
                                        children=dcc.Loading(
                                            dcc.Graph(
                                                id="median-length-graph",
                                                style={"height": "500px"},
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header",
                                        children=html.H5(
                                            "Activity Heatmap (Day/Hour)",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body",
                                        children=dcc.Loading(
                                            dcc.Graph(
                                                id="activity-heatmap",
                                                style={"height": "500px"},
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            # --- Section 3: Leaderboards ---
            html.H2("Leaderboards", className="h4 mt-5 mb-3"),
            html.Div(
                className="row",
                children=[
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header bg-primary text-white",
                                        children=html.H5(
                                            "Champions by Message Count",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body p-0",
                                        children=[
                                            html.H6(
                                                "🏆 Monthly Champions",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="monthly-leaderboard-msg")
                                            ),
                                            html.H6(
                                                "🥇 Daily Champions",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="daily-leaderboard-msg")
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=[
                            html.Div(
                                className="card shadow-sm h-100",
                                children=[
                                    html.Div(
                                        className="card-header bg-success text-white",
                                        children=html.H5(
                                            "Champions by Character Count",
                                            className="card-title mb-0",
                                        ),
                                    ),
                                    html.Div(
                                        className="card-body p-0",
                                        children=[
                                            html.H6(
                                                "🏆 Monthly Champions",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="monthly-leaderboard-char")
                                            ),
                                            html.H6(
                                                "🥇 Daily Champions",
                                                className="px-3 pt-3",
                                            ),
                                            dcc.Loading(
                                                html.Div(id="daily-leaderboard-char")
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
