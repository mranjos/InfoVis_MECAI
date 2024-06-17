import faicons as fa
import plotly.express as px
from shinywidgets import render_plotly

from shiny import reactive, render, req
from shiny.express import input, ui

from pathlib import Path
from datetime import date

import polars as pl
import polars.selectors as cs
import pandas as pd
import folium
from folium import plugins
import matplotlib.pyplot as plt
import squarify
import plotly.express as px

# Load data and compute static values
tips = px.data.tips()
bill_rng = (min(tips.total_bill), max(tips.total_bill))

caminho_base = Path(r'D:\Lenovo\1 - Estudos\6 - Mestrado\3 - Materias\MAI5017 - Visualização da Informação\Bases\Veiculos Subtraidos')
caminho_base_csv = caminho_base.joinpath("VeiculosSubtraidos_2024.csv")
valores_na = ["NULL", "NA", "N/A", "NaN"]

df = pl.scan_csv(caminho_base_csv, has_header=True, separator=";", low_memory=True, infer_schema_length=1000, null_values=valores_na) #precisa coletar, pois é só uma representação

@reactive.Calc
def df_filtro():
    cidade_key = input.select_cidade()
    cidade = {"cd1": "RIBEIRAO PRETO", "cd2": "S.CARLOS"}[cidade_key]
    df_filtrado = df.filter(pl.col('CIDADE') == cidade)
    return df_filtrado

@reactive.Calc
def obter_bairros_unicos():
    cidade_key = input.select_cidade()
    cidade = {"cd1": "RIBEIRAO PRETO", "cd2": "S.CARLOS"}[cidade_key]
    df_filtrado = df.filter(pl.col('CIDADE') == cidade)
    # Obter valores únicos da coluna 'category'
    unique_values = df_filtrado.select('BAIRRO').unique().collect().to_series().drop_nans().to_list()
    unique_values = [value for value in unique_values if value and value.strip()]

    # Criar um dicionário de opções para o select input
    options = {value: value for value in unique_values}
    return options

@reactive.effect
def update_bairros():
    bairros = obter_bairros_unicos()
    ui.update_select("select_bairro", choices=bairros)

# Add page title and sidebar
ui.page_opts(title="Segurança pública Roubos/Furtos na cidade de Ribeirão Preto", fillable=True)
with ui.sidebar(open="desktop"):
    ui.input_select("select_cidade", "Escolha uma opção:", {"cd1": "RIBEIRAO PRETO"}),
    ui.input_select("select_tipo_roubo", "Escolha uma opção:", {"op1": "Veículos", "op2": "Celulares"}),
    ui.input_select("select_ano", "Selecione o Ano:", {"an0": "Geral","an1": "2024", "an2": "2023"}),
    ui.input_select("select_bairro", "Selecione o Bairro:", {}),

    ui.input_slider("total_bill", "Bill amount", min=bill_rng[0], max=bill_rng[1], value=bill_rng, pre="$")
    ui.input_checkbox_group("time", "Food service", ["Lunch", "Dinner"], selected=["Lunch", "Dinner"], inline=True)
    ui.input_action_button("reset", "Reset filter")

# Add main content
ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "currency-dollar": fa.icon_svg("dollar-sign"),
    "gear": fa.icon_svg("gear")
}

with ui.layout_columns(fill=False):

    with ui.value_box(showcase=ICONS["user"]):
        "Total tippers"
        @render.express
        def total_tippers():
            input.select_bairro()
            #tips_data().shape[0]

    with ui.value_box(showcase=ICONS["wallet"]):
        "Average tip"
        @render.express
        def average_tip():
            d = tips_data()
            if d.shape[0] > 0:
                perc = d.tip / d.total_bill
                f"{perc.mean():.1%}"

    with ui.value_box(showcase=ICONS["currency-dollar"]):
        "Average bill"
        @render.express
        def average_bill():
            d = tips_data()
            if d.shape[0] > 0:
                bill = d.total_bill.mean()
                f"${bill:.2f}"


with ui.layout_columns(col_widths=[6, 6, 12]):

    with ui.card(full_screen=True):
        ui.card_header("Dados")
        @render.data_frame
        def table():
            return render.DataGrid(df_filtro().select(['CIDADE','BAIRRO', 'LATITUDE', 'LONGITUDE']).collect().to_pandas().dropna(subset=['LATITUDE', 'LONGITUDE']))

    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Total bill vs tip"
            with ui.popover(title="Add a color variable", placement="top"):
                ICONS["gear"]
                ui.input_radio_buttons(
                    "scatter_color", None,
                    ["none", "sex", "smoker", "day", "time"],
                    inline=True
                )

        @render_plotly
        def scatterplot():
            color = input.scatter_color()
            return px.scatter(
                tips_data(),
                x="total_bill",
                y="tip",
                color=None if color == "none" else color,
                trendline="lowess"
            )

    with ui.card(full_screen=True,min_height="500px"):
        ui.card_header("Mapa de Calor")

        @render.ui
        def plot_heatmap():
            # Criar um mapa centrado em São Carlos (coordenadas fornecidas como exemplo)
            mapa = folium.Map(location=[-21.1767, -47.8208], zoom_start=13)

            df_filtro_map = df_filtro().select(['CIDADE','BAIRRO', 'LATITUDE', 'LONGITUDE']).collect().to_pandas().dropna(subset=['LATITUDE', 'LONGITUDE'])

            mapa.add_child(plugins.HeatMap(df_filtro_map.loc[:, ['LATITUDE', 'LONGITUDE']]))

            return mapa


# --------------------------------------------------------
# Reactive calculations and effects
# --------------------------------------------------------

@reactive.calc
def tips_data():
    bill = input.total_bill()
    idx1 = tips.total_bill.between(bill[0], bill[1])
    idx2 = tips.time.isin(input.time())
    return tips[idx1 & idx2]

@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_slider("total_bill", value=bill_rng)
    ui.update_checkbox_group("time", selected=["Lunch", "Dinner"])