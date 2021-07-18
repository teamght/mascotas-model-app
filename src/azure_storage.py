from azure.storage.blob import BlockBlobService

from .config import ACCOUNT_NAME, ACCOUNT_KEY, CONTAINER_NAME

#
# Configuración de cuenta de Azure
#
block_blob_service = BlockBlobService(
    account_name=ACCOUNT_NAME,
    account_key=ACCOUNT_KEY
)

class AzureStorageClienteMascotas():

    def __init__(self):
        print('Instanciando AzureStorageClienteMascotas ...')
        flag = block_blob_service.create_container(CONTAINER_NAME)
        print('AzureStorageClienteMascotas instanciado. El contenedor {} exite ({})'.format(CONTAINER_NAME, flag))
    
    def listar_archivos(self):
        return block_blob_service.list_blobs(container_name=CONTAINER_NAME, prefix='static', delimiter='/static')
    
    def upload_image(self, full_file_name, file_path):
        block_blob_service.create_blob_from_path(CONTAINER_NAME, full_file_name, file_path)
    
    def eliminar_carpeta(self, nombre_carpeta):
        try:
            folders = [folder for folder in self.listar_archivos() if folder.name.split('/')[1] == nombre_carpeta]
            
            if len(folders) > 0:
                for dir_numero in folders:
                    print(dir_numero.name)
                    block_blob_service.delete_blob(container_name=CONTAINER_NAME, blob_name=dir_numero.name)

                return True, 'Carpeta eliminada.'
            print('No se encontró carpeta para eliminar')
            return False, 'No existe carpeta para eliminar.'
        except Exception as error:
            print('Error al eliminar carpeta: {}'.format(error))
            return False, 'Error al eliminar carpeta: {}'.format(error)
        