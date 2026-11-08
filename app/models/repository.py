import mysql.connector
import time
from functools import lru_cache
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.database import get_db_connection

def execute_query_with_time(query, params=None, fetch_all=True):
    # Exécute une requête et mesure le temps pris
    start_time = time.time()
    conn = get_db_connection()
    result = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall() if fetch_all else cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception:
            return [], 0
    end_time = time.time()
    return result, round((end_time - start_time) * 1000, 2)

@lru_cache(maxsize=10)
def find_variable_id(user_search_name):
    # Trouve l'ID de la variable selon le texte (SST, SSS, etc.)
    term = user_search_name.lower()
    if "temp" in term or "sst" in term: term = "sst"
    elif "sal" in term or "sss" in term: term = "sss"
    elif "chl" in term: term = "chl"

    query = "SELECT ID_Variable, Indicateurs FROM variable"
    all_vars, _ = execute_query_with_time(query)
    
    for v in all_vars:
        if term in v['Indicateurs'].lower():
            return v['ID_Variable']
    return None

@lru_cache(maxsize=32)
def fetch_weekly_data(start, end, ind_name):
    # Récupère les données hebdo (avec cache pour la performance)
    target_id = find_variable_id(ind_name)
    if not target_id: return [], 0
    
    query = """
        SELECT m.Jour_Opti as Date_Semaine, AVG(m.Valeur) as Moyenne
        FROM mesure m
        WHERE m.ID_Variable = %s 
          AND m.Jour_Opti BETWEEN %s AND %s
          AND m.ID_Mesure % 50 = 0
        GROUP BY m.Jour_Opti
        ORDER BY m.Jour_Opti ASC
        LIMIT 5000
    """
    raw_data, duration = execute_query_with_time(query, (target_id, start, end))
    
    clean_data = []
    for row in raw_data:
        try:
            clean_data.append({
                'Date_Semaine': str(row['Date_Semaine']),
                'Moyenne': float(row['Moyenne']) if row['Moyenne'] is not None else 0.0
            })
        except: continue
    return clean_data, duration

@lru_cache(maxsize=32)
def fetch_correlation_data(start, end, ind1_name, ind2_name):
    # Compare deux indicateurs pour la corrélation
    id1 = find_variable_id(ind1_name)
    id2 = find_variable_id(ind2_name)
    if not id1 or not id2: return [], 0

    start_total = time.time()
    
    query = """
        SELECT Jour_Opti as jour, AVG(Valeur) as moyenne
        FROM mesure
        WHERE ID_Variable = %s 
          AND Jour_Opti BETWEEN %s AND %s
          AND ID_Mesure % 50 = 0
        GROUP BY Jour_Opti
        ORDER BY jour ASC
    """
    
    data1, t1 = execute_query_with_time(query, (id1, start, end))
    data2, t2 = execute_query_with_time(query, (id2, start, end))

    dict1 = {str(row['jour']): float(row['moyenne']) for row in data1 if row['moyenne'] is not None}
    final_result = []
    
    for row in data2:
        jour = str(row['jour'])
        if jour in dict1 and row['moyenne'] is not None:
            final_result.append({
                'date': jour,
                'val1': dict1[jour],
                'val2': float(row['moyenne'])
            })

    return final_result, round((time.time() - start_total) * 1000, 2)

@lru_cache(maxsize=32)
def fetch_distribution_data(start, end, ind_name):
    target_id = find_variable_id(ind_name)
    if not target_id: return [], 0
    
    query = """
        SELECT Valeur FROM mesure
        WHERE ID_Variable = %s 
          AND Jour_Opti BETWEEN %s AND %s
          AND ID_Mesure % 100 = 0
        LIMIT 5000
    """
    raw_data, duration = execute_query_with_time(query, (target_id, start, end))
    
    return [float(row['Valeur']) for row in raw_data if row['Valeur'] is not None], duration

def add_log(action, table_name, detail, user_id):
    # Enregistre une action dans l'historique
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            sql = "INSERT INTO historique (Action, Table_Concernee, Detail, ID_Utilisateur, Date_Action) VALUES (%s, %s, %s, %s, NOW())"
            cursor.execute(sql, (action, table_name, detail, user_id))
            conn.commit()
            cursor.close()
            conn.close()
        except: pass

