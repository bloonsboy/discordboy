# dashboardus/layoutus.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime
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
            dcc.Markdown(id='dynamic-styles', style={'display': 'none'}),
            html.Header(
                className="bg-white shadow-sm mb-4",
                children=html.Div(
                    className="container d-flex align-items-center py-3",
                    children=[
                        html.I(className="fas fa-chart-bar me-3", style={"fontSize": "2rem", "color": "#4a90e2"}),
                        html.H1("Message Dashboard", className="h3 mb-0"),
                    ]
                )
            ),
            
            html.Div(
                id="filter-panel",
                className="card shadow-sm mb-4",
                children=html.Div(
                    className="card-body",
                    children=[
                        html.H5("Filters", className="card-title"),
                        html.Div(
                            className="row g-3",
                            children=[
                                # --- Colonne 1: Top & Analyse ---
                                html.Div(
                                    className="col-md-3",
                                    children=[
                                        html.Label("Top", className="form-label"),
                                        dcc.Dropdown(
                                            id="top-n-dropdown",
                                            options=[
                                                {"label": "Top 5", "value": 5}, {"label": "Top 10", "value": 10}, {"label": "Top 20", "value": 20}, 
                                                {"label": "Top 50", "value": 50}, {"label": "Custom", "value": "custom"},
                                            ],
                                            value=10, clearable=False,
                                        ),
                                        html.Label("Analyze by :", className="form-label fw-bold mt-3"),
                                        dbc.RadioItems(
                                            id='metric-selector',
                                            options=[
                                                {'label': 'Message Count', 'value': 'messages'},
                                                {'label': 'Character Count', 'value': 'characters'},
                                            ],
                                            value='messages',
                                            inline=True,
                                            labelClassName="me-3",
                                            inputClassName="me-1",
                                        ),
                                    ]
                                ),
                                # --- Colonne 2: Utilisateurs & Highlight ---
                                html.Div(
                                    className="col-md-5",
                                    children=[
                                        html.Label("Users", className="form-label"),
                                        dcc.Dropdown(id="user-dropdown", multi=True),
                                        
                                        html.Label("Highlight User", className="form-label mt-3"),
                                        dcc.Dropdown(id="highlight-user-dropdown", clearable=True, placeholder="Select a user to highlight..."),
                                    ]
                                ),
                                # --- Colonne 3: Période & Plage de dates ---
                                html.Div(
                                    className="col-md-4",
                                    children=[
                                        html.Label("Time", className="form-label"),
                                        dcc.Dropdown(
                                            id="date-range-dropdown",
                                            options=[
                                                {"label": "Custom", "value": "custom"}, {"label": "Current Year", "value": "current_year"},
                                                {"label": "Last 365 Days", "value": "last_365"}, {"label": "Last 6 Months", "value": "last_6_months"},
                                                {"label": "All-time", "value": "all-time"},
                                            ],
                                            value="last_365", clearable=False,
                                        ),
                                        html.Label("Date Range", className="form-label mt-3"),
                                        dcc.DatePickerRange(
                                            id="date-picker-range",
                                            min_date_allowed=min_date, max_date_allowed=max_date,
                                            start_date=min_date, end_date=max_date, display_format="DD/MM/YYYY",
                                            className="w-100"
                                        ),
                                        html.Div(id="date-range-display", className="text-muted mt-2 small"),
                                    ]
                                ),
                            ]
                        )
                    ]
                )
            ),

            html.Div(id="user-profile-card-container"),

            html.Div(
                className="row",
                children=[
                    html.Div(
                        className="col-lg-12 mb-4",
                        children=html.Div(
                            className="card shadow-sm",
                            children=[
                                html.Div(
                                    className="card-header d-flex justify-content-between align-items-center",
                                    children=[
                                        html.H5("📈 Temporal Evolution", className="card-title mb-0"),
                                        dbc.RadioItems(
                                            id='evolution-graph-selector',
                                            options=[
                                                {'label': 'Cumulative', 'value': 'cumulative'},
                                                {'label': 'Monthly', 'value': 'monthly'},
                                            ],
                                            value='cumulative',
                                            inline=True,
                                            labelClassName="me-3",
                                            inputClassName="me-1",
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="card-body",
                                    children=dcc.Loading(
                                        dcc.Graph(id='evolution-graph'),
                                        type="default"
                                    )
                                ),
                            ]
                        )
                    ),
                    html.Div(className="col-lg-6 mb-4", children=create_graph_card("⏰ Hourly Distribution (%)", "hourly-graph")),
                    html.Div(className="col-lg-6 mb-4", children=create_graph_card("🗓️ Weekly Activity", "weekday-graph")),
                    
                    # Monthly Champions Card (inlined)
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=html.Div(
                            className="card shadow-sm h-100",
                            children=[
                                html.Div(className="card-header", children=html.H5("🏆 Monthly Champions", className="card-title mb-0")),
                                html.Div(className="card-body", children=dcc.Loading(html.Div(id="monthly-leaderboard-container"), type="default")),
                            ]
                        )
                    ),
                    # Daily Champions Card (inlined)
                    html.Div(
                        className="col-lg-6 mb-4",
                        children=html.Div(
                            className="card shadow-sm h-100",
                            children=[
                                html.Div(className="card-header", children=html.H5("🥇 Daily Champions", className="card-title mb-0")),
                                html.Div(className="card-body", children=dcc.Loading(html.Div(id="daily-leaderboard-container"), type="default")),
                            ]
                        )
                    ),
                ],
            ),
        ],
    )

def create_graph_card(title, graph_id):
    return html.Div(
        className="card shadow-sm h-100",
        children=[
            html.Div(className="card-header", children=html.H5(title, className="card-title mb-0")),
            html.Div(className="card-body", children=dcc.Loading(dcc.Graph(id=graph_id, className="h-100"), type="default")),
        ]
    )
