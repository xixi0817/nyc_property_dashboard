# ============================================================
# app.py - NYC Property Market Dashboard
# Group 19: Xixi Lin, Jiahuan Wu, Victor Louie, Chhin Lama
# Baruch College CIS 9655 Data Visualization Spring 2026
# ============================================================

import pandas as pd
import numpy as np
import requests
from dash import Dash, dcc, html, Input, Output, State, ctx, no_update
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# LOAD DATA (from saved CSVs)
# ============================================================

df_master                 = pd.read_csv("Datasets/df_master.csv.gz")
df_schools_all            = pd.read_csv("Datasets/df_schools_all.csv")
df_income                 = pd.read_csv("Datasets/df_income.csv")
df_subway                 = pd.read_csv("Datasets/df_subway.csv")
arrest_per_zip            = pd.read_csv("Datasets/arrest_per_zip.csv")
df_zip_centroids          = pd.read_csv("Datasets/df_zip_centroids.csv")
arrest_zip_enhanced_clean = pd.read_csv("Datasets/arrest_zip_enhanced.csv")

# Fix zip_code format
for df in [df_master, df_schools_all, df_income,
           arrest_per_zip, df_zip_centroids, arrest_zip_enhanced_clean]:
    if "zip_code" in df.columns:
        df["zip_code"] = (df["zip_code"].astype(str)
                          .str.replace(".0", "", regex=False)
                          .str.strip().str.zfill(5))

# Fix dtypes
df_master["year"]       = pd.to_numeric(df_master["year"], errors="coerce")
df_master["sale_price"] = pd.to_numeric(df_master["sale_price"], errors="coerce")

# Load GeoJSON
zip_geojson_url = "https://raw.githubusercontent.com/fedhere/PUI2015_EC/master/mam1612_EC/nyc-zip-code-tabulation-areas-polygons.geojson"
nyc_zip_geojson = requests.get(zip_geojson_url).json()

# ============================================================
# THEME (same as your notebook)
# ============================================================

BOROUGH_NAME_MAP = {
    "bronx"       : "Bronx",
    "brooklyn"    : "Brooklyn",
    "manhattan"   : "Manhattan",
    "queens"      : "Queens",
    "statenisland": "Staten Island"
}

THEME = {
    "font_family"    : "Arial",
    "font_color"     : "#2c2c2c",
    "font_size"      : 12,
    "title_size"     : 20,
    "axis_title_size": 13,
    "tick_size"      : 11,
    "paper_bgcolor"  : "#ffffff",
    "plot_bgcolor"   : "#f8f9fa",
    "gridcolor"      : "rgba(0,0,0,0.06)",
    "linecolor"      : "rgba(0,0,0,0.15)",
    "borough_colors" : {
        "Bronx"        : "#636EFA",
        "Brooklyn"     : "#EF553B",
        "Manhattan"    : "#00CC96",
        "Queens"       : "#FFA15A",
        "Staten Island": "#AB63FA"
    },
    "map_style"      : "carto-positron",
    "height_medium"  : 500,
    "margin_chart"   : dict(t=80, b=60, l=80, r=120),
}

# ============================================================
# PRE-COMPUTE SCHOOL SCORE & BEST SCHOOL
# ============================================================

df_sch_score = (df_schools_all.groupby("zip_code")["rank"].mean()
                .reset_index().rename(columns={"rank": "avg_rank"}))
df_sch_score["school_score"] = 101 - df_sch_score["avg_rank"]

df_best_school = (
    df_schools_all.sort_values("rank")
    .groupby("zip_code").first().reset_index()
    [["zip_code", "school_name", "type", "school_level"]]
    .rename(columns={"school_name" : "best_school_name",
                     "type"        : "best_school_type",
                     "school_level": "best_school_level"})
)
df_sch_score = df_sch_score.merge(df_best_school, on="zip_code", how="left")

# ============================================================
# APP
# ============================================================

app = Dash(__name__)
server = app.server  # ← needed for Render

# ============================================================
# LAYOUT — Cell 77 design preserved, only scatter section updated
# ============================================================

