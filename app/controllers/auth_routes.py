from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import repository
 
auth_bp = Blueprint('auth', __name__)
 
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Traite le formulaire de connexion
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        user = repository.get_user_by_credentials(email, password)
        
        # Si l'utilisateur existe, on démarre la session
        if user:
            session.clear()
            session['user_id'] = user['ID_Utilisateur']
            session['username'] = user['Nom_Utilisateur']
            session['role'] = user['Role'] 
            repository.add_log("Connexion", "utilisateur", "Authentification réussie", user['ID_Utilisateur'])
            return redirect(url_for('main.index'))
        else:
            flash("Email ou mot de passe incorrect.", "danger")
    # Affiche la page de connexion
    return render_template('login.html')
 
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Traite la création de compte
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or len(username) > 80 or not email or len(email) > 254 or len(password) < 8:
            flash("Renseignez votre nom, votre adresse e-mail et un mot de passe de 8 caractères minimum.", "danger")
        elif repository.create_user(username, email, password):
            flash("Compte créé ! Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Erreur : Cet email est déjà utilisé.", "danger")
 
    return render_template('register.html')
 
@auth_bp.post('/logout')
def logout():
    # Vide la session et déconnecte l'utilisateur
    if 'user_id' in session:
        repository.add_log("Déconnexion", "utilisateur", "Fin de session", session['user_id'])
        session.clear()
        flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('auth.login'))
