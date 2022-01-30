# Bourse-et-Immobilier-Mongo-Flask-
Travail de découverte sur mongo et affichage grâce à Flask

Une image du projet fonctionnel se trouve dans le Dossier du projet: ***6 Evaluation/Projet/Overview.png***

*Le contexte :*

Le projet ici présenté à pour but de mettre en parallèle les indicateurs de la bourse comme le CAC40 ou le S&P500 avec l'évolution du prix au mètre carré en France dans chaque département. 

Ainsi, via l'application web finale, on peut voir si la bourse est dans une phase où investir est stratégique.


### User Guide
1) Cloner tout le projet à partir du GIT.
`git clone https://github.com/AriaBatut/DataEngineerTools`

2) Ouvrir un terminal, avec Docker installé et se mettre dans le dossier du projet qui vient d'être téléchargé DataEngineerTools\6Evaluation\Projet. Ouvrir Docker pour qu'il tourne en rrière plan puis il reste à lancer le projet en executahnt la commande suivant dans le terminal:
`docker-compose up`

3) Une fois tous les téléchargements effectués, il ne reste plus qu'à ouvrir un navigateur et aller à la page [localhost:5001](http://localhost:5001/)


### Developper Guide
Le fichier principal est intitulé **app.py**.

Dans celui-ci on importe les librairies utiles pour la création du projet.

Les principales parties sont ainsi :
1) La création d'une base de données non relationnelle avec MongoDB. On remplit celle-ci avec *BeautifulSoup4* qui scrape un site immobilier qui possède des annonces partout en France. La sauvegarde de nos annonces se trouve dans des *.json* pour un déploiement rapide.

2) La deuxième partie du projet permet de scraper les annonces en direct. Ainsi, l'utilisateur peut voir les dernières annonces postées. L'avantage de la sauvegarde de la partie 1 permet d'avoir des données si le site ne marche plus...

3) Ensuite, on s'interesse aux indicateurs boursiers. L'API utilisée est celle de Yahoo Finance (on ne choisit pas *yfinance* dans ce travail). La librairie *yahoo_fin* permet donc de prendre l'historique des données que l'on veut et permet aussi d'avoir un suivi sur une période choisie.

4) On crée une partie pour se donner une idée générale de l'évolution de toute la bourse. Et, en dessous, on a l'évolution des 5 derniers jours pour voir les dernières tendances. On y applique quelques modèles pour voir les évolutions avec *statsmodels*.

5) En parallèle, on récupère les données présentes sur data.gouv.fr pour afficher l'évolution du prix au mètre carré en France. Avec une régression linéaire, on peut voir la tendance à venir jusqu'en 2023.

6) Avec le scraping en temps réel, on calcule le prix au mètre carré moyen dans le département que l'on peut comparer avec la régression ci-dessus.

7) Les tableaux affichent des requêtes mongo pour aider l'utilisateur à avoir un meilleur recul sur les annonces en cours.

8) En fonction de ces différents points, il est plus ou moins stratégique d'investir à un instant t.


#### Docker

Le *docker-compose.yml* et le *Dockerfile* permettent de lancer une version du projet qui marche correctement. 
Le projet qui possède tout pour les installations, permet de lancer l'*app.py* automatiquement et la base de données MongoDB.

Néanmoins, on ne peut garantir la survie de ce projet dans le temps:
- l'API peut changer de format ce qui impliquerait des erreurs.
- le site peut ne plus accepter le scraping ou tout simplement être programmé autrement (classes qui changent par exmeple).

Dans l'état du projet actuel, un effort est fait pour permettre de tourner le projet malgré ces erreurs avec une sauvegarde des anciennes annonces scrapées qui se lancent si le site n'accepte plus le scraping. La version de l'API choisie permet également d'apporter des base de données les plus simples, qui vont potentiellement ne pas évoluées dans le format.


.....

###### Fin du README
