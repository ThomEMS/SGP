# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, abort
from functools import wraps
from database import init_db, ajouter_depense, get_resume, add_user, verify_user
import os

app = Flask(__name__)
# IMPORTANT: définit une clé secrète forte (utilise variable d'env en prod)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-moi-pour-prod-1234567890")

# init DB (création des tables si nécessaire)
init_db()

# --- Décorateur pour protéger routes ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            # redirige vers login en gardant la route voulue
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

# --- Routes d'auth ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = verify_user(username, password)
        if user:
            session["user"] = {"id": user["id"], "username": user["username"], "fullname": user["fullname"]}
            session.permanent = True
            next_url = request.args.get("next") or url_for("index")
            flash("Connecté", "success")
            return redirect(next_url)
        else:
            flash("Nom d'utilisateur ou mot de passe invalide", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Déconnecté", "info")
    return redirect(url_for("login"))

# --- Page d'accueil et ajout protégés ---
@app.route('/')
def index():
    resume = get_resume()
    categories = [r[0] for r in resume]
    montants = [r[2] for r in resume]
    return render_template('index.html', resume=resume, categories=categories, montants=montants, user=session.get("user"))

@app.route('/ajout', methods=['GET', 'POST'])
@login_required
def ajout():
    if request.method == 'POST':
        montant = float(request.form['montant'])
        categorie = request.form['categorie']
        description = request.form['description']
        type_depense = request.form['type_depense']
        part_thomas = float(request.form.get('part_thomas', montant))
        part_autre = float(request.form.get('part_autre', 0))
        nom_autre = request.form.get('nom_autre', '')
        ajouter_depense(montant, categorie, description, type_depense, part_thomas, part_autre, nom_autre)
        return redirect(url_for('index'))
    return render_template('ajout.html', user=session.get("user"))

# API protégée par login (ex: pour app mobile)
@app.route('/api/depenses')
@login_required
def api_depenses():
    return jsonify(get_resume())

if __name__ == '__main__':
    # en dev, debug True ; en prod, utiliser systemd + reverse proxy + HTTPS
    app.run(host='0.0.0.0', port=5000, debug=True)
