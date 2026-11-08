from flask_login import UserMixin
from app import login_manager
from app.models.repository import get_db_connection

class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    # Recharge l'utilisateur à partir de l'ID stocké en session
    conn = get_db_connection()
    user = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM utilisateur WHERE ID_Utilisateur = %s", (user_id,))
            data = cursor.fetchone()
            if data:
                user = User(data['ID_Utilisateur'], data['Nom_Utilisateur'], data['Email'])
            cursor.close()
            conn.close()
        except:
            pass
    return user