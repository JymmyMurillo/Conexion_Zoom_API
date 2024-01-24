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
meeting_id = os.getenv('ZOOM_MEETING_ID') # Corresponde al ID de la reunion a revisar, hay que cambiarlo cada vez que se crea una nueva reunion

# URL de autorización de Zoom
authorization_url = f'https://zoom.us/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'

# API_URL base
base_api_url = f'https://api.zoom.us/v2'

@app.route('/')
def home():
    """Ruta principal que redirige a la página de autorización de Zoom."""
    return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }}

                .zoom-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    font-size: 32px;
                    text-align: center;
                    text-decoration: none;
                    background-color: #0000ff;
                    color: #ffffff;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }}

                .zoom-button:hover {{
                    background-color: #27ae60;
                }}
            </style>
            <title>Iniciar sesión con Zoom</title>
        </head>
        <body>
            <a class="zoom-button" href="{authorization_url}">Iniciar sesión con Zoom</a>
        </body>
        </html>
    '''

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

      # Inicializar una lista para almacenar todos los participantes
    all_participants = []

    # Obtener listado de asistencia a la reunión con paginación
    next_page_token = None

    while True:
        # Construir la URL de la API con el token de la página siguiente si está disponible
        if next_page_token:
            api_url = f'{base_api_url}/report/meetings/{meeting_id}/participants?page_size=300&next_page_token={next_page_token}'
        else:
            api_url = f'{base_api_url}/report/meetings/{meeting_id}/participants?page_size=300'

        headers = {'Authorization': f'Bearer {access_token}'}
        api_response = requests.get(api_url, headers=headers)
        api_info = api_response.json()

        # Agregar los participantes de la página actual a la lista
        all_participants.extend(api_info.get('participants', []))

        # Verificar si hay más páginas
        next_page_token = api_info.get('next_page_token')
        if not next_page_token:
            break  # Salir del bucle si no hay más páginas

    # Incluir el total de registros en el objeto JSON de salida
    result = {
        'total_records': api_info.get('total_records', 0),
        'participants': all_participants
    }

    # Puedes hacer lo que quieras con la lista completa de participantes
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)