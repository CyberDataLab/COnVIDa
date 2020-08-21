# Import required libraries
from threading import Thread

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from functools import partial

import pandas as pd
import flask
from flask import render_template, redirect, send_from_directory, request
import copy
import json
from datetime import datetime as dt
import datetime
import os
import uuid
import sys
import uwsgidecorators
import time

PORT = 8899
# Developing: DEBUG = True
# Production: DEBUG = False
DEBUG = True


## Add convida lib and convida server lib to path

convida_lib_path = os.getcwd()
lib = os.path.join(convida_lib_path, 'COnVIDa-lib')
lib_aux = os.path.join(lib, 'lib')
sys.path.append(lib_aux)

convida_server_path = os.getcwd()
server_path = os.path.join(convida_server_path, 'COnVIDa-lib')
server_aux = os.path.join(server_path, 'server')
sys.path.append(server_aux)

from convida import COnVIDa
from regions import Regions
from datatype import DataType
from convida_server import convida_server

convida_server.init_log()
convida_server.load_data()

FOLDER_LOGS = os.path.join(os.getcwd(), 'log')
try:
    LAST_UPDATE = open(os.path.join(FOLDER_LOGS, 'update.txt'), "r").readline()
except:
    LAST_UPDATE = 'undefinied'

TIME_UPDATE = datetime.time(3, 00, 00)
TIME_UPDATE_D = datetime.timedelta(hours=TIME_UPDATE.hour, minutes=TIME_UPDATE.minute, seconds=TIME_UPDATE.second)

if not DEBUG:
    @uwsgidecorators.postfork
    @uwsgidecorators.thread
    def daily_update():
        print("Starting Thread...")
        while True:
            time_now = dt.now()
            time_now_d = datetime.timedelta(hours=time_now.hour, minutes=time_now.minute, seconds=time_now.second)
            time_left = TIME_UPDATE_D - time_now_d
            print("Time left to run daily_update: {} seconds".format(time_left.seconds))
            time.sleep(time_left.seconds)
            nAttemps = 0  # 3 attemps
            try:
                while ((not convida_server.daily_update()) and (nAttemps < 3)):
                    nAttemps += 1
                    time.sleep(240)
                if (nAttemps < 3):
                    f = open(os.path.join(FOLDER_LOGS, 'update.txt'), "w")
                    last_update = dt.now().strftime('%d-%m-%Y, %H:%M (GMT+1)')
                    f.write("{}".format(last_update))
                    f.close()
            except:
                print("Thread Critical Error")

PATH = os.path.dirname(__file__)
with open(PATH + '/assets/convida_dict.json', encoding='utf8') as json_file:
    convida_dict = json.load(json_file)

app = flask.Flask(__name__, template_folder="assets")

dash_app = dash.Dash(
    __name__, server=app, url_base_pathname='/',
    meta_tags=[
        {"name": "viewport", "content": "width=device-width"},
        {"name": "description", "content": convida_dict.get('description').get('ES')},
        {"name": "title", "content": "COnVIDa - {}".format(convida_dict.get('title').get('ES'))},
        {"name": "keywords", "content": convida_dict.get('keywords').get('ES')},
        {"name": "robots", "content": "index, follow"},
        {"name": "googlebot", "content": "index, follow"},
        {"name": "bingbot", "content": "index, follow"},
        {"property": "og:title", "content": "COnVIDa - {}".format(convida_dict.get('title').get('ES'))},
        {"property": "og:description", "content": convida_dict.get('description').get('ES')},
        {"property": "og:image", "content": "https://convida.inf.um.es/assets/img/convida-og.png"},
        {"property": "og:image:secure_url", "content": "https://convida.inf.um.es/assets/img/convida-og.png"},
        {"property": "og:image:type", "content": "image/png"},
        {"property": "og:image:width", "content": "666"},
        {"property": "og:image:height", "content": "666"},
        {"property": "og:url", "content": "https://convida.inf.um.es"},
        {"property": "og:type", "content": "website"},
        {"property": "og:updated_time", "content": "1440432930"},
        {"property": "og:site_name", "content": "COnVIDa"},
        {"property": "og:locale", "content": "es_ES"},
    ]
)

dash_app.scripts.config.serve_locally = False
dash_app.scripts.append_script({
    'external_url': 'https://www.googletagmanager.com/gtag/js?id=UA-166292510-1'
})


@app.route('/help')
def help_en():
    return render_template("help.html")


@app.route('/ayuda')
def help_es():
    return render_template("ayuda.html")


# An array of dictionaries with the keys 'label' and 'value',
# to be used as the options for the dropdown of Regions
regions_options = [
    {"label": str(region), "value": str(region)}
    for region in Regions.get_regions('ES')
]

# Default layout for an empty graph
empty_graph_layout = dict(
    autosize=True,
    automargin=True,
    margin=dict(l=30, r=30, b=20, t=40),
    hovermode="closest",
    plot_bgcolor="#F9F9F9",
    paper_bgcolor="#F9F9F9",
    legend=dict(font=dict(size=10), orientation="h"),
    yaxis=dict(
        type='linear'
    ),
)

# Default annotation for an empty graph
empty_graph_annotation = dict(
    text=convida_dict.get('no_regions_selected_label').get('ES'),
    x=0.5,
    y=0.5,
    align="center",
    showarrow=False,
    xref="paper",
    yref="paper",
)


