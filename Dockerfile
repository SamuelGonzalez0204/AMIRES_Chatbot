# Usa una imagen base oficial de Python. 'slim-bookworm' es más ligera.
FROM python:3.12-slim-bookworm

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requisitos e instálalos primero.
# Esto aprovecha el caché de Docker si los requisitos no cambian.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código de tu aplicación al directorio de trabajo
COPY . .

# Expone el puerto en el que la aplicación Flask se ejecutará dentro del contenedor
# (Gunicorn, que usaremos, por defecto escucha en el puerto 8000)
EXPOSE 8000

# Comando para iniciar la aplicación Flask usando Gunicorn (servidor de producción)
# El formato es 'nombre_del_modulo:instancia_de_la_app'
# 'chatbot_api' es el nombre de tu archivo sin .py
# 'app' es la variable de Flask (app = Flask(__name__))
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "chatbot_api:app"]