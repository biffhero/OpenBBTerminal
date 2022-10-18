""" Maps View """
import logging
import os
from turtle import fillcolor
import webbrowser
import pandas as pd
import folium
from typing import List, Tuple
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import export_data
from openbb_terminal.rich_config import console
from tqdm import tqdm
import investpy

from openbb_terminal.economy.econdb_model import (
    get_aggregated_macro_data,
    COUNTRY_CODES,
)

logger = logging.getLogger(__name__)

COUNTRY_SHAPES = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"

EUROZONE_COUNTRIES = [
    "Austria",
    "Belgium",
    "Cyprus",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Portugal",
    "Slovakia",
    "Slovenia",
    "Spain",
]


def get_folium_kwargs(
    legend: str = None,
    df: pd.DataFrame = None,
    country_shapes: str = COUNTRY_SHAPES,
    scale: list = None,
    fill_color: str = "RdYlGn",
) -> dict:

    kwargs = {
        "geo_data": country_shapes,
        "name": "choropleth",
        "columns": ["Country", "Value"],
        "key_on": "feature.properties.name",
        "line_weight": 2,
        "fill_color": fill_color,  # BuPu, RdYlGn_r TODO: passar isto para um arg no controller
        "fill_opacity": 0.5,
        "nan_fill_color": "white",
    }
    if not df.empty:
        kwargs["data"] = df
    if legend:
        kwargs["legend_name"] = legend
    if scale:
        kwargs["threshold_scale"] = scale

    return kwargs


def display_map(
    df: pd.DataFrame,
    legend: str,
    scale=None,
    fill_color: str = "RdYlGn_r",
) -> None:
    """Display map"""

    m = folium.Map(
        location=[20, 20],
        zoom_start=3,
        tiles="cartodbdark_matter",  # cartodbdark_matter, stamentoner this one is also cool
    )  # zoom_control=False, scrollWheelZoom=False, dragging=False

    kwargs = get_folium_kwargs(legend=legend, df=df, scale=scale, fill_color=fill_color)
    folium.Choropleth(**kwargs).add_to(m)

    # save folium to html
    m.save("maps.html")
    file_path = "maps.html"
    webbrowser.open("file://" + os.path.realpath(file_path))
    console.print("")


@log_start_end(log=logger)
def display_bitcoin_hash(export: str = ""):
    """Opens Finviz map website in a browser. [Source: Finviz]

    Parameters
    ----------
    period : str
        Performance period. Available periods are 1d, 1w, 1m, 3m, 6m, 1y.
    map_filter : str
        Map filter. Available map filters are sp500, world, full, etf.
    """
    df = pd.read_csv("https://ccaf.io/cbeci/api/v1.2.0/download/mining_countries")
    df = df[df["date"] == df["date"].max()]
    df = df[["country", "monthly_hashrate_%"]]
    df["country"] = df["country"].replace("United States", "United States of America")
    df["country"] = df["country"].replace("Iran, Islamic Rep.", "Iran")
    df["country"] = df["country"].replace("Germany *", "Germany")
    df["country"] = df["country"].replace("Ireland *", "Ireland")
    df["country"] = df["country"].replace("Mainland China", "China")
    df["monthly_hashrate_%"] = df["monthly_hashrate_%"].str.rstrip("%").astype("float")
    df.columns = ["Country", "Value"]
    display_map(df, "Bitcoin Hashing Rate % per country until 2022-01-01")
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "bh",
        df,
    )


@log_start_end(log=logger)
def display_interest_rates(export: str = ""):
    """Opens Finviz map website in a browser. [Source: Finviz]

    Parameters
    ----------
    period : str
        Performance period. Available periods are 1d, 1w, 1m, 3m, 6m, 1y.
    map_filter : str
        Map filter. Available map filters are sp500, world, full, etf.
    """
    ir_url = (
        "https://en.wikipedia.org/wiki/List_of_countries_by_central_bank_interest_rates"
    )
    df = pd.read_html(ir_url)
    df = df[0][["Country or currency union", "Central bank interest rate (%)"]]
    df.columns = ["Country", "Value"]
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "Country": country,
                        "Value": df[df["Country"] == "Eurozone"]["Value"].values[0],
                    }
                    for country in EUROZONE_COUNTRIES
                ]
            ),
        ],
    )
    df = df[df["Country"] != "Eurozone"]
    myscale = (df["Value"].quantile((0, 0.25, 0.5, 0.75, 1))).tolist()
    display_map(df, "Central Bank Interest Rates", myscale)
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "ir",
        df,
    )


