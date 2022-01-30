# ____________________________________________________________________________
# Les librairies


from flask import Flask

import os, wget

import pandas as pd
from yahoo_fin.stock_info import get_data

from datetime import datetime, timedelta

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly
import plotly.express as px
import ipywidgets
import plotly.graph_objects as go

import pymongo
from bs4 import BeautifulSoup
import requests
import re
import random
import json

from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import numpy as np
# ____________________________________________________________________________



# ____________________________________________________________________________
# Création de la base de données mongo

client = pymongo.MongoClient("mongo")
database = client['Immobilier']
collection_direct = database['Direct']
collection_save = database['Save']
# collection_save.delete_many({}) # si besoin de recommencer pour mettre de nouvelles annonces
# ____________________________________________________________________________




# ____________________________________________________________________________
# Extraction de la base de données sur data.gouv.fr
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

# ____________________________________________________________________________



# ____________________________________________________________________________
# Liste des colonnes de l'API qui existent 
API_col = [{'label': 'Open', 'value': 'Open'},
           {'label': 'High', 'value': 'High'},
           {'label': 'Low', 'value': 'Low'},
           {'label': 'Close', 'value': 'Close'},
           {'label': 'Volume', 'value': 'Volume'},
          ]

# Liste des tickers que l'on peut utiliser
API_tickers = [{'label': 'CAC 40', 'value': '^FCHI'},
               {'label': 'S&P 500', 'value': '^GSPC'},
              ]
# ____________________________________________________________________________



# ____________________________________________________________________________
#Fonctions pour extraire la bourse en direct des 5 derniers jours
def extract_api_5d(ticker):
    mtn = datetime.now()
    
    start = mtn - timedelta(days = 5)
    temp = get_data(ticker, start_date  = start, interval="1m").reset_index().drop(["ticker"], axis=1).rename(columns={"open": "Open",
                                                "high": "High",
                                                "low": "Low",
                                                "close": "Close",
                                                "volume": "Volume",
                                                "index": "Date",
                                               })
    return temp

# Extraire les données en direct de l'API
def extract_api(ticker):
    return get_data(ticker, interval="1d").reset_index().drop(["ticker"], axis=1).rename(columns={"open": "Open",
                                                "high": "High",
                                                "low": "Low",
                                                "close": "Close",
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
    df2 = df.dropna()
    df2 = df[["an", "pm2", "commu"]].query("commu == "+ str(dep)).groupby("an").mean().reset_index()
    fig = px.line(df2, x="an", y="pm2")
    
    
    X = df2["an"].values.reshape(-1, 1)
    x_range = np.linspace(X.min(), X.max() + 3, 100).reshape(-1, 1)
    
    degree = 1
    poly = PolynomialFeatures(degree)
    poly.fit(X)
    X_poly = poly.transform(X)
    x_range_poly = poly.transform(x_range)
    
    
    model = LinearRegression(fit_intercept=False)
    
    model.fit(X_poly, df2["pm2"])
    
    y_poly = model.predict(x_range_poly)
    
    fig.add_traces(
            go.Scatter(
                x=x_range.squeeze(),
                y=y_poly,
                showlegend=True,
                name="Régression linéaire degré 1 (jusqu'en 2023)"
            )
        )
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

# Affichage de la bourse sous 5 jours
def plotly_api_trend(df, y, name, modele):
    if modele == "rolling":
        fig = px.scatter(
            df, x='Date', y=y, opacity=0.65,
            trendline='rolling', trendline_options=dict(window=5), trendline_color_override='darkviolet')
    elif modele == "lowess":
        fig = px.scatter(
            df, x='Date', y=y, opacity=0.65,
            trendline='lowess', trendline_options=dict(frac=0.1), trendline_color_override='darkviolet')
    else :
        fig = px.scatter(
            df, x='Date', y=y, opacity=0.65,
            trendline='ols', trendline_color_override='darkviolet')
        
    
    fig.update_layout(title="Tendance des 5 deniers jours sur le " + name +" (API en direct) :",
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

# Afficher le tableau pour le département selectionné des différents types de bien proposées
# avec le nombre d'annonces pour chaque type ainsi que la moyenne de prix
def table_type_moyen(data, y, var):

    if var == 0:
        fig = go.Figure(
            data=[go.Table(
                    header=dict(values=['Departement', 'Prix', 'Type du bien', 'Pieces', 'Chambres', 'm2']),
                    cells=dict(values = 
                                [[i.get("Departement") for i in data], 
                                [i.get("Prix") for i in data],
                                [i.get("Type du bien") for i in data],[i.get("Pieces") for i in data],
                                [i.get("Chambres") for i in data],[i.get("m2") for i in data]] )
                    ),           
                ])
        title_ici = "Liste de toutes les annonces scrapées dans le " + str(y) + " :"
    
    elif var == 1:
        fig = go.Figure(
            data=[go.Table(
                        header=dict(values=['Type du bien', "Nombre d'annonces", 'Prix moyen']),
                        cells=dict(values = [[i.get("_id") for i in data],
                                        [i.get("Nombre d'annonces") for i in data],
                                        [round(i.get("Prix moyen")) for i in data]]))
                        ])
        title_ici = "Tri du scraping par type du bien dans le " + str(y) + " :"

    elif var == 2:
        fig = go.Figure(data=[go.Table(header=dict(values=['Departement', "Nombre d'annonces", 'Moyenne Prix', 'Moyenne Surface', 'Moyenne Pièces', 'Moyenne Chambres']),
                        cells=dict(values = [[round(i.get("_id")) for i in data], 
                                            [round(i.get("Number")) for i in data],
                                            [round(i.get("AveragePrice")) for i in data],
                                            [round(i.get("AverageSurface")) for i in data],
                                            [round(i.get("AveragePiece")) for i in data],
                                            [round(i.get("AverageRoom")) for i in data]]))
                            ])
        title_ici = "Résumé des annonces pour chaque département :"

    fig.update_layout(title=title_ici),
    fig.update_layout(template='plotly_dark',
                      paper_bgcolor='rgba(0, 0, 0, 0)')
    return fig
# ____________________________________________________________________________



# ____________________________________________________________________________
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

#liste des User Agent
user_agent_list = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)  AppleWebKit/537.36   (KHTML, like Gecko) Chrome/83.0.4103.97  Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36   (KHTML, like Gecko) Chrome/83.0.4103.97  Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36   (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)  AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1       Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0)     Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
]



