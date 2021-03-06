import os
import base64
from datetime import datetime

from .dog_face_cropper import DogFaceCropper

from src.util import eliminar_archivos_temporales, download_image, read_bytes_from_file

dfc = DogFaceCropper('./src/cropper/detectors')

class DogFaceCropperService():

    def __init__(self):
        if not os.path.exists('./temp_crop/'):
            os.mkdir('./temp_crop/')

    def obtener_nombre_archivos(self):
        current_date = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S.%f')[:-3]
        nombre_imagen_a_recortar = './temp_crop/image_{}.jpg'.format(current_date)
        nombre_imagen_recortada = './temp_crop/new_image_{}.jpg'.format(current_date)
        return nombre_imagen_a_recortar, nombre_imagen_recortada

    def recortar_imagen_mascota(self, imagen_bytes):
        print('Inicio de Service para recortar una imagen ({})'.format(datetime.now()))
        results={}
        resultado_imagen = None
        try:
            nombre_imagen_a_recortar, nombre_imagen_recortada = self.obtener_nombre_archivos()

            with open(nombre_imagen_a_recortar, 'wb') as f:
                f.write(base64.b64decode(imagen_bytes))

            flag = dfc.process_file(nombre_imagen_a_recortar, nombre_imagen_recortada)
            
            if flag:
                with open(nombre_imagen_recortada,'rb') as file:
                    img = file.read()
                
                codigo, mensaje  = 200, 'La foto contiene un rostro de perro.'
                resultado_imagen = base64.b64encode(img)
                #eliminar_archivos_temporales(nombre_imagen_recortada)
            else:
                codigo, mensaje  = 400, 'La foto no contiene un rostro de perro.'
            
            eliminar_archivos_temporales(nombre_imagen_a_recortar)
            print('Fin de Service de recorte de una imagen de mascota: {}'.format(datetime.now()))
            results['mensaje'] = mensaje
            results['codigo'] = codigo
            return flag, nombre_imagen_recortada, resultado_imagen, results
        except Exception as e:
            print('Hubo un error al recortar una imagen de mascota: ({}) {}'.format(datetime.now(), e))
            eliminar_archivos_temporales(nombre_imagen_a_recortar)
            #eliminar_archivos_temporales(nombre_imagen_recortada)
            results['mensaje'] = 'Hubo un error al recortar una imagen de mascota.'
            results['codigo'] = 503
            return False, None, None, results
    
    def obtener_imagenes_recortadas(self, list_img_url):
        print('Inicio de descarga de im??genes de mascota')
        results={}
        imagenes_recortadas_base64 = []
        list_img_paths = [] # Ubicaci??n de los archivos en disco
        try:
            if len(list_img_url) == 0:
                results = {'mensaje':'Debe cargar al menos una imagen de mascota a recortar.', 'codigo': 400}
                return False, [], [], results
            
            contador_error_img_url = 0
            for indice_list_img_url,img_url in enumerate(list_img_url):
                try:
                    nombre_imagen_a_recortar, nombre_imagen_recortada = self.obtener_nombre_archivos()
                    
                    flag,mensaje = download_image(img_url, nombre_imagen_a_recortar)
                    contador_error_img_url += 1 if not flag else 0
                    if contador_error_img_url == len(list_img_url):
                        results = {'mensaje':mensaje,'codigo':503}
                    
                    if flag:
                        try:
                            flag = dfc.process_file(nombre_imagen_a_recortar, nombre_imagen_recortada)
                            if flag:
                                list_img_paths.append(nombre_imagen_recortada)
                                file_base64 = read_bytes_from_file(nombre_imagen_recortada)
                                imagenes_recortadas_base64.append(file_base64)
                                codigo, mensaje  = 200, 'La foto contiene un rostro de perro.'
                            else:
                                codigo, mensaje  = 400, 'La foto no contiene un rostro de perro.'
                            results = {'mensaje':mensaje,'codigo':codigo}
                        except Exception as e:
                            eliminar_archivos_temporales(nombre_imagen_a_recortar)
                            print('Hubo un error durante el recorte de las im??genes de mascota ({}): {}'.format(datetime.now(), e))
                            results = {'mensaje':'Hubo un error durante el recorte de las im??genes de mascota.','codigo':503}
                            return False, [], [], results

                    eliminar_archivos_temporales(nombre_imagen_a_recortar)
                except Exception as e:
                    print('Hubo un error al descargar una imagen de mascota: ({}) {}'.format(datetime.now(), e))
                    eliminar_archivos_temporales(nombre_imagen_a_recortar)
                    return False, [], [], results
            print('Fin de descarga de im??genes de mascota')
            return True, list_img_paths, imagenes_recortadas_base64, results
        except Exception as e:
            print('Hubo un error durante el proceso de descarga de imagen de mascota: ({}) {}'.format(datetime.now(), e))
            return False, [], [], results

    def recortar_imagenes_mascota(self, list_imagen_bytes):
        print('Inicio de Service para recortar las im??genes ({})'.format(datetime.now()))
        results={}
        imagenes_recortadas_base64 = []
        list_img_paths = [] # Ubicaci??n de los archivos en disco
        try:
            if len(list_imagen_bytes) == 0:
                results['mensaje'] = 'Debe cargar al menos una imagen de mascota a recortar.'
                results['codigo'] = 400
                return False, None, None, results
            
            flag_aux = False
            for imagen_bytes in list_imagen_bytes:
                flag, nombre_imagen_recortada, imagen_recortada_bytes, respuesta = self.recortar_imagen_mascota(imagen_bytes)
                if flag:
                    flag_aux = True
                    imagenes_recortadas_base64.append(imagen_recortada_bytes)
                    list_img_paths.append(nombre_imagen_recortada)
                results = respuesta
            
            print('Fin de Service para recortar las {} im??genes de mascota ({})'.format(len(imagenes_recortadas_base64), datetime.now()))
            return flag_aux, list_img_paths, imagenes_recortadas_base64, results
        except Exception as e:
            print('Hubo un error durante el recorte de las im??genes de mascota ({}): {}'.format(datetime.now(), e))
            results['mensaje'] = 'Hubo un error durante el recorte de las im??genes de mascota.'
            results['codigo'] = 503
            return False, None, None, results