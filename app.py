from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'

# Configuration de la base de données
if os.environ.get('RENDER'):
    # On Render, database file is pre-created by startup script
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/seo_tracker.db'
else:
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
    data = request.get_json()
    
    if data.get('report_id'):
        # Mise à jour d'un rapport existant
        report = Report.query.get_or_404(data['report_id'])
        report.month = datetime.strptime(data['month'], '%Y-%m').date()
        report.actions_seo = data['actions_seo']
        if 'secretary_report' in data:
            report.secretary_report = data['secretary_report']
    else:
        # Création d'un nouveau rapport
        report = Report(
            client_id=data['client_id'],
            month=datetime.strptime(data['month'], '%Y-%m').date(),
            actions_seo=data['actions_seo'],
            secretary_report=data.get('secretary_report', '')
        )
        db.session.add(report)
    
    db.session.commit()
    return jsonify({'success': True})

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
