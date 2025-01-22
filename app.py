from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'

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
                Client(name="Espace Coiffure Fabienne", email="espacecoiffurefabienne@gmail.com"),
                Client(name="Optique Saint Martin", email="contact@optiquesaintmartin.fr"),
                Client(name="Boulangerie Maison Martin", email="maisonmartin.boulangerie@gmail.com"),
                Client(name="Garage Renault Mantes", email="garage.renault.mantes@gmail.com"),
                Client(name="Pharmacie du Centre", email="pharmacieducentre78@gmail.com"),
                Client(name="Cabinet Dentaire Conflans", email="cabinetdentaireconflans@gmail.com"),
                Client(name="Le Bistrot du Port", email="lebistrotduport@gmail.com"),
                Client(name="Au Jardin de Laura", email="aujardindelaura@gmail.com"),
                Client(name="Immobilier Prestige", email="contact@immoprestige78.fr"),
                Client(name="Institut Beauté Marine", email="institut.beaute.marine@gmail.com"),
                Client(name="Agence Web", email="contact@vbwebcorp.fr"),
                Client(name="Plombier Mantes", email="plombier.mantes@gmail.com"),
                Client(name="Electricien Conflans", email="electricien.conflans@gmail.com")
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
    name = request.form.get('name')
    email = request.form.get('email')
    
    if name and email:
        client = Client(name=name, email=email)
        db.session.add(client)
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/client/<int:client_id>')
@login_required
def client_reports(client_id):
    client = Client.query.get_or_404(client_id)
    reports = Report.query.filter_by(client_id=client_id).order_by(Report.month.desc()).all()
    return render_template('client_reports.html', client=client, reports=reports)

@app.route('/save_report', methods=['POST'])
@login_required
def save_report():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
            
        if not data.get('month') or not data.get('actions_seo'):
            return jsonify({'success': False, 'error': 'Le mois et le rapport sont requis'}), 400

        if not data.get('client_id'):
            return jsonify({'success': False, 'error': 'ID client manquant'}), 400

        try:
            month_date = datetime.strptime(data['month'], '%Y-%m').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Format de date invalide'}), 400
        
        if data.get('report_id'):
            # Mise à jour d'un rapport existant
            report = Report.query.get_or_404(data['report_id'])
            report.month = month_date
            report.actions_seo = data['actions_seo']
            if 'secretary_report' in data:
                report.secretary_report = data['secretary_report']
        else:
            # Création d'un nouveau rapport
            report = Report(
                client_id=data['client_id'],
                month=month_date,
                actions_seo=data['actions_seo'],
                secretary_report=data.get('secretary_report', '')
            )
            db.session.add(report)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving report: {str(e)}")
        return jsonify({'success': False, 'error': 'Une erreur est survenue lors de la sauvegarde'}), 500

@app.route('/save_template', methods=['POST'])
@login_required
def save_template():
    data = request.get_json()
    template = Template.query.first()
    if template:
        template.content = data['content']
    else:
        template = Template(content=data['content'])
        db.session.add(template)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    # Supprimer d'abord tous les rapports associés
    Report.query.filter_by(client_id=client_id).delete()
    db.session.delete(client)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_report/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})

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
