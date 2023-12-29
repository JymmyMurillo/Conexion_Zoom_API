# Proyecto Flask de Asistencia a Reuniones Zoom

Este proyecto utiliza Flask para interactuar con la API de Zoom y obtener la lista de participantes en una reunión.

## Requisitos Previos

Asegúrate de tener instalado Python y pip. Además, se recomienda utilizar un entorno virtual para gestionar las dependencias del proyecto.

## Clonar el Repositorio

```bash
git clone https://github.com/JymmyMurillo/Conexion_Zoom_API.git

cd Conexion_Zoom_API
```

## Configuración de Variables de Entorno
Crea un archivo .env en el directorio raíz del proyecto y configura las variables de entorno necesarias. Puedes usar el archivo .env.example como base.

```bash
# Flask Configuration
FLASK_SECRET_KEY=YourSecretKeyExample #You define it randomly

# Zoom OAuth Configuration
ZOOM_CLIENT_ID=YourZoomClientIdExample #Extracted from the zoom Marketplace app
ZOOM_CLIENT_SECRET=YourZoomClientSecretExample #Extracted from the zoom Marketplace app
ZOOM_REDIRECT_URI=http://localhost:5000/redirect #You can leave this same value, it corresponds to the port where the application will be executed
ZOOM_MEETING_ID=YourZoomMeetingIdExample #Corresponds to the ID of the meeting to be reviewed, it must be changed each time a new meeting is created.
```

## Instalación de Dependencias
```bash
pip install -r requirements.txt
```

## Inicialización del Proyecto
```bash
python index.py
```
La aplicación se ejecutará en http://localhost:5000/. Abre tu navegador y accede a esta URL para iniciar sesión con Zoom.

## Uso
1. Haz clic en "Iniciar sesión con Zoom" en la página principal.
2. Autoriza la aplicación en la página de autenticación de Zoom.
3. Serás redirigido de nuevo a la aplicación, donde se mostrará la información de los participantes.

