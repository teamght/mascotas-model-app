import os
import pymongo
from azure.storage.blob import BlockBlobService

# Variables de entorno
DB_URI = os.environ.get('MONGODB_URL')
DB_NAME = os.environ.get('DB_NAME')
DB_COLECCION = os.environ.get('DB_COLECCION')
ACCOUNT_NAME = os.environ.get('ACCOUNT_NAME')
ACCOUNT_KEY = os.environ.get('ACCOUNT_KEY')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME')
DISTANCIA_KILOMETROS = os.environ.get('DISTANCIA_KILOMETROS')

#
# Configuración de cuenta de Azure
#
block_blob_service = BlockBlobService(
    account_name=ACCOUNT_NAME,
    account_key=ACCOUNT_KEY
)

# Mostrar todas las carpetas que existen
lista_carpetas = block_blob_service.list_blobs(container_name=CONTAINER_NAME, prefix='static', delimiter='/static')
for carpeta in lista_carpetas:
    print("Nombre de la carpeta: {}".format(carpeta.name))
    try:
        block_blob_service.delete_blob(CONTAINER_NAME,carpeta.name,snapshot=None)
    except Exception as e:
        print("Error al eliminar la carpeta {}: {}".format(carpeta.name, e))

# Eliminar todos los documentos de MongoDB
try:
    client = pymongo.MongoClient(DB_URI)
    db = client[DB_NAME]
    db[DB_COLECCION].remove()
except Exception as e:
    print("Error al eliminar colección: {}".format(e))