app.layout = html.Div([

    # Hidden store: central borough state (syncs top dropdown <-> bottom radio)
    dcc.Store(id="borough-state", data="all"),

    # ── Header ──────────────────────────────────────────
    html.Div([
        html.H1("NYC Property Market Dashboard",
            style={"fontFamily": "Arial", "fontSize": "26px",
                   "color": "#2c2c2c", "margin": "0"}),
        html.P("How do neighborhood factors influence residential property prices across NYC (2013–2025)?",
            style={"fontFamily": "Arial", "fontSize": "13px",
                   "color": "#666", "margin": "4px 0 0 0"})
    ], style={"padding": "20px 30px 15px 30px",
              "borderBottom": "1px solid #e8e8e8"}),

    # ── KPI Cards ───────────────────────────────────────
    html.Div(id="kpi-cards", style={
        "display": "flex",
        "padding": "15px 30px",
        "gap"    : "12px",
        "borderBottom": "1px solid #e8e8e8"
    }),

    # ── Top Controls (Year + Borough Dropdown) ───────────
    html.Div([
        html.Div([
            html.Label("Year Range",
                style={"fontFamily": "Arial", "fontSize": "12px",
                       "color": "#666", "marginBottom": "8px", "display": "block"}),
            dcc.RangeSlider(
                id="year-slider",
                min=2013, max=2025, step=1,
                value=[2013, 2025],
                marks={y: {"label": str(y),
                           "style": {"fontFamily": "Arial", "fontSize": "10px"}}
                       for y in range(2013, 2026)},
                tooltip={"placement": "bottom", "always_visible": False}
            )
        ], style={"flex": "3"}),

        html.Div([
            html.Label("Borough",
                style={"fontFamily": "Arial", "fontSize": "12px",
                       "color": "#666", "marginBottom": "8px", "display": "block"}),
            dcc.Dropdown(
                id="borough-dropdown",
                options=[{"label": v, "value": k} for k, v in BOROUGH_NAME_MAP.items()],
                value=None,
                placeholder="All Boroughs",
                style={"fontFamily": "Arial", "fontSize": "12px"}
            )
        ], style={"flex": "1", "marginLeft": "20px"}),

    ], style={"display": "flex", "alignItems": "flex-end",
              "padding": "15px 30px",
              "borderBottom": "1px solid #e8e8e8",
              "background": "#fafafa"}),

    # ── Row 1: Map (full width) ──────────────────────────
    html.Div([
        dcc.Graph(id="fig-map", style={"height": "550px"})
    ], style={"padding": "20px 30px 10px 30px",
              "borderBottom": "1px solid #e8e8e8"}),

    # ── Row 2: Line Chart (full width) ──────────────────
    html.Div([
        dcc.Graph(id="fig-line", style={"height": "420px"})
    ], style={"padding": "10px 30px",
              "borderBottom": "1px solid #e8e8e8"}),

    # ── Row 3: Explore by Borough (replaces "Explore by Factor") ──
    html.Div([
        html.Div([
            html.Span("Explore by Factor: by Borough  ",
                style={"fontFamily": "Arial", "fontSize": "13px",
                       "color": "#2c2c2c", "fontWeight": "bold"}),
            dcc.RadioItems(
                id="borough-radio",
                options=[
                    {"label": " All",            "value": "all"},
                    {"label": " Bronx",          "value": "bronx"},
                    {"label": " Brooklyn",       "value": "brooklyn"},
                    {"label": " Manhattan",      "value": "manhattan"},
                    {"label": " Queens",         "value": "queens"},
                    {"label": " Staten Island",  "value": "statenisland"},
                ],
                value="all",
                inline=True,
                style={"fontFamily": "Arial", "fontSize": "13px",
                       "color": "#2c2c2c", "display": "inline"},
                labelStyle={"marginLeft": "20px", "cursor": "pointer"}
            )
        ], style={"display": "flex", "alignItems": "center"})
    ], style={"padding": "15px 30px",
              "background": "#fafafa",
              "borderBottom": "1px solid #e8e8e8"}),

    # ── Row 4: 4 scatter plots in 2x2 grid ──────────────
    # First row: Income | School
    html.Div([
        html.Div([dcc.Graph(id="fig-income", style={"height": "440px"})],
                 style={"flex": "1", "minWidth": "0"}),
        html.Div([dcc.Graph(id="fig-school", style={"height": "440px"})],
                 style={"flex": "1", "minWidth": "0",
                        "borderLeft": "1px solid #e8e8e8"}),
    ], style={"display": "flex",
              "padding": "10px 30px",
              "borderBottom": "1px solid #e8e8e8"}),

    # Second row: Crime | Subway
    html.Div([
        html.Div([dcc.Graph(id="fig-crime", style={"height": "440px"})],
                 style={"flex": "1", "minWidth": "0"}),
        html.Div([dcc.Graph(id="fig-subway", style={"height": "440px"})],
                 style={"flex": "1", "minWidth": "0",
                        "borderLeft": "1px solid #e8e8e8"}),
    ], style={"display": "flex",
              "padding": "10px 30px",
              "borderBottom": "1px solid #e8e8e8"}),

    # ── Footer ──────────────────────────────────────────
    html.Div([
        html.Span("Xixi Lin · Jiahuan Wu · Victor Louie · Chhin Lama",
            style={"fontFamily": "Arial", "fontSize": "12px", "color": "#999"}),
        html.Span("Baruch College · CIS 9655 · Spring 2026",
            style={"fontFamily": "Arial", "fontSize": "12px", "color": "#999"})
    ], style={"display": "flex", "justifyContent": "space-between",
              "padding": "15px 30px",
              "borderTop": "1px solid #e8e8e8",
              "background": "#fafafa"})

], style={"background": "white", "minHeight": "100vh"})