def get_admin_logs():
    # Récupère les logs pour l'admin
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT h.ID_Log, h.Action, h.Table_Concernee, h.Detail, h.Date_Action, u.Nom_Utilisateur 
            FROM historique h 
            LEFT JOIN utilisateur u ON h.ID_Utilisateur = u.ID_Utilisateur 
            ORDER BY h.Date_Action DESC LIMIT 50
        """
        cursor.execute(query)
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return logs
    except: return []

def is_admin(user_id):
    if not user_id:
        return False
    user, _ = execute_query_with_time(
        'SELECT Role FROM utilisateur WHERE ID_Utilisateur = %s', (user_id,), fetch_all=False
    )
    return bool(user and user['Role'].lower() == 'admin')


def get_all_users():
    conn = get_db_connection()
    users = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ID_Utilisateur, Nom_Utilisateur, Email, Role FROM utilisateur ORDER BY ID_Utilisateur DESC")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
        except: pass
    return users

def admin_save_user(user_id, username, email, role, password=None):
    # Admin : Crée ou met à jour un utilisateur
    if not user_id and not password:
        return False
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            if user_id: 
                if password: 
                    sql = "UPDATE utilisateur SET Nom_Utilisateur=%s, Email=%s, Role=%s, Mot_de_Passe=%s WHERE ID_Utilisateur=%s"
                    cursor.execute(sql, (username, email, role, generate_password_hash(password), user_id))
                else: 
                    sql = "UPDATE utilisateur SET Nom_Utilisateur=%s, Email=%s, Role=%s WHERE ID_Utilisateur=%s"
                    cursor.execute(sql, (username, email, role, user_id))
            else: 
                pwd = generate_password_hash(password)
                sql = "INSERT INTO utilisateur (Nom_Utilisateur, Email, Role, Mot_de_Passe) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (username, email, role, pwd))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except: pass
    return False

def delete_user(user_id):
    # Supprime un utilisateur et ses données liées
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favoris_perso WHERE ID_Utilisateur = %s", (user_id,))
            cursor.execute("DELETE FROM historique WHERE ID_Utilisateur = %s", (user_id,))
            cursor.execute("DELETE FROM utilisateur WHERE ID_Utilisateur = %s", (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except: pass
    return False

def get_user_by_credentials(email, password):
    conn = get_db_connection()
    user = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM utilisateur WHERE Email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
        except: pass
    if user and check_password_hash(user.pop("Mot_de_Passe"), password):
        return user
    return None

def create_user(username, email, password):
    conn = get_db_connection()
    success = False
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO utilisateur (Nom_Utilisateur, Email, Mot_de_Passe, Role) VALUES (%s, %s, %s, 'User')", (username, email, generate_password_hash(password)))
            conn.commit()
            success = True
            cursor.close()
            conn.close()
        except: pass
    return success

def add_favorite_safe(user_id, zone, indicator, start_date, end_date):
    # Ajoute un favori en évitant les doublons
    conn = get_db_connection()
    status = "error"
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ID_Favori FROM favoris_perso 
                   WHERE ID_Utilisateur = %s 
                   AND Nom_Zone = %s 
                   AND Indicateur = %s 
                   AND Date_Debut = %s 
                   AND Date_Fin = %s""", 
                (user_id, zone, indicator, start_date, end_date)
            )
            existing = cursor.fetchone()
            if existing:
                status = "exists"
            else:
                cursor.execute(
                    "INSERT INTO favoris_perso (ID_Utilisateur, Nom_Zone, Indicateur, Date_Debut, Date_Fin) VALUES (%s, %s, %s, %s, %s)", 
                    (user_id, zone, indicator, start_date, end_date)
                )
                conn.commit()
                status = "added"
                add_log("Favoris", "favoris_perso", f"Ajout favori: {zone}-{indicator}", user_id)
            cursor.close()
            conn.close()
        except Exception:
            pass
    return status

