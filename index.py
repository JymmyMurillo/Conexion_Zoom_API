import base64
import os
from collections import defaultdict
from datetime import timedelta, datetime
from io import BytesIO
from flask import Flask, request, send_file
import requests
from dotenv import load_dotenv
import pandas as pd
import pytz

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
BASE_API_URL = 'https://api.zoom.us/v2'

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

result = {}
meeting_data = {}

@app.route('/redirect')
def redirect_page():
    """Ruta que maneja la redirección desde Zoom después de la autorización."""
    global result, meeting_data
    # Recuperar el código de autorización de la consulta de redireccionamiento
    code = request.args.get('code')

    # Intercambio de código de autorización por un token de acceso
    token_url = 'https://zoom.us/oauth/token'
    client_credentials = f'{client_id}:{client_secret}'
    headers = {'Authorization': f'Basic {base64.b64encode(client_credentials.encode()).decode()}'}
    data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri}

    # Hacer la solicitud para obtener el token de acceso
    response = requests.post(token_url, headers=headers, data=data, timeout=10)
    response.raise_for_status()
    token_data = response.json()
    access_token = token_data.get('access_token')
    
    # Obtener información de la reunión
    meeting_url = f'{BASE_API_URL}/meetings/{meeting_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    meeting_response = requests.get(meeting_url, headers=headers, timeout=10)
    meeting_data = meeting_response.json()

    # Ajustar la fecha de inicio a la zona horaria de Colombia
    start_time_utc = datetime.fromisoformat(meeting_data['start_time'][:-1]).replace(tzinfo=pytz.utc)
    start_time_colombia = start_time_utc.astimezone(pytz.timezone('America/Bogota'))
    formatted_start_time = start_time_colombia.strftime('%Y-%m-%d %H:%M:%S')

    # Actualizar la información de la reunión con la fecha ajustada
    meeting_data.update({'start_time_colombia': formatted_start_time})

    # Inicializar un diccionario para almacenar información de participantes agrupada por nombre
    participant_data = defaultdict(lambda: {'connections': 0, 'connection_times': [], 'total_duration': 0})

    # Obtener listado de asistencia a la reunión con paginación
    next_page_token = None

    while True:
        # Construir la URL de la API con el token de la página siguiente si está disponible
        if next_page_token:
            api_url = f'{BASE_API_URL}/report/meetings/{meeting_id}/participants?page_size=300&next_page_token={next_page_token}'
        else:
            api_url = f'{BASE_API_URL}/report/meetings/{meeting_id}/participants?page_size=300'

        api_response = requests.get(api_url, headers=headers, timeout=10)
        api_response.raise_for_status()
        api_info = api_response.json()

        # Agregar los participantes de la página actual al diccionario
        for participant in api_info.get('participants', []):
            participant_name = participant.get('name')
            join_time = participant.get('join_time')
            leave_time = participant.get('leave_time')
            duration = participant.get('duration', 0)

            # Convertir las cadenas de tiempo a objetos datetime y ajustar la zona horaria
            join_time = datetime.fromisoformat(join_time).replace(tzinfo=pytz.utc)
            join_time_colombia = join_time.astimezone(pytz.timezone('America/Bogota'))

            leave_time = datetime.fromisoformat(leave_time).replace(tzinfo=pytz.utc)
            leave_time_colombia = leave_time.astimezone(pytz.timezone('America/Bogota'))

            # Incrementar el número de conexiones y agregar información de fechas y horas
            participant_data[participant_name]['connections'] += 1
            participant_data[participant_name]['connection_times'].append({
            'join_time': join_time_colombia.strftime('%Y-%m-%d %H:%M:%S'),
            'leave_time': leave_time_colombia.strftime('%Y-%m-%d %H:%M:%S')
        })

            # Sumar la duración de esta conexión al total
            participant_data[participant_name]['total_duration'] += duration

        # Verificar si hay más páginas
        next_page_token = api_info.get('next_page_token')
        if not next_page_token:
            break  # Salir del bucle si no hay más páginas

    # Estructurar el resultado con la información agrupada y el número de participantes
    result = {
        'total_records': api_info.get('total_records', 0),
        'num_participants': len(participant_data),  # Nuevo campo
        'participants': sorted([{'name': key, **value} for key, value in participant_data.items()], key=lambda x: x['name'])
    }

    # Convertir el resultado a un DataFrame de pandas para una visualización más clara
    df = pd.DataFrame(result['participants'])
    
    # Crear una nueva columna 'connection_info' que contenga la información formateada de conexión y desconexión
    df['connection_info'] = df.apply(lambda row: '<br>'.join([f'{pair["join_time"]} to {pair["leave_time"]}' for pair in row['connection_times']]), axis=1)

    # Eliminar la columna 'connection_times' original
    df = df.drop('connection_times', axis=1)

    # Convertir la duración total a formato de horas, minutos y segundos
    df['total_duration'] = df['total_duration'].apply(lambda x: str(timedelta(seconds=x)))

    # Renombrar las columnas a español
    df = df.rename(columns={
        'name': 'Nombre del participante',
        'connections': 'Número de conexiones',
        'connection_info': 'Información de conexión y desconexión',
        'total_duration': 'Duración total'
    })
    
    # Convertir el DataFrame a formato HTML
    table_html = df.to_html(index=False, classes='table table-bordered table-hover', escape=False)

    # Aplicar estilos para centrar el contenido en la tabla HTML
    table_html = table_html.replace('<td', '<td style="text-align:center; vertical-align:middle;"')
    
    # Obtener el número total de participantes y agregarlo a la visualización HTML
    total_participants_html = f'<p><strong>Número total de participantes:</strong> {len(participant_data)}</p>'

    # Renderizar la tabla HTML en la respuesta
    return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Información de participantes</title>
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
        </head>
        <body>
            <div class="container mt-3">
                <h2>Información de la reunión</h2>
                <p><strong>Nombre de la reunión:</strong> {meeting_data.get('topic')}</p>
                <p><strong>Organizador:</strong> {meeting_data.get('host_email')}</p>
                <p><strong>Fecha de la reunión:</strong> {meeting_data.get('start_time_colombia')}</p>
                <p><strong>ID de la reunión:</strong> {meeting_data.get('id')}</p>
                {total_participants_html}
                <h2>Información de participantes</h2>
                <a class="export-button btn btn-primary" href="/export">Exportar a Excel</a>
                {table_html}
            </div>
        </body>
        </html>
    '''

@app.route('/export')
def export_to_excel():
    global result, meeting_data
    
    # Obtener el DataFrame con la información de los participantes
    df = pd.DataFrame(result['participants'])

    # Crear una nueva columna 'connection_info' que contenga la información formateada de conexión y desconexión
    df['connection_info'] = df.apply(lambda row: '\n'.join([f'{pair["join_time"]} to {pair["leave_time"]}' for pair in row['connection_times']]), axis=1)

    # Eliminar la columna 'connection_times' original
    df = df.drop('connection_times', axis=1)
    
    # Renombrar las columnas a español
    df = df.rename(columns={
        'name': 'Nombre del participante',
        'connections': 'Número de conexiones',
        'connection_info': 'Información de conexión y desconexión',
        'total_duration': 'Duración total'
    })
    
    # Obtener la fecha de la reunión y el nombre de la reunión para construir el nombre del archivo
    meeting_date_colombia = datetime.fromisoformat(meeting_data['start_time'][:-1]).astimezone(pytz.timezone('America/Bogota'))
    meeting_date_str = meeting_date_colombia.strftime('%Y-%m-%d')
    excel_filename = f'{meeting_date_str}_{meeting_data["topic"].replace(" ", "_")}_Asistencia.xlsx'

    # Crear un objeto BytesIO para almacenar el archivo Excel
    excel_io = BytesIO()

   # Escribir la información de la reunión en el Excel antes de convertir el DataFrame
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        # Convertir el DataFrame a un archivo Excel
        df.to_excel(writer, index=False, startrow=8, sheet_name='Participantes', header=True)

        # Obtener el nombre real de la hoja del DataFrame después de escribirlo
        sheet_name = writer.sheets['Participantes'].name

        # Añadir un formato para las celdas con saltos de línea y centrado vertical y horizontal
        wrap_center_format = writer.book.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})

        # Aplicar el formato a la columna 'Información de conexión y desconexión'
        writer.sheets[sheet_name].set_column('D:D', 50, wrap_center_format)  # Ajusta el ancho (50 es un ejemplo)
        
        # Ajustar automáticamente el ancho de las demás columnas
        for i, col in enumerate(df.columns):
            if col != 'Información de conexión y desconexión':
                max_len = df[col].astype(str).apply(len).max()
                max_len = max_len if max_len > len(col) else len(col)
                writer.sheets[sheet_name].set_column(i, i, max_len + 2, wrap_center_format)
                
        # Escribir la información de la reunión
        writer.sheets[sheet_name].write('A1', 'Información de la reunión', writer.book.add_format({'bold': True, 'underline': True}))
        writer.sheets[sheet_name].write('A2', f'Nombre de la reunión: {meeting_data.get("topic")}')
        writer.sheets[sheet_name].write('A3', f'Organizador: {meeting_data.get("host_email")}')
        writer.sheets[sheet_name].write('A4', f'Fecha de la reunión: {meeting_data.get("start_time_colombia")}')
        writer.sheets[sheet_name].write('A5', f'ID de la reunión: {meeting_data.get("id")}')
        writer.sheets['Participantes'].write('A7', f'Número total de participantes: {result["num_participants"]}')


    # Guardar el archivo Excel en el objeto BytesIO

    excel_io.seek(0)

    # Enviar el archivo Excel como respuesta
    return send_file(excel_io, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name=excel_filename)

if __name__ == '__main__':
    app.run(debug=True)