@log_start_end(log=logger)
def get_macro_data(
    parameters: List[str],
    countries: List[str],
    change: bool = False,
    periods: int = 12,
) -> pd.DataFrame:

    df, _, _ = get_aggregated_macro_data(parameters, countries)
    if change:
        df = df.pct_change(periods=periods) * 100

    df = pd.DataFrame(df.iloc[-1])
    df = df.reset_index()
    df.drop(df.columns[[1]], axis=1, inplace=True)
    df.columns.values[0] = "Country"
    df.columns.values[1] = "Value"

    return df


@log_start_end(log=logger)
def display_macro(indicator: str = "RGDP", export: str = ""):
    """Opens macro data map website in a browser. [Source: EconDB]"""

    countries = list(COUNTRY_CODES.keys())
    df = get_macro_data([indicator], countries, change=True, periods=12)

    df["Country"] = df["Country"].replace("United_States", "United States of America")
    df["Country"] = df["Country"].replace("_", " ")
    myscale = (df["Value"].quantile((0, 0.25, 0.5, 0.75, 1))).tolist()
    display_map(df, f"{indicator}", myscale)
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        f"macro_{indicator}",
        df,
    )


@log_start_end(log=logger)
def display_openbb(export: str = ""):
    """Opens macro data map website in a browser. [Source: EconDB]"""

    d = {
        "United Kingdom": 3,
        "United States of America": 6,
        "Portugal": 5,
        "Vietnam": 1,
        "Canada": 2,
        "Montenegro": 1,
        "Russia": 1,
        "France": 1,
        "Sri Lanka": 1,
        "Netherlands": 1,
        "Romania": 1,
        "Sweden": 1,
    }
    df = pd.DataFrame(data=d.items(), columns=["Country", "Value"])
    myscale = (df["Value"].quantile((0, 0.25, 0.5, 0.75, 1))).tolist()
    display_map(df, "OpenBB", myscale, "BuPu")
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "openbb",
        df,
    )


@log_start_end(log=logger)
def display_stocks(export: str = ""):
    """Opens macro data map website in a browser. [Source: EconDB]"""

    # Using yfinance is better, we can pull all data at once. We just need this
    # dictionary populated.
    #
    # world_indices = {"United States of America": "^GSPC", "Portugal": "PSI20.LS"}

    # df = yfinance.download(
    #     list(world_indices.values()),
    #     start=datetime.today() - timedelta(days=1),
    #     threads=False,
    #     progress=False,
    # )["Adj Close"]

    # df.columns = list(world_indices.keys())
    # df = df.pct_change(1) * 100
    # df.dropna(inplace=True)
    # df = df.T

    countries = investpy.get_index_countries()
    d = {}
    no_data_countries = []
    for country in tqdm(countries, desc="Downloading"):
        try:
            performance = (
                investpy.indices.get_indices_overview(country)
                .iloc[0]["change_percentage"]
                .replace("%", "")
            )
            d[country] = float(performance)
        except Exception as _:
            no_data_countries.append(country.title())

    if no_data_countries:
        s = ", ".join(no_data_countries)
        console.print(f"[red]No data for {s}.[/red]")
    df = pd.DataFrame(data=d.values(), index=d.keys())

    df = df.reset_index()
    df.columns.values[0] = "Country"
    df.columns.values[1] = "Value"
    df["Country"] = df["Country"].str.title()
    df["Country"] = df["Country"].replace("United States", "United States of America")

    myscale = (df["Value"].quantile((0, 0.25, 0.5, 0.75, 1))).tolist()
    display_map(df, "OpenBB", myscale, "RdYlGn")
    export_data(
        export,
        os.path.dirname(os.path.abspath(__file__)),
        "openbb",
        df,
    )


@log_start_end(log=logger)
def display_map_explorer(coordinates: List[Tuple[float, float]]):
    """
    Display map explorer

    Parameters
    ----------
    coordinates : List[Tuple[float, float]]
        List of coordinates
    """
    m = folium.Map()
    for coordinate in coordinates:
        folium.Marker(location=[coordinate[0], coordinate[1]]).add_to(m)

    # save folium to html
    m.save("maps.html")
    file_path = "maps.html"
    webbrowser.open("file://" + os.path.realpath(file_path))
    console.print("")
