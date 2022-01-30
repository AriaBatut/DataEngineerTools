from flask import Flask

import os, wget

import pandas as pd
from yahoo_fin.stock_info import get_data

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly
import plotly.express as px
import ipywidgets

import pymongo
from bs4 import BeautifulSoup
import requests
import re
import random
import json


# ______________________________________
# Extraction des PTZ
if not (os.path.isfile("ptz.csv")):
    file = "ptz.txt"
    if not (os.path.isfile(file)):
        url = "https://www.data.gouv.fr/fr/datasets/r/eac9a237-0907-45e7-a41e-ff2c171fe10d"
        wget.download(url, file)

    data_ptz = pd.read_csv(file, sep="\t", low_memory=False, encoding='cp1252')
    result_ptz = pd.DataFrame()

    data_ptz_cins = data_ptz[["an", "cins", "pm2"]].dropna()

    # On regroupe par années par communes
    for year in data_ptz_cins["an"].unique():
        data_year = data_ptz_cins[data_ptz_cins["an"] == year]
        result_ptz = result_ptz.append(data_year.groupby("cins").mean().reset_index())

    result_ptz["cins"] = pd.to_numeric(result_ptz["cins"], errors='coerce')
    result_ptz["commu"] = [(x - x%1000)/1000 for x in result_ptz["cins"]]
    result_ptz["an"] = result_ptz["an"].astype(int)
    result_ptz.to_csv("ptz.csv")
ptz = pd.read_csv("ptz.csv")
# ______________________________________



# ______________________________________
# Liste des colonnes de l'API qui existent 
API_col = [{'label': 'Open', 'value': 'Open'},
           {'label': 'High', 'value': 'High'},
           {'label': 'Low', 'value': 'Low'},
           {'label': 'Close', 'value': 'Close'},
           {'label': 'Adj Close', 'value': 'Adj Close'},
           {'label': 'Volume', 'value': 'Volume'},
          ]


# Liste des tickers que l'on peut utiliser
API_tickers = [{'label': 'CAC 40', 'value': '^FCHI'},
               {'label': 'S&P 500', 'value': '^GSPC'},
              ]


# Extraire les données en direct de l'API
def extract_api(ticker):
    return get_data(ticker, interval="1d").reset_index().drop(["ticker"], axis=1).rename(columns={"open": "Open",
                                                "high": "High",
                                                "low": "Low",
                                                "close": "Close",
                                                "adjclose": "Adj Close",
                                                "volume": "Volume",
                                                "index": "Date",
                                               })

# Afficher l'évolution d'un paramètre de la bourse
def plotly_api(df, y, name):
    fig = px.line(df, x="Date", y=y)
    fig.update_layout(title="Suivi de " + y + " en fonction de la Date sur le " + name + " (API en direct) :",
                      xaxis_title="Date",
                      yaxis_title=y,
                      ),
    fig.update_layout(template='plotly_dark',
                      plot_bgcolor='rgba(0, 0, 0, 0)',
                      paper_bgcolor='rgba(0, 0, 0, 0)',
                      xaxis_showgrid=False,
                      yaxis_showgrid=False,
                      xaxis_zeroline=False,
                      yaxis_zeroline=False)
    return fig


# Afficher l'évolution du prix au mètre carré
def plotly_ptz(df, dep):
    df2 = df[["an", "pm2", "commu"]].query("commu == "+ str(dep)).groupby("an").mean().reset_index()
    fig = px.line(df2, x="an", y="pm2")    
    fig.update_layout(title="Evolution du pm2 dans le " + str(dep) + " (data.gouv) :",
                      xaxis_title="Année",
                      yaxis_title="pm2",
                      ),
    fig.update_layout(template='plotly_dark',
                      plot_bgcolor='rgba(0, 0, 0, 0)',
                      paper_bgcolor='rgba(0, 0, 0, 0)',
                      xaxis_showgrid=False,
                      yaxis_showgrid=False,
                      xaxis_zeroline=False,
                      yaxis_zeroline=False)
    return fig

# Récupérer les nombres contenues dans une chaîne de caractère
def recuperer_chiffre_description(text):
    L = [int(s) for s in re.findall(r'-?\d+\.?\d*', text)]
    return L

#Récupère le prix
def recupere_nombre(text):
    A = [str(s) for s in re.findall(r'-?\d+\.?\d*', text)]

    if len(A) == 2:
        if A[1] == 0:
            nombre = int(A[0]+str('000'))
        else:
            nombre = int(A[0]+A[1])
    if len(A) == 3:
        if A[2] == 0:
            nombre = int(A[0]+A[1]+str('000'))
        else:
            nombre = int(A[0]+A[1]+A[2])
    if len(A) == 1:
        nombre = int(A[0].replace(".", "")+'00000')
    return nombre


