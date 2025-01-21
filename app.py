from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seo_tracker.db'
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
    # Supprimer et recréer toutes les tables
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Ajouter le template par défaut
        default_template = Template(content="""Bonjour,

Voici la synthèse des actions SEO réalisées ce mois-ci pour votre site :

[Actions réalisées]

Ces actions permettront d'améliorer votre visibilité sur les moteurs de recherche.

Cordialement,""")
        db.session.add(default_template)
        
        # Ajouter les clients initiaux
        clients = [
            Client(name='Méréo', email='guiard.pierre@gmail.com'),
            Client(name='Happy Kite Surf', email='benoitplanchon@gmail.com'),
            Client(name='Actimaine', email='contact@acti-maine.fr'),
            Client(name='DP Rénov', email='desbarrephillippe@gmail.com'),
            Client(name='Las Siette', email='safak.evin@las-siette.fr'),
            Client(name='Rennes Pneus', email='contact@rennespneus.fr'),
            Client(name='Vents et courbes', email='ventsetcourbes@gmail.com'),
            Client(name='COMIZI', email='ababel@comizi.fr'),
            Client(name='ECO Habitat', email='ecohabitat44.contact@gmail.com')
        ]
        
        for client in clients:
            db.session.add(client)
        
        db.session.commit()

@app.route('/')
def index():
    clients = Client.query.all()
    template = Template.query.first()
    return render_template('index.html', clients=clients, template=template)

@app.route('/add_client', methods=['POST'])
def add_client():
    name = request.form.get('name')
    email = request.form.get('email')
    
    if name and email:
        client = Client(name=name, email=email)
        db.session.add(client)
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/client/<int:client_id>')
def client_reports(client_id):
    client = Client.query.get_or_404(client_id)
    reports = Report.query.filter_by(client_id=client_id).order_by(Report.month.desc()).all()
    return render_template('client_reports.html', client=client, reports=reports)

@app.route('/save_report', methods=['POST'])
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
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    # Supprimer d'abord tous les rapports associés
    Report.query.filter_by(client_id=client_id).delete()
    db.session.delete(client)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
else:
    with app.app_context():
        db.create_all()
        if not Template.query.first():
            default_template = Template(content="""Bonjour,

Voici la synthèse des actions SEO réalisées ce mois-ci pour votre site :

[Actions réalisées]

Ces actions permettront d'améliorer votre visibilité sur les moteurs de recherche.

Cordialement,""")
            db.session.add(default_template)
            db.session.commit()
