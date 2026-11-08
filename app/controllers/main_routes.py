from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models import repository
from app.models.database import get_db_connection  
 
main_bp = Blueprint('main', __name__)
 
@main_bp.route('/')
def index():
    # Vérifie si la base de données répond
    conn = get_db_connection()
    if conn:
        status_text = "Connectée"
        status_color = "#27ae60" 
        conn.close() 
    else:
        status_text = "Base de données : Erreur "
        status_color = "#e74c3c" 
    return render_template('index.html', db_status=status_text, color=status_color)
 
@main_bp.route('/map')
def map_page():
    # Accès protégé : connexion requise
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    return render_template('map.html')
 
@main_bp.route('/charts')
def charts_page():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    return render_template('charts.html')
 
@main_bp.route('/favorites')
def favorites_page():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_id = session['user_id']
    try:
        # Récupère les favoris de l'utilisateur
        my_favorites = repository.get_user_dashboard(user_id)
    except: my_favorites = []
    return render_template('favorites.html', favorites=my_favorites)
 
@main_bp.route('/about')
def about_page():
    return render_template('about.html')

@main_bp.route('/reviews', methods=['GET', 'POST'])
def reviews_page():
    # Gestion de l'envoi d'avis
    if request.method == 'POST':
        if 'user_id' not in session:
            flash("Vous devez être connecté pour laisser un avis.", "danger")
            return redirect(url_for('auth.login'))

        note = request.form.get('note', type=int)
        message = request.form.get('message', '').strip()

        if note not in range(1, 6) or not message:
            flash("Choisissez une note de 1 à 5 et ajoutez un message.", "warning")
        elif repository.save_review(session['user_id'], note, message):
            repository.add_log("Avis", "avis", f"Avis enregistré ({note}/5)", session['user_id'])
            flash("Merci ! Votre avis a été enregistré.", "success")
        else:
            flash("Impossible d’enregistrer l’avis.", "danger")

        return redirect(url_for('main.reviews_page'))

    return render_template('reviews.html')

@main_bp.route('/admin/dashboard')
def admin_dashboard_page():
    # Sécurité : vérifie si l'utilisateur est Admin
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    if not repository.is_admin(session.get('user_id')):
        flash("Accès refusé. Réservé aux administrateurs.", "danger")
        return redirect(url_for('main.index'))

    # Récupération des logs, utilisateurs et avis pour le tableau de bord
    raw_logs = repository.get_admin_logs()
    formatted_logs = []
    for log in raw_logs:
        formatted_logs.append({
            'id': log.get('ID_Log'),
            'date': log.get('Date_Action'),
            'user': log.get('Nom_Utilisateur') or 'Inconnu',
            'action': log.get('Action'),
            'target': log.get('Table_Concernee'),
            'detail': log.get('Detail')
        })

    raw_users = repository.get_all_users()
    formatted_users = []
    for u in raw_users:
        is_admin_bool = (u.get('Role') in ['Admin', 'ADMIN'])
        formatted_users.append({
            'id': u.get('ID_Utilisateur'),
            'username': u.get('Nom_Utilisateur'),
            'email': u.get('Email'),
            'Role': u.get('Role'), 
            'is_admin': is_admin_bool
        })

    reviews_list = repository.get_all_reviews()

    return render_template('admin_dashboard.html', logs=formatted_logs, users=formatted_users, reviews=reviews_list)

@main_bp.route('/admin/manage_user', methods=['POST'])
def manage_user():
    # Création ou modification d'un utilisateur par l'admin
    if not repository.is_admin(session.get('user_id')):
        return redirect(url_for('main.index'))

    user_id = request.form.get('user_id') 
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') 

    role = 'Admin' if is_admin else 'User'

    if (not user_id or password) and len(password or '') < 8:
        flash("Utilisez un mot de passe d’au moins 8 caractères.", "warning")
        return redirect(url_for('main.admin_dashboard_page'))

    if repository.admin_save_user(user_id, username, email, role, password):
        action_type = "Modification" if user_id else "Création"
        repository.add_log(action_type, "utilisateur", f"Admin a géré l'user {username}", session['user_id'])
        flash(f"Utilisateur {action_type.lower()} effectuée avec succès.", "success")
    else:
        flash("Erreur lors de l'enregistrement.", "danger")

    return redirect(url_for('main.admin_dashboard_page'))

@main_bp.post('/admin/delete_user/<int:user_id>')
def delete_user_route(user_id):
    # Suppression d'un utilisateur
    if not repository.is_admin(session.get('user_id')):
        return redirect(url_for('main.index'))
    if user_id == session.get('user_id'):
        flash("Impossible de supprimer son propre compte.", "warning")
        return redirect(url_for('main.admin_dashboard_page'))

    if repository.delete_user(user_id):
        repository.add_log("Suppression", "utilisateur", f"Admin a supprimé l'ID {user_id}", session['user_id'])
        flash("Utilisateur supprimé.", "success")
    else:
        flash("Erreur lors de la suppression.", "danger")
        
    return redirect(url_for('main.admin_dashboard_page'))
