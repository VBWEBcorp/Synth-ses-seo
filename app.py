from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-key-for-dev')

# Configuration du logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/seo-tracker.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SEO Tracker startup')

# Configuration de la base de données
if os.environ.get('RENDER'):
    # Sur Render, l'URL commence par postgres://, mais SQLAlchemy a besoin de postgresql://
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # En local, utiliser SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seo_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Identifiants d'authentification
USERNAME = "admin"
PASSWORD = "VBWEBcorp2024!"

# Fonction pour vérifier si l'utilisateur est connecté
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Identifiants invalides. Veuillez réessayer.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

db = SQLAlchemy(app)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    reports = db.relationship('Report', backref='client', lazy=True)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    actions_seo = db.Column(db.Text)
    secretary_report = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    with app.app_context():
        # Créer les tables si elles n'existent pas, sans supprimer les données existantes
        db.create_all()
        
        # Ajouter le template par défaut seulement s'il n'existe pas déjà
        if not Template.query.first():
            default_template = Template(content="""Bonjour,

Voici la synthèse des actions SEO réalisées ce mois-ci pour votre site :

[Actions réalisées]

Ces actions permettront d'améliorer votre visibilité sur les moteurs de recherche.

Cordialement,""")
            db.session.add(default_template)
            db.session.commit()

        # Ajouter les clients initiaux seulement s'il n'y a pas encore de clients
        if not Client.query.first():
            initial_clients = [
                Client(name="Méréo", email="guiard.pierre@gmail.com"),
                Client(name="Happy Kite Surf", email="benoitplanchon@gmail.com"),
                Client(name="Actimaine", email="contact@acti-maine.fr"),
                Client(name="DP Rénov", email="desbarrephillippe@gmail.com"),
                Client(name="Las Siette", email="safak.evin@las-siette.fr"),
                Client(name="Rennes Pneus", email="contact@rennespneus.fr"),
                Client(name="Vents et courbes", email="ventsetcourbes@gmail.com"),
                Client(name="COMIZI", email="ababel@comizi.fr"),
                Client(name="ECO Habitat", email="ecohabitat44.contact@gmail.com")
            ]
            
            for client in initial_clients:
                db.session.add(client)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error adding initial clients: {str(e)}")

@app.route('/')
@login_required
def index():
    clients = Client.query.all()
    template = Template.query.first()
    return render_template('index.html', clients=clients, template=template)

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        
        if not name or not email:
            app.logger.warning('Tentative d\'ajout de client avec des données manquantes')
            return jsonify({'error': 'Le nom et l\'email sont requis'}), 400
        
        existing_client = Client.query.filter_by(email=email).first()
        if existing_client:
            app.logger.warning(f'Tentative d\'ajout d\'un client avec un email déjà existant: {email}')
            return jsonify({'error': 'Un client avec cet email existe déjà'}), 400
        
        client = Client(name=name, email=email)
        db.session.add(client)
        db.session.commit()
        app.logger.info(f'Nouveau client ajouté avec succès: {name} ({email})')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de l\'ajout d\'un client: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de l\'ajout du client'}), 500

@app.route('/client/<int:client_id>')
@login_required
def client_reports(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        reports = Report.query.filter_by(client_id=client_id).order_by(Report.month.desc()).all()
        return render_template('client_reports.html', client=client, reports=reports)
    except Exception as e:
        app.logger.error(f'Erreur lors de l\'accès aux rapports du client {client_id}: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de l\'accès aux rapports'}), 500