# On remplit une collection
if len(list(collection_save.find())) == 0:
    with open('immo_1_49.json') as mf:
        data = json.load(mf)
    collection_save.insert_many(data)

    with open('immo_50_95.json') as mf:
        data2 = json.load(mf)
    collection_save.insert_many(data2)

# Scraping en direct
def scrap_immo(dep, page=6):
    start = "https://www.seloger.com/immobilier/achat/immo-le-tech-66/bien-appartement/?projects=2&types=2%2C1&places=%5B%7B%22subDivisions%22%3A%5B%22"
    end = "%22%5D%7D%5D&mandatorycommodities=0&enterprise=0&qsVersion=1.0&LISTING-LISTpg="
    scrap_immo = []
    dep = str(dep)
    
    if len(dep) == 1:
        dep = str(0)+dep
    
    for page in range(1, page):

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
    if len(scrap_immo)==0:
        return list(collection_save.find({"Departement":int(dep)}))
    else :
        return scrap_immo
# ____________________________________________________________________________



# ____________________________________________________________________________
# Script pour créer les fichiers immo.json

# scrap_immo=[]

# start = "https://www.seloger.com/immobilier/achat/immo-le-tech-66/bien-appartement/?projects=2&types=2%2C1&places=%5B%7B%22subDivisions%22%3A%5B%22"
# end = "%22%5D%7D%5D&mandatorycommodities=0&enterprise=0&qsVersion=1.0&LISTING-LISTpg="

# compteur = 0

# for i in range(1,96):
#     dep = str(i)
    
#     if len(dep) == 1:
#         dep = str(0)+dep
    
#     for j in range(1,6):
#         page = j
        
#         url = start+dep+end+str(page)
    
#         response = requests.get(url, headers={'User-Agent': user_agent_list[0]}, timeout = 50)
#         print(response)
#         soup = BeautifulSoup(response.text)

#         for s in soup.find_all(class_="Card__ContentZone-sc-7insep-2 diTKck"):
#             scraping={}

#             prix = s.find_all(class_="Price__Label-sc-1g9fitq-2 jtuVxc")
#             type_bien = s.find_all(class_= "ContentZone__Title-wghbmy-4 clOuRb")
#             description = s.find_all(class_="ContentZone__TagsLine-wghbmy-6 fCXpjq")

#             scraping['Departement'] = int(dep)

#             for p in prix:
                
#                 scraping['Prix'] = recupere_nombre(p.text)

#             for t_b in type_bien:
#                 scraping['Type du bien'] = t_b.text

#             for d in description:
#                 D = recuperer_chiffre_description(d.text)
#                 if len(D) == 3:
#                     scraping['Pieces']=D[0]
#                     scraping['Chambres']=D[1]
#                     scraping['m2']=D[2]

#             scrap_immo.append(scraping)
#             print(compteur, dep, page)
#             compteur += 1
# ____________________________________________________________________________



# ____________________________________________________________________________
# ____________________________________________________________________________
# ____________________________________________________________________________