def get_data_source_dropdown_options(dataSource, dataType, language):
    """Creates and returns the dropdown options for each data source.

    The dropdown options include the label, the value and the title
    for each dropdown item.

    Parameters
    ----------
    dataSource : str
        The name of the data source (e.g., 'COVID19', 'Mobility', etc.)
    dataType : DataType
        The data type for the specified data source, either TEMPORAL or GEOGRAPHICAL
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    dict array
        an array of dictionaries with the keys 'label', 'value', 'disabled' and 'title'
    """
    data_items_names = COnVIDa.get_data_items_names(dataType, language=language)
    data_items_descriptions = COnVIDa.get_data_items_descriptions(dataType, language=language)
    data_items_units = COnVIDa.get_data_items_units(dataType, language=language)

    data_source_data_items_names = data_items_names.get(dataSource + 'DataSource')
    data_source_data_items_descriptions = data_items_descriptions.get(dataSource + 'DataSource')
    data_source_data_items_units = data_items_units.get(dataSource + 'DataSource')
    data_source_options = [
        {"label": str(data_item_name), "value": str(data_item_name),
         "disabled": False, "title": str(data_item_description) + " [" + data_item_unit + "]"}
        for data_item_name, data_item_description, data_item_unit in
        zip(data_source_data_items_names, data_source_data_items_descriptions, data_source_data_items_units)
    ]
    return data_source_options


def generate_header(language):
    """Creates and returns the HTML code for the header of the dashboard

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        HTML code for the header of the dashboard including COnVIDa logo,
        title and UMU logo
    """

    return html.Div(
        [
            html.Div(
                [
                    html.A(
                        [
                            html.Img(
                                src=dash_app.get_asset_url("img/convida-logo.png"),
                                id="convida-logo",
                                style={"height": "70px"},
                            ),
                        ],
                        href="/" if language == 'ES' else "/en",
                        target="_self",
                    ),
                ],
                style={
                    "display": "block",
                    "text-align": "center",
                },
                className="one-third column",
            ),
            html.Div(
                [
                    html.H2(convida_dict.get('title').get(language)),
                ],
                className="one-half column",
                id="title",
            ),
            html.Div(
                [
                    html.A(
                        [
                            html.Img(
                                src=dash_app.get_asset_url("img/umu-logo.png"),
                                id="umu-logo",
                                style={"height": "60px"},
                            ),
                        ],
                        href="https://www.um.es",
                        target="_blank",
                    ),
                ],
                style={
                    "display": "block",
                    "text-align": "center",
                },
                className="one-third column",
            ),
        ],
        id="header",
        className="row flex-display",
    )


def generate_laguage_bar(language):
    """Creates and returns the HTML code for the languages bar of the dashboard

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        HTML code for the languages bar of the dashboard including language
        flags (Spanish and English), help icon and source code icon
    """

    return html.Div(
        [
            html.A(
                html.Img(
                    src=dash_app.get_asset_url("img/source-code.png"),
                    className="help_button",
                ),
                href="https://github.com/CyberDataLab/COnVIDa",
                target="_blank",
                title=convida_dict.get('source_code').get(language),
            ),
            html.A(
                html.Img(
                    src=dash_app.get_asset_url("img/help.svg"),
                    className="help_button",
                ),
                href="/ayuda" if language == 'ES' else "/help",
                title=convida_dict.get('help_label').get(language),
            ),
            html.Img(
                src=dash_app.get_asset_url("img/en-flag.png"),
                id="en-lang",
                n_clicks=0,
                className="lang_button",
                title=convida_dict.get('english').get(language),
            ),
            html.Img(
                src=dash_app.get_asset_url("img/es-flag.png"),
                id="es-lang",
                n_clicks=0,
                className="lang_button",
                title=convida_dict.get('spanish').get(language),
            ),
            html.Div(
                [
                    html.H6(convida_dict.get('last_update').get(language) + LAST_UPDATE),
                ],
                id="last_update",
            ),
        ],
        id="languages-bar",
        className="row flex-display",
        style={
            "display": "block",
        },
    )