@app.route('/save_report', methods=['POST'])
@login_required
def save_report():
    try:
        data = request.get_json()
        
        if not data:
            app.logger.warning('Tentative de sauvegarde de rapport sans données')
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
            
        if not data.get('month') or not data.get('actions_seo'):
            app.logger.warning('Tentative de sauvegarde de rapport avec des champs requis manquants')
            return jsonify({'success': False, 'error': 'Le mois et le rapport sont requis'}), 400

        if not data.get('client_id'):
            app.logger.warning('Tentative de sauvegarde de rapport sans ID client')
            return jsonify({'success': False, 'error': 'ID client manquant'}), 400

        try:
            month_date = datetime.strptime(data['month'], '%Y-%m').date()
        except ValueError as e:
            app.logger.warning(f'Format de date invalide: {data.get("month")}')
            return jsonify({'success': False, 'error': 'Format de date invalide'}), 400
        
        if data.get('report_id'):
            report = Report.query.get_or_404(data['report_id'])
            report.month = month_date
            report.actions_seo = data['actions_seo']
            if 'secretary_report' in data:
                report.secretary_report = data['secretary_report']
            app.logger.info(f'Rapport {report.id} mis à jour pour le client {report.client_id}')
        else:
            report = Report(
                client_id=data['client_id'],
                month=month_date,
                actions_seo=data['actions_seo'],
                secretary_report=data.get('secretary_report', '')
            )
            db.session.add(report)
            app.logger.info(f'Nouveau rapport créé pour le client {data["client_id"]}')
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de la sauvegarde du rapport: {str(e)}')
        return jsonify({'success': False, 'error': 'Une erreur est survenue lors de la sauvegarde'}), 500

@app.route('/save_template', methods=['POST'])
@login_required
def save_template():
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            app.logger.warning('Tentative de sauvegarde de template sans contenu')
            return jsonify({'error': 'Le contenu du template est requis'}), 400
            
        template = Template.query.first()
        if not template:
            template = Template(content=data['content'])
            db.session.add(template)
        else:
            template.content = data['content']
            
        db.session.commit()
        app.logger.info('Template mis à jour avec succès')
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de la sauvegarde du template: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de la sauvegarde du template'}), 500

@app.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        # Supprimer d'abord tous les rapports associés
        Report.query.filter_by(client_id=client_id).delete()
        db.session.delete(client)
        db.session.commit()
        app.logger.info(f'Client {client_id} supprimé avec succès')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de la suppression du client {client_id}: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de la suppression du client'}), 500

@app.route('/delete_report/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    try:
        report = Report.query.get_or_404(report_id)
        db.session.delete(report)
        db.session.commit()
        app.logger.info(f'Rapport {report_id} supprimé avec succès')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de la suppression du rapport {report_id}: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de la suppression du rapport'}), 500

@app.route('/init_clients', methods=['GET'])
@login_required
def init_clients():
    try:
        # Liste des clients à ajouter
        clients_to_add = [
            {"name": "Méréo", "email": "guiard.pierre@gmail.com"},
            {"name": "Happy Kite Surf", "email": "benoitplanchon@gmail.com"},
            {"name": "Actimaine", "email": "contact@acti-maine.fr"},
            {"name": "DP Rénov", "email": "desbarrephillippe@gmail.com"},
            {"name": "Las Siette", "email": "safak.evin@las-siette.fr"},
            {"name": "Rennes Pneus", "email": "contact@rennespneus.fr"},
            {"name": "Vents et courbes", "email": "ventsetcourbes@gmail.com"},
            {"name": "COMIZI", "email": "ababel@comizi.fr"},
            {"name": "ECO Habitat", "email": "ecohabitat44.contact@gmail.com"}
        ]

        # Ajouter chaque client s'il n'existe pas déjà
        added_count = 0
        for client_data in clients_to_add:
            existing_client = Client.query.filter_by(email=client_data["email"]).first()
            if not existing_client:
                client = Client(name=client_data["name"], email=client_data["email"])
                db.session.add(client)
                added_count += 1
                app.logger.info(f'Client ajouté: {client_data["name"]} ({client_data["email"]})')

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'{added_count} clients ont été ajoutés avec succès'
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erreur lors de l\'initialisation des clients: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Une erreur est survenue lors de l\'ajout des clients'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
else:
    try:
        with app.app_context():
            # Create database tables if they don't exist
            db.create_all()
            
            # Initialize default template if necessary
            template = Template.query.first()
            if not template:
                default_template = Template(content="""Bonjour,

Voici la synthèse des actions SEO réalisées ce mois-ci pour votre site :

[Actions réalisées]

Ces actions permettront d'améliorer votre visibilité sur les moteurs de recherche.

Cordialement,""")
                db.session.add(default_template)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"Error initializing default template: {str(e)}")
                    raise
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise
