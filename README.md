# SEO Tracker

Une application web simple et collaborative pour gérer le suivi SEO mensuel de vos clients.

## Fonctionnalités

- Gestion des clients (ajout, visualisation)
- Création de rapports SEO mensuels
- Interface collaborative entre le consultant SEO et l'assistante
- Historique des données pour chaque client
- Interface moderne et responsive

## Installation

1. Cloner le repository
2. Créer un environnement virtuel Python :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Lancer l'application :
```bash
python app.py
```

L'application sera accessible à l'adresse : http://localhost:5000

## Structure du projet

- `app.py` : Application principale Flask
- `templates/` : Templates HTML
- `static/` : Fichiers statiques (CSS, JS)
- `instance/` : Base de données SQLite (créée automatiquement)

## Technologies utilisées

- Backend : Python/Flask
- Base de données : SQLite
- Frontend : HTML5, CSS3 (Bootstrap 5), JavaScript
- Persistance des données : Flask-SQLAlchemy