# ____________________________________________________________________________
# Début de l'application
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
    
    # Sous-itre
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H2("Faut'il investir dans l'immobilier en prenant en compte le cours de la bourse ?", style={'color': 'darkviolet'}),
            ],style={'textAlign': 'center'})
        ]),
    ],justify="center"),
    
    dbc.Row([
            dbc.Col([
                    html.H6("Prix du mètre carré actuel dans le département choisi :"),
                    html.H2(id='pm2_mean', style={'color': '#7FDBFF'})
            ], width=4),
    ],justify="end"),

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
            dbc.Card([
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
            ], style={'border-color':'darkviolet'})
        ], width=6),
    ],justify="center"),




    # Courbes
    dbc.Row([
        

        
        # Pas à remplir
        dbc.Col([
            dbc.Card([
                # Choix du modele
                dbc.Row([
                    dcc.RadioItems(
                        id="modele_choice",
                        options=[   {'label': 'rolling', 'value': "rolling"},
                                    {'label': 'lowess', 'value': 'lowess'},
                                    {'label': 'ols', 'value': 'ols'},
                                    ],
                        value='rolling',
                    )
                ],justify="start"),
                dcc.Graph(
                    id="plt_5d",
                    figure={},
                    config={'displayModeBar': False}
                ),

            ], style={'border-color':'darkviolet'})
        ], width=6),
        

        
        # _________________________
        # Tu mets ce que tu veux
        dbc.Col([
                dbc.Row([
                    dcc.RadioItems(
                        id="table_choice",
                        options=[   {'label': 'Toutes les anonces', 'value': "0"},
                                    {'label': 'Tri par type de bien', 'value': '1'},
                                    {'label': 'Résumé par département', 'value': '2'},
                                    ],
                        value='0',
                    )
                ],justify="start"),
                dcc.Graph(
                    id="table_a",
                    figure={},
                    config={'displayModeBar': False}
                ),
            
            
        ], width=6), # evite de toucher à cette taille
        # _________________________

    ],justify="center"),
])


# Choix des paramètres pour l'API
@app.callback(
    Output('api_plot', 'figure'),
    Output('plt_5d', 'figure'),
    Input('api_dropdown', 'value'),
    Input('yf_choice', 'value'),
    Input('modele_choice', 'value'),
    
    
)

def yfinance(y, ticker, modele):
    if ticker == "^GSPC":
        name = "S&P 500"
    else:
        name = "CAC 40"
    return plotly_api(extract_api(ticker), y, name), plotly_api_trend(extract_api_5d(ticker), y, name, modele)


# Choix du département du ptz
@app.callback(
    Output('ptz_plot', 'figure'),
    Output('table_a', 'figure'),
    # Output('my-output', 'children'),    
    Output('pm2_mean', 'children'),
    Input('ptz_input', 'value'),
    Input('table_choice', 'value'),
)

def ptz_choix(y, var):
    data = scrap_immo(y, 1)
    collection_direct.delete_many({})
    collection_direct.insert_many(data)

    result1 = collection_direct.aggregate([
        {"$group" : {
            "_id" : "$Type du bien",
            "Nombre d'annonces" : {"$sum" : 1},
            "Prix moyen" : {"$avg" : "$Prix"}}}, 
        { "$sort" : { "Number" : -1} }
    ])
    cursor_7 = collection_direct.aggregate(
                                            [{ "$project": { 
                                                    "_id": "$Departement",

                                                    "result":{"$divide": [ "$Prix", "$m2" ]}
                                                    } 
                                                }]
                                            )

    cursor_8 = collection_save.aggregate([{"$group" : {"_id" : "$Departement","Number" : {"$sum" : 1},
                                              "AveragePrice" : {"$avg" : "$Prix"},
                                              "AverageSurface" : {"$avg" : "$m2"},
                                             "AveragePiece" : {"$avg" : "$Pieces"},
                                              "AverageRoom" : {"$avg" : "$Chambres"}}},
                                { "$sort" : { "_id" : 1} }])

    pm2_tot = 0
    taille = 0
    for mee in [i.get("result") for i in list(cursor_7)]:

        if mee != None and mee <=20000:
            pm2_tot+=mee
            taille+=1
    pm2_aff = round(pm2_tot/taille )
    var2 = int (var)

    if var2 == 0:
        table_r = table_type_moyen(list(collection_direct.find()), y, 0)
    elif var2 == 1 :
        table_r = table_type_moyen(list(result1), y, 1)
    elif var2 == 2 :
        table_r = table_type_moyen(list(cursor_8), None, 2)

    return plotly_ptz(ptz, y), table_r, str(pm2_aff)+" €/m²"
# ____________________________________________________________________________

# server.run()