client = pymongo.MongoClient("mongo")
database = client['Immobilier']
collection_direct = database['Direct']
collection_save = database['Save']

collection_save.delete_many({}) # a retirer après avoir exécuter une fois le programme

if len(list(collection_save.find())) == 0:

    with open('immo_1_49.json') as mf:
        data = json.load(mf)
    collection_save.insert_many(data)

    with open('immo_50_95.json') as mf:
        data2 = json.load(mf)
    collection_save.insert_many(data2)



print("_"*500)

#liste des User Agent
user_agent_list = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)  AppleWebKit/537.36   (KHTML, like Gecko) Chrome/83.0.4103.97  Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36   (KHTML, like Gecko) Chrome/83.0.4103.97  Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36   (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)  AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1       Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0)     Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
]

start = "https://www.seloger.com/immobilier/achat/immo-le-tech-66/bien-appartement/?projects=2&types=2%2C1&places=%5B%7B%22subDivisions%22%3A%5B%22"
end = "%22%5D%7D%5D&mandatorycommodities=0&enterprise=0&qsVersion=1.0&LISTING-LISTpg="

def scrap_immo(start, end, dep):
    scrap_immo = []
    dep = str(dep)
    
    if len(dep) == 1:
        dep = str(0)+dep
    
    for page in range(1,6):

        url = start+dep+end+str(page)
    
        response = requests.get(url, headers={'User-Agent': random.choice(user_agent_list)}, timeout = 50)
        soup = BeautifulSoup(response.text)

        for s in soup.find_all(class_="Card__ContentZone-sc-7insep-2 diTKck"):
            scraping={}

            prix = s.find_all(class_="Price__Label-sc-1g9fitq-2 jtuVxc")
            type_bien = s.find_all(class_= "ContentZone__Title-wghbmy-4 clOuRb")
            description = s.find_all(class_="ContentZone__TagsLine-wghbmy-6 fCXpjq")

            scraping['Departement'] = int(dep)

            for p in prix:
                scraping['Prix'] = recupere_nombre(p.text)

            for t_b in type_bien:
                scraping['Type du bien'] = t_b.text

            for d in description:
                D = recuperer_chiffre_description(d.text)
                if len(D) >= 3:
                    scraping['Pieces']=D[0]
                    scraping['Chambres']=D[1]
                    scraping['m2']=D[2]

            scrap_immo.append(scraping)
    return scrap_immo

#def choix_collec()
    


# ______________________________________




    
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.GRID, dbc.themes.DARKLY])

app.layout = html.Div([
    
    
    # Titre
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("Bourse et immobilier"),
            ],style={'textAlign': 'center'})
        ]),
    ],justify="center"),
    
    
    # Choix du Ticker
    dbc.Row([
        dcc.RadioItems(
            id="yf_choice",
            options=API_tickers,
            value='^FCHI',
        )
    ],justify="start"),
    
    
    # Courbes
    dbc.Row([
        
        # API
        dbc.Col([
            dcc.Dropdown(
                id="api_dropdown",
                options=API_col,
                placeholder="Select API value",
                style={"backgroundColor": "black", "color": "black"},
                value='Open',
                clearable=False,
            ),
            dcc.Graph(
                id="api_plot",
                figure={},
                config={'displayModeBar': False}
            ),
        ], width=6),
        
        
        # PM2
        dbc.Col([
            dcc.Input(id="ptz_input", 
                      type="number", 
                      min=1,
                      max=95,
                      placeholder="select department",
                      value=78,
                      style={"backgroundColor": "black", "color": "white"}),
            
            dcc.Graph(
                id="ptz_plot",
                figure={},
                config={'displayModeBar': False}
            ),
        ], width=6),
    ],justify="center"),




    # Courbes
    dbc.Row([
        

        
        # Pas à remplir
        dbc.Col([
            dbc.Card([
                    "Pour moi"

            ], style={'border-color':'green'})
            ], width=6),
        

        
        # _________________________
        # Tu mets ce que tu veux
        dbc.Col([

            dbc.Card([


            ], style={'border-color':'yellow'})

            
        ], width=6), # evite de toucher à cette taille
        # _________________________






    ],justify="center"),
    



    
])


# Choix des paramètres pour l'API
@app.callback(
    Output('api_plot', 'figure'),
    Input('api_dropdown', 'value'),
    Input('yf_choice', 'value'),
    
)

def yfinance(y, ticker):
    if ticker == "^GSPC":
        name = "S&P 500"
    else:
        name = "CAC 40"
    print(ticker)
    print("_"*100)
    return plotly_api(extract_api(ticker), y, name)


# Choix du département du ptz
@app.callback(
    Output('ptz_plot', 'figure'),
    Input('ptz_input', 'value'),
)

def ptz_choix(y):
    return plotly_ptz(ptz, y)

# server.run()