from app import create_app

app = create_app()

if __name__ == '__main__':
    print(" Lancement du serveur sur http://127.0.0.1:5001")
    app.run(host='127.0.0.1', port=5001)
