from flask import Blueprint, jsonify, request, session
from app.models import repository
from app import cache

api_bp = Blueprint('api', __name__)

# --- Routes pour les graphiques ---

@api_bp.route('/api/stats/weekly')
def stats_weekly():
    start = request.args.get('start')
    end = request.args.get('end')
    ind = request.args.get('ind', 'SST')
    data, duration = repository.fetch_weekly_data(start, end, ind)
    return jsonify({'results': data, 'time': duration})

@api_bp.route('/api/stats/correlation')
def stats_correlation():
    start = request.args.get('start')
    end = request.args.get('end')
    ind1 = request.args.get('ind1')
    ind2 = request.args.get('ind2')
    data, duration = repository.fetch_correlation_data(start, end, ind1, ind2)
    return jsonify({'results': data, 'time': duration})

@api_bp.route('/api/stats/distribution')
def stats_distribution():
    start = request.args.get('start')
    end = request.args.get('end')
    ind = request.args.get('ind')
    data, duration = repository.fetch_distribution_data(start, end, ind)
    return jsonify({'results': data, 'time': duration})

# --- Route pour la carte ---

@api_bp.route('/api/data')
@cache.cached(timeout=60, query_string=True) # Mise en cache pour 60 sec
def get_map_data():
    start_date = request.args.get('start') 
    end_date = request.args.get('end')
    
    if not end_date: 
        end_date = start_date

    indicator = request.args.get('indicator', 'SST')
    zone = request.args.get('zone', 'europe')

    # Coordonnées des zones
    zones_bbox = {
        'manche': [-6.0, 48.0, 2.0, 52.0],
        'atl':    [-10.0, 43.0, -1.0, 49.0],
        'med':    [3.0, 36.0, 15.0, 44.0],
        'europe': [-20.0, 30.0, 30.0, 60.0]
    }
    bbox = zones_bbox.get(zone, zones_bbox['europe'])
    
    try:
        data = repository.get_map_data_local(start_date, end_date, indicator, bbox)
        return jsonify(data)
        
    except Exception:
        return jsonify({"error": "Erreur serveur"}), 500

# --- Routes pour les favoris ---

@api_bp.route('/api/favoris/add', methods=['POST'])
def add_fav_route():
    if 'user_id' not in session: return jsonify({'error': 'Non connecté'}), 401
    data = request.json
    status = repository.add_favorite_safe(
        session['user_id'], data.get('zone'), data.get('indicator'), 
        data.get('start_date'), data.get('end_date')
    )
    msg = "Favori ajouté !" if status == 'added' else "Déjà existant !"
    return jsonify({'status': status, 'message': msg})

@api_bp.route('/api/favoris/delete', methods=['POST'])
def delete_fav_route():
    if 'user_id' not in session: return jsonify({'error': 'Non connecté'}), 401
    data = request.json
    success = repository.delete_favorite_by_id(data.get('fav_id'), session['user_id'])
    return jsonify({'success': success})

@api_bp.route('/admin/logs')
def admin_logs():
    if not repository.is_admin(session.get('user_id')):
        return jsonify([]), 403
    logs = repository.get_admin_logs()
    return jsonify(logs)

@api_bp.route('/api/available-dates')
def available_dates_route():
    dates = repository.get_available_dates()
    return jsonify(dates)