def generate_data_retrieval_settings_panel(dropdown_options, language):
    """Creates and returns the HTML code for the data retrieval settings
    panel of the dashboard.

    Parameters
    ----------
    dropdown_options : dict
        A dictionary with the dropdown options for each data source
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        HTML code for the data retrieval settings panel of the dashboard
        including dates picker, regions selection and data sources selection
    """

    return html.Div(
        [
            html.Div([
                html.Div(
                    [
                        html.H6(convida_dict.get('date_range_label').get(language), className="control_label"),
                        dcc.DatePickerRange(
                            id='date-picker-range',
                            first_day_of_week=1,
                            day_size=43,
                            display_format='DD/MM/YYYY',
                            start_date=str(dt(2020, 2, 21))[0:10],
                            end_date=convida_server.get_max_date(),
                            min_date_allowed=convida_server.get_min_date(),
                            max_date_allowed=convida_server.get_max_date(),
                        ),
                    ],
                    className="data-retrieval-settings-container three columns",
                ),
                html.Div(
                    [
                        html.H6(convida_dict.get('regions_label').get(language), className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_regions_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_regions",
                            options=regions_options,
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-retrieval-settings-container three columns",
                ),
                html.Div(
                    [
                        html.H6([
                            html.Img(src=dash_app.get_asset_url("img/covid19-icon.svg"),
                                     className="data-source-icon"),
                            convida_dict.get('covid19_data_label').get(language),
                        ], className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_covid19_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_covid19",
                            options=dropdown_options['COVID19'],
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-source-container three columns",
                ),
                html.Div(
                    [
                        html.H6(convida_dict.get('further_data_sources_label').get(language), className="control_label"),
                        dcc.Checklist(
                            options=[
                                {'label': 'INE', 'value': 'ine'},
                                {'label': convida_dict.get('mobility').get(language), 'value': 'mobility'},
                                {'label': 'MoMo', 'value': 'momo'},
                                {'label': 'AEMET', 'value': 'aemet'},
                            ],
                            id="further-data-sources",
                        ),
                    ],
                    className='data-retrieval-settings-container three columns',
                ),
            ],
            ),
            html.Div([
                html.Div(
                    [
                        html.H6([
                            html.Img(src=dash_app.get_asset_url("img/ine-icon.svg"),
                                     className="data-source-icon"),
                            convida_dict.get('ine_data_label').get(language),
                        ], className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_ine_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_ine",
                            options=dropdown_options['INE'],
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-source-container three columns",
                    id="ine-data-source-container",
                    style={"display": "none"},
                ),
                html.Div(
                    [
                        html.H6([
                            html.Img(src=dash_app.get_asset_url("img/mobility-icon.svg"),
                                     className="data-source-icon"),
                            convida_dict.get('mobility_data_label').get(language),
                        ], className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_mobility_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_mobility",
                            options=dropdown_options['Mobility'],
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-source-container three columns",
                    id="mobility-data-source-container",
                    style={"display": "none"},
                ),
                html.Div(
                    [
                        html.H6([
                            html.Img(src=dash_app.get_asset_url("img/momo-icon.svg"),
                                     className="data-source-icon"),
                            convida_dict.get('momo_data_label').get(language),
                        ], className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_momo_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_momo",
                            options=dropdown_options['MoMo'],
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-source-container three columns",
                    id="momo-data-source-container",
                    style={"display": "none"},
                ),
                html.Div(
                    [
                        html.H6([
                            html.Img(src=dash_app.get_asset_url("img/aemet-icon.svg"),
                                     className="data-source-icon"),
                            convida_dict.get('aemet_data_label').get(language),
                        ], className="control_label"),
                        html.Button(convida_dict.get('select_all_label').get(language),
                                    id="select_all_aemet_button",
                                    n_clicks=0,
                                    className="select-all-button",
                                    ),
                        dcc.Dropdown(
                            id="selected_aemet",
                            options=dropdown_options['AEMET'],
                            multi=True,
                            className="dcc_control",
                            placeholder=convida_dict.get('select_label').get(language)
                        ),
                    ],
                    className="data-source-container three columns",
                    id="aemet-data-source-container",
                    style={"display": "none"},
                ),
            ],
                id="further_data_sources_container",
            ),

        ],
        className="pretty_container",
        id="data-retrieval-settings-panel",
        style={"display": "grid"},
    )


def generate_modal_window(id, language):
    """Creates and returns the HTML code for the modal window to download
    the queried data.

    Parameters
    ----------
    id : str
        Identifier of the modal window to be created
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        HTML code for the modal window to download the queried data
        including download buttons for several file types
    """

    return dbc.Modal(
        [
            dbc.ModalHeader(convida_dict.get('select_data_format_label').get(language)),
            dbc.ModalBody(
                html.Div(
                    id="download-area-{}".format(id),
                    className="block container-display",
                    children=[]
                )
            ),
            dbc.ModalFooter(
                dbc.Button(convida_dict.get('close').get(language), id="close-{}".format(id), className="ml-auto",
                           style={"width": "20%"})
            ),
        ],
        id=id,
    )


def generate_graph_container(language, graph_type):
    """Creates and returns the HTML code for the graph container
    of the dashboard.

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    graph_type : str
        The type of graph to be generated (e.g., 'temporal' or 'regional')

    Returns
    -------
    html
        HTML code for the graph container of the dashboard
        including the loading wheel functionality
    """

    return html.Div(
        [
            dcc.Loading(
                [
                    dcc.Graph(
                        id="{}_graph".format(graph_type),
                        config={
                            "locale": "es" if language == 'ES' else "en-US",
                            "displaylogo": False,
                        },
                        figure={
                            "layout": empty_graph_layout,
                        },
                    )
                ],
                type="circle",
            )
        ],
        id="{}-graph-container".format(graph_type),
        className="pretty_container",
    )


def generate_graph_settings_container(language, graph_type):
    """Creates and returns the HTML code for the graph settings
    container of the dashboard.

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    graph_type : str
        The type of graph whose settings are to be generated
        (e.g., 'temporal' or 'regional')

    Returns
    -------
    html
        HTML code for the graph settings container of the dashboard
        including the type of graph (lines or bars) and the plot
        scale (linear or logarithmic).
    """

    return html.Div(
        [
            html.Div(
                [
                    html.H6(convida_dict.get('graph_type_label').get(language),
                            className="control_label"),
                    dcc.Dropdown(
                        id="{}_selected_graph_type".format(graph_type),
                        options=[
                            {"label": convida_dict.get('lines_graph_type_label').get(language),
                             "value": "lines"},
                            {"label": convida_dict.get('bars_graph_type_label').get(language),
                             "value": "bars"},
                        ],
                        multi=False,
                        value='lines',
                        clearable=False,
                        className="dcc_control",
                        searchable=False
                    ),
                ],
                style={"width": "100%"},
            ),
            html.Div(
                [
                    html.H6(convida_dict.get('plot_scale_label').get(language),
                            className="control_label"),
                    dcc.RadioItems(
                        id="{}_selected_plot_scale".format(graph_type),
                        value="Linear",
                        options=[
                            {"label": convida_dict.get('plot_scale_linear_label').get(language),
                             "value": "Linear"},
                            {"label": convida_dict.get('plot_scale_log_label').get(language),
                             "value": "Log"},
                        ],
                        labelStyle={"display": "inline-block"},
                        className="dcc_control",
                    ),
                ],
                style={"width": "100%"},
            ),
        ],
        id="graph-settings-container-{}".format(graph_type),
        className="pretty_container",
        style={"display": "flex"},
    )


def generate_table_container(language, table_type):
    """Creates and returns the HTML code for the table
    container of the dashboard.

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    table_type : str
        The type of table to be generated (e.g., 'temporal' or 'regional')

    Returns
    -------
    html
        HTML code for the table container of the dashboard
        including the summary table itself, the downloading
        buttons (for raw data and summary), as well as a
        legend.
    """

    return html.Div(
        [
            html.Div(
                [html.H6(convida_dict.get('summary_table_label').get(language),
                         className="control_label")]
            ),
            html.Div(
                [],
                id="{}-summary-table".format(table_type),
                style={"display": "flex"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            dbc.Button(convida_dict.get('save_raw_data_label').get(language),
                                       id="{}-save-raw-data-button".format(table_type),
                                       className="button",
                                       style={"margin-bottom": "20px"},
                                       n_clicks=0),
                            dbc.Button(convida_dict.get('save_summary_data_label').get(language),
                                       id="{}-save-summary-table-button".format(table_type),
                                       className="button",
                                       n_clicks=0),
                        ],
                        className="one-half column save-buttons",
                        style={"text-align": "center"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(convida_dict.get('legend').get(language),
                                            className="control_label"),
                                    html.Div(
                                        [html.Strong("count: "), convida_dict.get('count-meaning').get(language)],
                                    ),
                                    html.Div(
                                        [html.Strong(html.A("mean",
                                                            href=convida_dict.get('mean-wiki-link').get(language),
                                                            target="_blank"),
                                                     ), html.Strong(": "),
                                         convida_dict.get('mean-meaning').get(language)],
                                    ),
                                    html.Div(
                                        [html.Strong(html.A("std",
                                                            href=convida_dict.get('std-wiki-link').get(language),
                                                            target="_blank"),
                                                     ), html.Strong(": "),
                                         convida_dict.get('std-meaning').get(language)],
                                    ),
                                    html.Div(
                                        [html.Strong("min: "), convida_dict.get('min-meaning').get(language)],
                                    ),
                                    html.Div(
                                        [html.Strong("25%: "),
                                         html.A(convida_dict.get('percentile').get(language),
                                                href=convida_dict.get('percentile-wiki-link').get(language),
                                                target="_blank"), " 25"],
                                    ),
                                    html.Div(
                                        [html.Strong("50%: "),
                                         html.A(convida_dict.get('median').get(language),
                                                href=convida_dict.get('median-wiki-link').get(language),
                                                target="_blank")],
                                    ),
                                    html.Div(
                                        [html.Strong("75%: "),
                                         html.A(convida_dict.get('percentile').get(language),
                                                href=convida_dict.get('percentile-wiki-link').get(language),
                                                target="_blank"), " 75"],
                                    ),
                                    html.Div(
                                        [html.Strong("max: "), convida_dict.get('max-meaning').get(language)],
                                    ),
                                ],
                                className="summary-table-legend-container",
                                id="{}-summary-table-legend-container".format(table_type)
                            ),
                        ],
                        className="one-half column",
                    ),
                ],
                className="row container-display",
            ),
        ],
        className="pretty_container",
        id="{}-summary-table-container".format(table_type),
        style={"display": "none"}
    )


def generate_graph_and_table_containers(language, graph_type):
    """Creates and returns the HTML code for the graph and table
    container of the dashboard.

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    graph_type : str
        The type of graph (and table) to be generated (e.g., 
        'temporal' or 'regional')

    Returns
    -------
    html
        HTML code for the graph container, the graph settings
        and the table container of the dashboard.
    """

    return html.Div(
        [
            html.H6(
                convida_dict.get("{}_visualization_label".format(graph_type)).get(language),
                className="control_label",
                style={"padding-bottom": "5px",
                       "font-size": "1.8rem"},
            ),
            generate_graph_container(language, graph_type),
            generate_graph_settings_container(language, graph_type),
            generate_table_container(language, graph_type),
        ],
    )


def generate_layout(language):
    """Creates and returns the initial HTML layout of the dashboard.

    Parameters
    ----------
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        initial HTML code of the COnVIDa dashboard
    """

    dash_app.title = 'COnVIDa - ' + convida_dict.get('title').get(language)
    # Generate options for dropdowns
    dropdown_options = {}
    dropdown_options['INE'] = get_data_source_dropdown_options('INE', DataType.GEOGRAPHICAL, language)
    for dataSource in ['COVID19', 'Mobility', 'MoMo', 'AEMET']:
        dropdown_options[dataSource] = get_data_source_dropdown_options(dataSource, DataType.TEMPORAL, language)

    return html.Div(
        [
            dcc.Store(id="LANG", data=language, storage_type="local"),
            dcc.Store(id="temporal_query_params", data=None),
            dcc.Store(id="regional_query_params", data=None),
            dcc.Store(id="dropdown_options", data=dropdown_options),

            generate_modal_window('temporal-modal-raw-data-table', language),
            generate_modal_window('temporal-modal-summary-table', language),
            generate_modal_window('regional-modal-raw-data-table', language),
            generate_modal_window('regional-modal-summary-table', language),

            # empty Div to trigger javascript file for graph resizing
            html.Div(id="output-clientside"),

            generate_header(language),
            generate_laguage_bar(language),
            generate_data_retrieval_settings_panel(dropdown_options, language),

            generate_graph_and_table_containers(language, "temporal"),
            generate_graph_and_table_containers(language, "regional"),

            html.Footer(
                [
                    html.Div(html.H6(convida_dict.get('footer_1').get(language))),
                    html.Div(convida_dict.get('footer_2').get(language), style={"display": "inline"}),
                    html.A("convida@listas.um.es", href="mailto:convida@listas.um.es")
                ],
                className="convida_footer",
            )
        ],
        id="mainContainer",
        style={"display": "flex", "flexDirection": "column"},
    )


dash_app.layout = html.Div(generate_layout('ES'), id="convida_main_container")


@dash_app.callback(
    [Output("LANG", "data"), Output("convida_main_container", "children")],
    [Input("es-lang", "n_clicks"), Input("en-lang", "n_clicks")],
)
def set_language(n_clicks_es, n_clicks_en):
    if n_clicks_en == 1:
        return 'EN', generate_layout('EN')
    return 'ES', generate_layout('ES')


@dash_app.callback(
    Output("selected_regions", "value"),
    [Input("select_all_regions_button", "n_clicks")],
)
def select_all_regions(n_clicks):
    if n_clicks > 0:
        return [dropdown_option.get("label") for dropdown_option in regions_options]
    return []


def select_all_data_items(n_clicks, dropdown_options, dataSource):
    if n_clicks > 0:
        return [dropdown_option.get("label") for dropdown_option in dropdown_options[dataSource]]
    return []


for dataSource in ["COVID19", "Mobility", "INE", "MoMo", "AEMET"]:
    dash_app.callback(
        Output("selected_{}".format(dataSource.lower()), "value"),
        [Input("select_all_{}_button".format(dataSource.lower()), "n_clicks")],
        [State("dropdown_options", "data")]
    )(partial(select_all_data_items, dataSource=dataSource))


@dash_app.callback(
    [
        Output('ine-data-source-container', 'style'),
        Output('mobility-data-source-container', 'style'),
        Output('momo-data-source-container', 'style'),
        Output('aemet-data-source-container', 'style'),
    ],
    [
        Input('further-data-sources', 'value'),
    ],
)
def toggle_further_data_sources(selected_further_data_sources):
    none = {'display': 'none'}
    block = {'display': 'block'}

    if selected_further_data_sources is None:
        return none, none, none, none

    output = []
    for data_source in ["ine", "mobility", "momo", "aemet"]:
        if data_source in selected_further_data_sources:
            output.append(block)
        else:
            output.append(none)

    return output


def update_graph_and_table(start_date, end_date,
                           selected_regions, selected_covid19,
                           selected_ine, selected_mobility,
                           selected_momo, selected_aemet,
                           selected_graph_type,
                           selected_plot_scale,
                           language,
                           analysis_type):
    """Updates graph and table given the specified query parameters.

    Given the specified query parameters it retrieves the corresponding
    data items, plots them in the graph, and displays them in the
    summary table.

    Parameters
    ----------
    start_date : str
        The start date for the time window of queried data
    end_date : str
        The end date for the time window of queried data
    selected_regions : list
        The list of regions (as str) for which to query data
    selected_covid19 : list
        The list of data items to query from the COVID19 data source
    selected_ine : list
        The list of data items to query from the INE data source
    selected_mobility : list
        The list of data items to query from the Mobility data source
    selected_momo : list
        The list of data items to query from the MoMo data source
    selected_aemet : list
        The list of data items to query from the AEMET data source
    selected_graph_type : str
        The selected type of graph to be plotted (e.g., 'lines' or 'bars`)
    selected_plot_scale : str
        The selected scale of the graph to be plotted (e.g., 'linear'
        or 'logarithmic`)
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    analysis_type : str
        The type of visualization for the graph (e.g., 'temporal' or
        'regional')

    Returns
    -------
    dict
        a dict with the figure data and its layout
    DataTable
        a Dash DataTable containing the queried data
    CSS style
        table container CSS style ('none' or 'block')
    list
        the list of query parameters to be stored in a Dash Store
    """

    layout_graph = copy.deepcopy(empty_graph_layout)
    selected_temporal_data_items = selected_covid19 + selected_mobility + selected_momo + selected_aemet
    selected_data_items = selected_temporal_data_items + selected_ine

    # No data to plot
    if ((len(selected_regions) == 0) or (len(selected_data_items) == 0) or
            ((len(selected_temporal_data_items) == 0) and (analysis_type == 'temporal'))):

        if len(selected_regions) == 0:
            empty_graph_annotation['text'] = convida_dict.get('no_regions_selected_label').get(language)
        elif len(selected_data_items) == 0:
            empty_graph_annotation['text'] = convida_dict.get('no_data_selected_label').get(language)
        elif len(selected_temporal_data_items) == 0:
            empty_graph_annotation['text'] = convida_dict.get('no_temporal_data_selected_label').get(language)

        layout_graph["annotations"] = [empty_graph_annotation]

        figure = dict(data=[], layout=layout_graph)
        output = [figure, [], {"display": "none"}, []]
        return output

    layout_graph["dragmode"] = "select"
    layout_graph["showlegend"] = True
    layout_graph["autosize"] = True

    layout_graph["yaxis"]["type"] = 'linear' if selected_plot_scale == 'Linear' else 'log'
    graph_type = "scatter" if selected_graph_type == 'lines' else "bar"
    logging = True if analysis_type == 'temporal' else False #To avoid double logging

    dfQuery = query_data(start_date, end_date, selected_regions,
                         selected_temporal_data_items,
                         selected_ine,
                         analysis_type, language, logging)

    data = []
    for column in list(dfQuery.columns.values):
        data.append(
            dict(
                type=graph_type,
                mode="lines+markers",
                name=str(column),
                x=dfQuery.index,
                y=dfQuery[column],
                line=dict(shape="spline", smoothing=2, width=1),
                marker=dict(symbol="diamond-open"),
            ),
        )
    graph = dict(data=data, layout=copy.deepcopy(layout_graph))
    table = get_summary_table(dfQuery)

    output = [graph, table, {"display": "block"},
            [start_date, end_date, selected_regions,
            selected_temporal_data_items, selected_ine]]
    return output


for analysis_type in ('temporal', 'regional'):
    dash_app.callback(
        [
            Output("{}_graph".format(analysis_type), "figure"),
            Output("{}-summary-table".format(analysis_type), "children"),
            Output("{}-summary-table-container".format(analysis_type), "style"),
            Output("{}_query_params".format(analysis_type), "data"),
        ],
        [
            Input('date-picker-range', 'start_date'),
            Input('date-picker-range', 'end_date'),
            Input("selected_regions", "value"),
            Input("selected_covid19", "value"),
            Input("selected_ine", "value"),
            Input("selected_mobility", "value"),
            Input("selected_momo", "value"),
            Input("selected_aemet", "value"),
            Input("{}_selected_graph_type".format(analysis_type), "value"),
            Input("{}_selected_plot_scale".format(analysis_type), "value"),
        ],
        [
            State("LANG", "data"),
        ]
    )(partial(update_graph_and_table, analysis_type=analysis_type))


def query_data(start_date, end_date, selected_regions,
               selected_temporal_data_items, selected_geographical_data_items,
               analysis_type, language, logging=False) -> pd.DataFrame:
    """Retrieves and returns data items according to the specified query parameters.

    Given the specified query parameters it retrieves the corresponding
    data items, stores them in a DataFrame and returns such DataFrame.

    Parameters
    ----------
    start_date : str
        The start date for the time window of queried data
    end_date : str
        The end date for the time window of queried data
    selected_regions : list
        The list of regions (as str) for which to query data
    selected_temporal_data_items : list
        The list of temporal data items to query
    selected_geographical_data_items : list
        The list of geographical data items to query
    analysis_type : str
        The type of analysis for the queried data (e.g.,
        'temporal' or 'geographical')
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    logging : bool
        Boolean to indicate whether to log this query or not

    Returns
    -------
    DataFrame
        a DataFrame containing all the queried data items
    """

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    dfTemp = pd.DataFrame()
    if len(selected_temporal_data_items) > 0:
        dfTemp = convida_server.get_data_items(data_items=selected_temporal_data_items,
                                               regions=selected_regions,
                                               start_date=start, end_date=end, language=language)

    if analysis_type == "temporal":
        dfQuery = dfTemp
    else:
        if len(selected_temporal_data_items) > 0:
            # Convert temporal data to geographical data by keeping the mean values
            dfTemp = dfTemp.mean(axis='index').unstack()

        dfGeo = pd.DataFrame()
        if len(selected_geographical_data_items) > 0:
            dfGeo = convida_server.get_data_items(data_items=selected_geographical_data_items,
                                                  regions=selected_regions, language=language)

        dfQuery = pd.concat([dfTemp, dfGeo], axis=1)

    if logging:
        query = dict()
        query['timestamp_date'] = dt.now().strftime('%Y-%m-%d')
        query['timestamp_time'] = dt.now().strftime('%H:%M')
        query['ip_address'] = request.environ['REMOTE_ADDR'] if request.environ.get('HTTP_X_FORWARDED_FOR') is None else request.environ['HTTP_X_FORWARDED_FOR']
        query['user_agent'] = request.headers.get('User-Agent')
        query['language'] = language
        query['start_date'] = start_date
        query['end_date'] = end_date
        query['regions'] = selected_regions
        query['data_items'] = selected_temporal_data_items + selected_geographical_data_items

        with open(os.path.join(FOLDER_LOGS, 'queries.log'), "a", encoding='utf8') as json_file:
            json.dump(query, json_file, ensure_ascii=False)

    return dfQuery


def get_summary_table(dfQuery) -> dash_table.DataTable:
    """Builds and returns a DataTable from the specified DataFrame.

    Given the specified DataFrame it builds and returns the corresponding
    DataTable.

    Parameters
    ----------
    dfQuery : DataFrame
        The DataFrame containing all the queried data items

    Returns
    -------
    DataTable
        a DataTable with all the queried data items contained in the given DataFrame
    """

    if dfQuery.empty:
        return []

    summary_table = dfQuery.describe()
    summary_table = summary_table.round(2)
    summary_table = summary_table.transpose()
    summary_table = summary_table.reset_index()
    summary_table = summary_table.rename(columns={'index': ''})

    summary_data_table = dash_table.DataTable(
        id='summary_table',
        columns=[{"name": col, "id": col} for col in summary_table.columns],
        data=summary_table.to_dict('records'),
        style_cell_conditional=[
            {
                'if': {'column_id': cell},
                'textAlign': 'left',
            } for cell in ['Date', 'Region']
        ],
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        tooltip_data=[
            {
                column: {'value': str(value), 'type': 'text'}
                for column, value in row.items()
            } for row in summary_table.to_dict('rows')
        ],
        css=[
            {'selector': '.previous-next-container', 'rule': 'display: flex; float: left'},
            {'selector': '.page-number', 'rule': 'display: ruby'},
            {'selector': '.current-page', 'rule': 'min-width: 40px'},
        ],
        sort_action='native',
        page_size=10,
    )
    return summary_data_table


def toggle_modal_save_raw_data(n1, n2, is_open, query_params, language, table_type):
    """Displays a modal window to save all the queried data items.

    Given the specified query parameters it retrieves the corresponding
    data items, stores them in a DataFrame, saves it into several file
    types and displays a modal window for the user to download them.

    Parameters
    ----------
    query_params : list
        The list of query parameters containing 1) the start date, 2) the
        end date, 3) the selected regions, 4) the temporal data items to
        query, 5) the geographical data items to query
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    table_type : str
        The type of graph associated to this table (e.g., 'temporal' or
        'regional')

    Returns
    -------
    bool
        whether to display or hide the modal window
    html
        html div containing the downloading buttons
    """

    if query_params is None:
        raise PreventUpdate

    if is_open:
        return not is_open, [create_download_buttons("", "", "", "", language)]

    start_date = query_params[0]
    end_date = query_params[1]
    selected_regions = query_params[2]
    selected_temporal_data_items = query_params[3]
    selected_ine = query_params[4]
    analysis_type = table_type

    dfQuery = query_data(start_date, end_date, selected_regions,
                         selected_temporal_data_items,
                         selected_ine,
                         analysis_type, language)

    uriCSV, uriHTML, uriJSON, uriXML = create_files(dfQuery)
    return not is_open, [create_download_buttons(uriCSV, uriHTML, uriJSON, uriXML, language)]


for table_type in ("temporal", "regional"):
    dash_app.callback(
        [Output("{}-modal-raw-data-table".format(table_type), "is_open"), Output("download-area-{}-modal-raw-data-table".format(table_type), "children")],
        [Input("{}-save-raw-data-button".format(table_type), "n_clicks"), Input("close-{}-modal-raw-data-table".format(table_type), "n_clicks")],
        [State("{}-modal-raw-data-table".format(table_type), "is_open"), State("{}_query_params".format(table_type), "data"), State("LANG", "data")],
    )(partial(toggle_modal_save_raw_data, table_type=table_type))


def toggle_modal_save_summary_table(n1, n2, is_open, query_params, language, table_type):
    """Displays a modal window to save a summary of all the queried data items.

    Given the specified query parameters it retrieves the corresponding
    data items, stores them in a DataFrame, computes a summary of it,
    saves such summary into several file types and displays a modal
    window for the user to download them.

    Parameters
    ----------
    query_params : list
        The list of query parameters containing 1) the start date, 2) the
        end date, 3) the selected regions, 4) the temporal data items to
        query, 5) the geographical data items to query
    language : str
        The language to be used (e.g., 'ES' or 'EN')
    table_type : str
        The type of graph associated to this table (e.g., 'temporal' or
        'regional')

    Returns
    -------
    bool
        whether to display or hide the modal window
    html
        html div containing the downloading buttons
    """

    if query_params is None:
        raise PreventUpdate

    if is_open:
        return not is_open, [create_download_buttons("", "", "", "", language)]

    start_date = query_params[0]
    end_date = query_params[1]
    selected_regions = query_params[2]
    selected_temporal_data_items = query_params[3]
    selected_ine = query_params[4]
    analysis_type = table_type

    dfQuery = query_data(start_date, end_date, selected_regions,
                         selected_temporal_data_items,
                         selected_ine,
                         analysis_type, language)

    summary_table = dfQuery.describe()
    summary_table = summary_table.round(2)
    summary_table = summary_table.transpose()
    summary_table = summary_table.reset_index()
    summary_table = summary_table.rename(columns={'index': ''})

    uriCSV, uriHTML, uriJSON, uriXML = create_files(summary_table)
    return not is_open, [create_download_buttons(uriCSV, uriHTML, uriJSON, uriXML, language)]


for table_type in ("temporal", "regional"):
    dash_app.callback(
        [Output("{}-modal-summary-table".format(table_type), "is_open"), Output("download-area-{}-modal-summary-table".format(table_type), "children")],
        [Input("{}-save-summary-table-button".format(table_type), "n_clicks"), Input("close-{}-modal-summary-table".format(table_type), "n_clicks")],
        [State("{}-modal-summary-table".format(table_type), "is_open"), State("{}_query_params".format(table_type), "data"), State("LANG", "data")],
    )(partial(toggle_modal_save_summary_table, table_type=table_type))


def create_download_buttons(uriCSV, uriHTML, uriJSON, uriXLS, language):
    """Creates the html buttons to download the specified files.

    Given the specified files containing either the queried data items
    or a summary of them, it creates the html buttons to download such
    specified files.

    Parameters
    ----------
    uriCSV : str
        URI of the CSV file
    uriHTML : str
        URI of the HTML file
    uriJSON : str
        URI of the JSON file
    uriXLS : str
        URI of the XLS file
    language : str
        The language to be used (e.g., 'ES' or 'EN')

    Returns
    -------
    html
        html div containing the downloading buttons
    """

    downloading_buttons = html.Div([
        html.Form(
            action=uriCSV,
            method="get",
            className="form-modal",
            children=[
                html.Button(
                    className="button button-modal",
                    type="submit",
                    children=[
                        html.Div([html.Img(
                            src=dash_app.get_asset_url("img/csv.svg"),
                            style={
                                "height": "35px",
                            },
                        ), convida_dict.get('download').get(language) + " CSV"], className="container-button-modal"),

                    ]
                )
            ],
        ),
        html.Form(
            action=uriXLS,
            method="get",
            className="form-modal",
            children=[
                html.Button(
                    className="button button-modal",
                    type="submit",
                    children=[
                        html.Div([html.Img(
                            src=dash_app.get_asset_url("img/xls.svg"),
                            style={
                                "height": "35px",
                            },
                        ), convida_dict.get('download').get(language) + " XLS"], className="container-button-modal"),

                    ]
                )
            ],
        ),
        html.Form(
            action=uriJSON,
            method="get",
            className="form-modal",
            children=[
                html.Button(
                    className="button button-modal",
                    type="submit",
                    children=[
                        html.Div([html.Img(
                            src=dash_app.get_asset_url("img/json.svg"),
                            style={
                                "height": "35px",
                            },
                        ), convida_dict.get('download').get(language) + " JSON"], className="container-button-modal"),

                    ]
                )
            ],
            style={'display': 'block'} if uriJSON else {'display': 'none'}
        ),
        html.Form(
            action=uriHTML,
            method="get",
            className="form-modal",
            children=[
                html.Button(
                    className="button button-modal",
                    type="submit",
                    children=[
                        html.Div([html.Img(
                            src=dash_app.get_asset_url("img/html.svg"),
                            style={
                                "height": "35px",
                            },
                        ), convida_dict.get('download').get(language) + " HTML"], className="container-button-modal"),

                    ]
                )
            ],
        ),
    ], className="row flex-display"
    )
    return downloading_buttons


@app.route('/tmp/<path:path>')
def serve_static(path):
    root_dir = os.getcwd()
    return flask.send_from_directory(
        os.path.join(root_dir, 'tmp'), path
    )


def create_files(df):
    """Creates several files to be downloaded from the given DataFrame.

    Given the specified DataFrame containing either the queried data items
    or a summary of them, it transforms such DatFrame into several file types
    to be further downloaded.

    Parameters
    ----------
    df : DataFrame
        DataFrame containing either the queried data items or a summary of them

    Returns
    -------
    str
        URI of the CSV file
    str
        URI of the HTML file
    str
        URI of the JSON file
    str
        URI of the XLS file
    """

    # Create CSV
    filename = f"{uuid.uuid1()}.csv"
    uriCSV = f"tmp/{filename}"

    df.to_csv(uriCSV)

    # Create HTML
    filename = f"{uuid.uuid1()}.html"
    uriHTML = f"tmp/{filename}"

    df.to_html(uriHTML)

    # Create JSON
    filename = f"{uuid.uuid1()}.json"
    uriJSON = f"tmp/{filename}"

    try:
        json = df.to_json(force_ascii=False)
        with open(uriJSON, "w", encoding='utf8') as file:
            file.write(json)

    except:
        uriJSON = None

    # Convert to XML
    filename = f"{uuid.uuid1()}.xls"
    uriXLS = f"tmp/{filename}"

    df.to_excel(uriXLS)

    return uriCSV, uriHTML, uriJSON, uriXLS


# Main
if __name__ == "__main__":
    if not os.path.exists(os.path.join(FOLDER_LOGS, 'queries.log')):
        with open(os.path.join(FOLDER_LOGS, 'queries.log'), 'w'): pass
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)