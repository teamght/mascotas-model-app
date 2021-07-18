import os

MODELO_ENTRENADO = 'saved_model'

REPOSITORIO_DE_IMAGENES_PUBLICAS = 'static'

FORMATO_NUEVA_IMAGEN = '{}_{}.jpg'

DB_URI = os.environ.get('MONGODB_URL')
DB_NAME = os.environ.get('DB_NAME')
DB_COLECCION = os.environ.get('DB_COLECCION')
SIZE = (224,224,3)

ACCOUNT_NAME = os.environ.get('ACCOUNT_NAME')
ACCOUNT_KEY = os.environ.get('ACCOUNT_KEY')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME')

DISTANCIA_KILOMETROS = os.environ.get('DISTANCIA_KILOMETROS')
