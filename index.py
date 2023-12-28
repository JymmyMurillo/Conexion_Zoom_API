import base64
from flask import Flask, request, redirect, jsonify
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Cambia esto con una clave segura y guárdala de forma segura

# Configuración de la aplicación OAuth en Zoom
client_id = os.getenv('ZOOM_CLIENT_ID')
client_secret = os.getenv('ZOOM_CLIENT_SECRET')
redirect_uri = os.getenv('ZOOM_REDIRECT_URI')  # Ajusta esto según tu configuración en la plataforma de desarrollo de Zoom

# URL de autorización de Zoom
authorization_url = f'https://zoom.us/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'

@app.route('/')
def home():
    """Ruta principal que redirige a la página de autorización de Zoom."""
    return f'<a href="{authorization_url}">Iniciar sesión con Zoom</a>'

@app.route('/redirect')
def redirect_page():
    """Ruta que maneja la redirección desde Zoom después de la autorización."""
    # Recuperar el código de autorización de la consulta de redireccionamiento
    code = request.args.get('code')

    # Intercambio de código de autorización por un token de acceso
    token_url = 'https://zoom.us/oauth/token'
    client_credentials = f'{client_id}:{client_secret}'
    headers = {'Authorization': f'Basic {base64.b64encode(client_credentials.encode()).decode()}'}
    data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri}

    # Hacer la solicitud para obtener el token de acceso
    response = requests.post(token_url, headers=headers, data=data)
    token_data = response.json()
    access_token = token_data.get('access_token')

    # Obtener información del usuario utilizando el token de acceso
    user_url = 'https://api.zoom.us/v2/users/me'
    headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get(user_url, headers=headers)
    user_info = user_response.json()

    # Aquí puedes hacer lo que quieras con la información del usuario
    return jsonify(user_info)

if __name__ == '__main__':
    app.run(debug=True)