# ============================================================
# HELPERS
# ============================================================

def kpi_card(label, value, color):
    return html.Div([
        html.P(label, style={"fontFamily": "Arial", "fontSize": "12px",
                              "color": "#999", "margin": "0"}),
        html.H2(value, style={"fontFamily": "Arial", "fontSize": "22px",
                               "color": color, "margin": "4px 0 0 0",
                               "fontWeight": "700"})
    ], style={"background": "white", "borderRadius": "8px",
              "padding": "12px 18px", "flex": "1",
              "border": "1px solid #e8e8e8",
              "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"})


def apply_scatter_theme(fig, x_label, y_label="Median Property Sale Price"):
    """Apply your unified theme to a scatter plot (matches your notebook)."""
    fig.update_layout(
        title=dict(
            x=0.5,
            font=dict(family=THEME["font_family"], size=THEME["title_size"],
                      color=THEME["font_color"])
        ),
        paper_bgcolor=THEME["paper_bgcolor"],
        plot_bgcolor =THEME["plot_bgcolor"],
        font=dict(family=THEME["font_family"], size=THEME["font_size"],
                  color=THEME["font_color"]),
        margin=THEME["margin_chart"],
        legend=dict(
            title=dict(text="Borough",
                       font=dict(family=THEME["font_family"], size=13,
                                 color=THEME["font_color"])),
            font=dict(family=THEME["font_family"], size=13,
                      color=THEME["font_color"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(
            title=dict(text=x_label,
                       font=dict(family=THEME["font_family"],
                                 size=THEME["axis_title_size"],
                                 color=THEME["font_color"])),
            tickfont=dict(family=THEME["font_family"], size=13,
                          color=THEME["font_color"]),
            gridcolor=THEME["gridcolor"], linecolor=THEME["linecolor"],
            showline=True
        ),
        yaxis=dict(
            title=dict(text=y_label,
                       font=dict(family=THEME["font_family"],
                                 size=THEME["axis_title_size"],
                                 color=THEME["font_color"])),
            tickprefix="$", tickformat=",.0f",
            tickfont=dict(family=THEME["font_family"], size=13,
                          color=THEME["font_color"]),
            gridcolor=THEME["gridcolor"], linecolor=THEME["linecolor"],
            showline=True
        ),
        hoverlabel=dict(
            bgcolor="white", bordercolor="rgba(0,0,0,0.15)",
            font=dict(family=THEME["font_family"], size=13,
                      color=THEME["font_color"])
        )
    )
    return fig


def grey_out_other_boroughs(fig, selected_borough_label):
    """When a specific borough is selected, dim all other borough markers
    (but keep them visible). Trendline stays as-is."""
    if selected_borough_label is None:
        return fig
    for trace in fig.data:
        if trace.name in THEME["borough_colors"]:
            trace.opacity = 1.0 if trace.name == selected_borough_label else 0.15
    return fig


# ============================================================
# CALLBACK 1: Sync top dropdown <-> bottom radio
# ============================================================

@app.callback(
    Output("borough-state",     "data"),
    Output("borough-dropdown",  "value"),
    Output("borough-radio",     "value"),
    Input("borough-dropdown",   "value"),
    Input("borough-radio",      "value"),
    prevent_initial_call=True
)
def sync_borough_controls(dropdown_val, radio_val):
    """Whichever the user just changed becomes the source of truth.
    The other UI control updates to match."""
    trigger = ctx.triggered_id

    if trigger == "borough-dropdown":
        new_state = dropdown_val if dropdown_val else "all"
        return new_state, dropdown_val, new_state

    elif trigger == "borough-radio":
        new_state    = radio_val
        new_dropdown = None if radio_val == "all" else radio_val
        return new_state, new_dropdown, radio_val

    return no_update, no_update, no_update


# ============================================================
# CALLBACK 2: Update all charts based on year + borough state
# ============================================================

@app.callback(
    Output("kpi-cards",  "children"),
    Output("fig-map",    "figure"),
    Output("fig-line",   "figure"),
    Output("fig-income", "figure"),
    Output("fig-school", "figure"),
    Output("fig-crime",  "figure"),
    Output("fig-subway", "figure"),
    Input("year-slider",    "value"),
    Input("borough-state",  "data"),
)
def update_charts(year_range, borough_state):

    year_min, year_max = year_range

    # selected_borough = None  → all boroughs (Map/Line show full NYC)
    # selected_borough = "manhattan" → filter to that borough
    selected_borough = (None if (borough_state is None or borough_state == "all")
                        else borough_state)
    selected_borough_label = (BOROUGH_NAME_MAP.get(selected_borough)
                              if selected_borough else None)

    # Filter df_master by year + borough (used for KPI/Map/Line)
    dff = df_master[
        (df_master["year"] >= year_min) &
        (df_master["year"] <= year_max)
    ].copy()
    if selected_borough:
        dff = dff[dff["borough"] == selected_borough]

    # ── KPI ──
    total_sales  = len(dff)
    median_price = dff["sale_price"].median()
    p_first      = dff[dff["year"] == year_min]["sale_price"].median()
    p_last       = dff[dff["year"] == year_max]["sale_price"].median()
    pct          = ((p_last - p_first) / p_first * 100) if p_first and p_first > 0 else 0
    sign         = "+" if pct >= 0 else ""

    if len(dff) > 0:
        top_boro      = dff.groupby("borough")["sale_price"].median().idxmax()
        top_boro_name = BOROUGH_NAME_MAP.get(top_boro, top_boro)
    else:
        top_boro_name = "N/A"

    kpi_cards = [
        kpi_card("Total Transactions",
                 f"{total_sales:,}", "#2c2c2c"),
        kpi_card("NYC Median Sale Price",
                 f"${median_price:,.0f}" if pd.notna(median_price) else "N/A",
                 "#636EFA"),
        kpi_card(f"Price Change {year_min}→{year_max}",
                 f"{sign}{pct:.1f}%",
                 "#00CC96" if pct >= 0 else "#EF553B"),
        kpi_card("Most Expensive Borough", top_boro_name, "#EF553B"),
    ]

    # ── Viz 1: Map ──
    zip_col  = "zip_code"
    zip_data = (
        dff.dropna(subset=[zip_col, "sale_price"])
        .groupby([zip_col, "borough"], as_index=False)
        .agg(median_sale_price=("sale_price", "median"),
             avg_sale_price   =("sale_price", "mean"),
             total_sales      =("sale_price", "count"))
    )
    zip_data = zip_data[zip_data["total_sales"] >= 10].copy()
    zip_data["borough_display"] = zip_data["borough"].map(BOROUGH_NAME_MAP)

    df_sub_dist = df_zip_centroids[["zip_code", "nearest_subway_dist_miles", "nearest_subway"]]
    arr_zip     = arrest_per_zip.rename(columns={"arrest_count": "crime_count_2025"})

    zip_data = (zip_data
                .merge(df_sch_score[["zip_code", "school_score"]],
                       on="zip_code", how="left")
                .merge(df_sub_dist, on="zip_code", how="left")
                .merge(arr_zip,     on="zip_code", how="left"))
    zip_data["school_score"]              = zip_data["school_score"].round(1)
    zip_data["nearest_subway_dist_miles"] = zip_data["nearest_subway_dist_miles"].round(2)

    if len(zip_data) > 0:
        p_min = zip_data["median_sale_price"].quantile(0.10)
        p_max = zip_data["median_sale_price"].quantile(0.85)
    else:
        p_min, p_max = 0, 1

    fig_map = px.choropleth_map(
        zip_data, geojson=nyc_zip_geojson,
        locations=zip_col, featureidkey="properties.postalCode",
        color="median_sale_price",
        color_continuous_scale="Blues", range_color=(p_min, p_max),
        map_style=THEME["map_style"], zoom=9.2,
        center={"lat": 40.7128, "lon": -74.0060}, opacity=0.78,
        hover_name="borough_display",
        hover_data={
            "median_sale_price"        : ":$,.0f",
            "avg_sale_price"           : ":$,.0f",
            "total_sales"              : ":,",
            zip_col                    : True,
            "school_score"             : ":.1f",
            "nearest_subway_dist_miles": ":.2f",
            "nearest_subway"           : True,
            "crime_count_2025"         : ":,",
            "borough_display"          : False,
            "borough"                  : False
        },
        labels={
            "median_sale_price"        : "Median Sale Price",
            "avg_sale_price"           : "Avg Sale Price",
            "total_sales"              : "Total Sales",
            zip_col                    : "ZIP Code",
            "school_score"             : "School Quality Score",
            "nearest_subway_dist_miles": "Nearest Subway (miles)",
            "nearest_subway"           : "Nearest Station",
            "crime_count_2025"         : "Arrests (2025)"
        },
        title=f"NYC Median Property Sale Price by ZIP Code ({year_min}–{year_max})"
    )
    fig_map.update_traces(marker_line_width=0.3, marker_line_color="white")
    fig_map.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        title=dict(x=0.5, font=dict(family="Arial", size=16, color="#2c2c2c")),
        font=dict(family="Arial", size=12),
        coloraxis_colorbar=dict(
            title=dict(text="Median Sale Price",
                       font=dict(family="Arial", size=13)),
            tickprefix="$", tickformat=",.0f",
            tickfont=dict(family="Arial", size=11),
            thickness=18, len=0.6
        )
    )

    # ── Viz 2: Line Chart ──
    line_data = (dff[dff["sale_price"] >= 10_000]
                 .groupby(["year", "borough"], as_index=False)
                 .agg(median_sale_price=("sale_price", "median")))
    line_data["borough_display"] = line_data["borough"].map(BOROUGH_NAME_MAP)

    annotation_offset = {
        "Manhattan": 80000, "Brooklyn": 50000, "Queens": 0,
        "Staten Island": -50000, "Bronx": -80000
    }
    boroughs_to_show = (
        [BOROUGH_NAME_MAP[selected_borough]] if selected_borough
        else ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]
    )

    fig_line = go.Figure()
    for borough in boroughs_to_show:
        df_b = line_data[line_data["borough_display"] == borough].sort_values("year")
        if len(df_b) < 2:
            continue
        p1 = df_b["median_sale_price"].iloc[0]
        pl = df_b["median_sale_price"].iloc[-1]
        pc = ((pl - p1) / p1 * 100)
        sg = "+" if pc >= 0 else ""

        fig_line.add_trace(go.Scatter(
            x=df_b["year"], y=df_b["median_sale_price"].tolist(),
            mode="lines+markers", name=borough, legendgroup=borough,
            line=dict(color=THEME["borough_colors"][borough], width=2.5),
            marker=dict(size=6, color=THEME["borough_colors"][borough]),
            hovertemplate=(f"<b>{borough}</b><br>Year: %{{x}}<br>"
                           f"Median Price: $%{{y:,.0f}}<extra></extra>")
        ))
        fig_line.add_trace(go.Scatter(
            x=[df_b["year"].max()],
            y=[pl + annotation_offset.get(borough, 0)],
            mode="text", name=borough, legendgroup=borough,
            showlegend=False,
            text=[f"  {borough} {sg}{pc:.0f}%"],
            textposition="middle right", cliponaxis=False,
            textfont=dict(family="Arial", size=11,
                          color=THEME["borough_colors"][borough]),
            hoverinfo="skip"
        ))

    fig_line.add_vrect(x0=2019.5, x1=2021.5,
                       fillcolor="rgba(255,200,0,0.08)",
                       layer="below", line_width=0)
    fig_line.add_annotation(x=2020.5, y=1, xref="x", yref="paper",
                             text="COVID-19", showarrow=False,
                             font=dict(family="Arial",
                                       color="rgba(180,140,0,0.7)", size=11))
    fig_line.update_layout(
        title=dict(text=f"Property Sale Price Trends by Borough ({year_min}–{year_max})",
                   x=0.5, font=dict(family="Arial", size=16, color="#2c2c2c")),
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        font=dict(family="Arial", size=12, color="#2c2c2c"),
        height=400,
        margin=dict(t=60, b=50, l=80, r=180),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0,
                    font=dict(family="Arial", size=11), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(title="Year", tickmode="linear", dtick=1,
                   range=[year_min - 0.5, year_max + 1.5],
                   tickfont=dict(family="Arial", size=11),
                   gridcolor="rgba(0,0,0,0.06)", showline=True),
        yaxis=dict(title="Median Sale Price", tickprefix="$",
                   tickformat=",.0f",
                   tickfont=dict(family="Arial", size=11),
                   gridcolor="rgba(0,0,0,0.06)", showline=True),
        hovermode="x unified"
    )

    # ════════════════════════════════════════════════════
    # SCATTER PLOTS — use FULL year-filtered data (all boroughs visible).
    # When a borough is selected, others are dimmed via grey_out_other_boroughs.
    # ════════════════════════════════════════════════════

    dff_all = df_master[
        (df_master["year"] >= year_min) &
        (df_master["year"] <= year_max)
    ].copy()

    base_data = (
        dff_all[dff_all["sale_price"] >= 10_000]
        .dropna(subset=["sale_price", "zip_code", "borough"])
        .groupby(["zip_code", "borough"], as_index=False)
        .agg(median_sale_price=("sale_price", "median"),
             total_sales      =("sale_price", "count"))
    )
    base_data = base_data[base_data["total_sales"] >= 10].copy()
    base_data["borough_display"] = base_data["borough"].map(BOROUGH_NAME_MAP)

    # ── Scatter 1: INCOME (your Cell 58) ──
    inc_data = base_data.merge(
        df_income[["zip_code", "median_income_usd"]],
        on="zip_code", how="inner"
    )

    fig_income = px.scatter(
        inc_data,
        x="median_income_usd", y="median_sale_price",
        color="borough_display", size="total_sales", size_max=40,
        trendline="ols", trendline_scope="overall",
        trendline_color_override="gray",
        color_discrete_map=THEME["borough_colors"],
        hover_name="borough_display",
        hover_data={
            "zip_code"         : True,
            "median_income_usd": ":$,.0f",
            "median_sale_price": ":$,.0f",
            "total_sales"      : ":,",
            "borough_display"  : False,
            "borough"          : False
        },
        labels={
            "median_income_usd" : "Median Household Income",
            "median_sale_price" : "Median Property Sale Price",
            "total_sales"       : "Total Sales",
            "borough_display"   : "Borough",
            "zip_code"          : "ZIP Code"
        },
        title="Median Household Income vs Property Sale Price by ZIP Code"
    )
    fig_income = apply_scatter_theme(fig_income, "Median Household Income")
    fig_income = grey_out_other_boroughs(fig_income, selected_borough_label)

    # ── Scatter 2: SCHOOL (your Cell 61) ──
    sch_data = base_data.merge(
        df_sch_score[["zip_code", "school_score", "best_school_name",
                      "best_school_type", "best_school_level"]],
        on="zip_code", how="inner"
    )
    sch_data = sch_data[sch_data["school_score"] > 0].copy()

    fig_school = px.scatter(
        sch_data,
        x="school_score", y="median_sale_price",
        color="borough_display", size="total_sales", size_max=40,
        trendline="ols", trendline_scope="overall",
        trendline_color_override="gray",
        color_discrete_map=THEME["borough_colors"],
        hover_name="borough_display",
        hover_data={
            "zip_code"         : True,
            "school_score"     : ":.1f",
            "best_school_name" : True,
            "best_school_type" : True,
            "best_school_level": True,
            "median_sale_price": ":$,.0f",
            "total_sales"      : ":,",
            "borough_display"  : False,
            "borough"          : False
        },
        labels={
            "school_score"     : "School Quality Score (higher = better)",
            "best_school_name" : "Top School",
            "best_school_type" : "School Type",
            "best_school_level": "School Level",
            "median_sale_price": "Median Property Sale Price",
            "total_sales"      : "Total Sales",
            "borough_display"  : "Borough",
            "zip_code"         : "ZIP Code"
        },
        title="School Quality vs Property Sale Price by ZIP Code"
    )
    fig_school = apply_scatter_theme(fig_school, "School Quality Score (higher = better)")
    fig_school = grey_out_other_boroughs(fig_school, selected_borough_label)

    # ── Scatter 3: CRIME (your Cell 63 — enhanced with crime details) ──
    crim_data = base_data.merge(
        arrest_zip_enhanced_clean[[
            "zip_code", "arrest_count", "crime_per_10k",
            "murder", "rape", "robbery", "fel_assault",
            "burglary", "gr_larceny", "gla"
        ]],
        on="zip_code", how="inner"
    )

    fig_crime = px.scatter(
        crim_data,
        x="arrest_count", y="median_sale_price",
        color="borough_display", size="total_sales", size_max=40,
        trendline="ols", trendline_scope="overall",
        trendline_color_override="gray",
        color_discrete_map=THEME["borough_colors"],
        hover_name="borough_display",
        hover_data={
            "zip_code"        : True,
            "median_sale_price": ":$,.0f",
            "total_sales"     : ":,",
            "arrest_count"    : ":,",
            "crime_per_10k"   : ":.1f",
            "murder"          : ":.0f",
            "rape"            : ":.0f",
            "robbery"         : ":.0f",
            "fel_assault"     : ":.0f",
            "burglary"        : ":.0f",
            "gr_larceny"      : ":.0f",
            "gla"             : ":.0f",
            "borough_display" : False,
            "borough"         : False
        },
        labels={
            "zip_code"        : "ZIP Code",
            "median_sale_price": "Median Property Sale Price",
            "total_sales"     : "Total Sales",
            "arrest_count"    : "Arrests per ZIP (2025)",
            "crime_per_10k"   : "Serious Crimes per 10,000 People",
            "murder"          : "Murder (Homicide)",
            "rape"            : "Rape (Sexual Assault)",
            "robbery"         : "Robbery (Armed/Force)",
            "fel_assault"     : "Felony Assault (Violence)",
            "burglary"        : "Burglary (Break-in)",
            "gr_larceny"      : "Grand Larceny (Theft >$1,000)",
            "gla"             : "Grand Larceny Auto (Car Theft)",
            "borough_display" : "Borough"
        },
        title="Crime Rate vs Property Sale Price by ZIP Code (2025)"
    )
    fig_crime = apply_scatter_theme(fig_crime, "Total Arrests per ZIP Code (2025)")
    fig_crime = grey_out_other_boroughs(fig_crime, selected_borough_label)

    # ── Scatter 4: SUBWAY (your Cell 69) ──
    sub_data = base_data.merge(
        df_zip_centroids[["zip_code", "nearest_subway_dist_miles", "nearest_subway"]],
        on="zip_code", how="inner"
    )

    fig_subway = px.scatter(
        sub_data,
        x="nearest_subway_dist_miles", y="median_sale_price",
        color="borough_display", size="total_sales", size_max=40,
        trendline="ols", trendline_scope="overall",
        trendline_color_override="gray",
        color_discrete_map=THEME["borough_colors"],
        hover_name="borough_display",
        hover_data={
            "zip_code"                 : True,
            "nearest_subway_dist_miles": ":.2f",
            "nearest_subway"           : True,
            "median_sale_price"        : ":$,.0f",
            "total_sales"              : ":,",
            "borough_display"          : False,
            "borough"                  : False
        },
        labels={
            "nearest_subway_dist_miles": "Distance to Nearest Subway (miles)",
            "median_sale_price"        : "Median Property Sale Price",
            "total_sales"              : "Total Sales",
            "borough_display"          : "Borough",
            "zip_code"                 : "ZIP Code",
            "nearest_subway"           : "Nearest Station"
        },
        title="Subway Accessibility vs Property Sale Price by ZIP Code"
    )
    fig_subway = apply_scatter_theme(fig_subway, "Distance to Nearest Subway (miles)")
    fig_subway = grey_out_other_boroughs(fig_subway, selected_borough_label)

    return (kpi_cards, fig_map, fig_line,
            fig_income, fig_school, fig_crime, fig_subway)


# ============================================================
# RUN
# ============================================================

#if __name__ == "__main__":
 #   app.run(debug=False, port=8051)

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8051))
    app.run(debug=False, host="0.0.0.0", port=port)