def delete_favorite_by_id(fav_id, user_id):
    conn = get_db_connection()
    success = False
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Nom_Zone, Indicateur FROM favoris_perso WHERE ID_Favori = %s", (fav_id,))
            fav_info = cursor.fetchone()
            detail_log = f"Suppression ID {fav_id}"
            if fav_info:
                detail_log = f"Suppression favori: {fav_info[0]}-{fav_info[1]}"
            cursor.execute("DELETE FROM favoris_perso WHERE ID_Favori = %s AND ID_Utilisateur = %s", (fav_id, user_id))
            if cursor.rowcount > 0:
                conn.commit()
                success = True
                add_log("Favoris", "favoris_perso", detail_log, user_id)
            cursor.close()
            conn.close()
        except Exception:
            pass
    return success

def get_user_dashboard(user_id):
    # Récupère la liste des favoris d'un user
    data = []
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ID_Favori, Nom_Zone, Indicateur, 
                       DATE_FORMAT(Date_Debut, '%d/%m/%Y') as Start,
                       DATE_FORMAT(Date_Fin, '%d/%m/%Y') as End,
                       DATE_FORMAT(Date_Debut, '%Y-%m-%d') as Start_SQL,
                       DATE_FORMAT(Date_Fin, '%Y-%m-%d') as End_SQL
                FROM favoris_perso 
                WHERE ID_Utilisateur = %s
                ORDER BY ID_Favori DESC
            """
            cursor.execute(query, (user_id,))
            data = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception:
            pass
    return data

def save_review(user_id, note, message):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO avis (ID_Utilisateur, Note, Message, Date_Avis) VALUES (%s, %s, %s, NOW())", (user_id, note, message))
            conn.commit()
            conn.close()
            return True
        except: return False
    return False

def get_all_reviews():
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT a.*, u.Nom_Utilisateur 
            FROM avis a 
            LEFT JOIN utilisateur u ON a.ID_Utilisateur = u.ID_Utilisateur 
            ORDER BY a.Date_Avis DESC
        """
        cursor.execute(sql)
        reviews = cursor.fetchall()
        cursor.close()
        conn.close()
        return reviews
    except: return []

def get_map_data_local(start_str, end_str, ind_name, zone_bbox):
    # Récupère les points pour la carte selon la zone et la date
    conn = get_db_connection()
    if not conn: return []

    var_id = find_variable_id(ind_name)
    if not var_id: return []

    # Définit les bornes min/max pour la coloration
    if "Temp" in ind_name or "SST" in ind_name:
        min_val, max_val = -2.0, 30.0
    elif "Sal" in ind_name or "SSS" in ind_name:
        min_val, max_val = 10.0, 40.0
    elif "Chl" in ind_name:
        min_val, max_val = 0.0, 5.0
    else:
        min_val, max_val = 0.0, 100.0
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = f"""
            SELECT 
                loc.Latitude as lat, 
                loc.Longitude as lon, 
                m.Valeur as valeur 
            FROM mesure m
            INNER JOIN localisation loc ON m.ID_Localisation = loc.ID_Localisation
            WHERE m.ID_Variable = %s 
              AND m.Jour_Opti >= %s 
              AND m.Jour_Opti <= %s
              AND loc.Latitude BETWEEN %s AND %s
              AND loc.Longitude BETWEEN %s AND %s
              AND m.ID_Mesure % 100 = 0 
            LIMIT 500000
        """
        
        cursor.execute(query, (
            var_id, start_str, end_str,
            zone_bbox[1], zone_bbox[3], zone_bbox[0], zone_bbox[2]
        ))
        
        results = cursor.fetchall()
        
        formatted_results = []
        for row in results:
            val = float(row['valeur'])
            # Calcule l'intensité de couleur (0 à 1)
            intensity = (val - min_val) / (max_val - min_val)
            intensity = max(0.0, min(1.0, intensity))
            
            formatted_results.append([
                float(row['lat']),
                float(row['lon']),
                round(val, 2),
                intensity
            ])

        cursor.close()
        conn.close()
        return formatted_results
        
    except Exception:
        return []

def get_available_dates():
    # Liste les dates disponibles pour le filtre
    conn = get_db_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT DISTINCT DATE_FORMAT(Jour_Opti, '%Y-%m-%d') as date_val 
            FROM mesure 
            ORDER BY date_val DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        dates = [r['date_val'] for r in rows]
        cursor.close()
        conn.close()
        return dates
    except Exception:
        return []