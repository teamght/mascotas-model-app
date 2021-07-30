import os
import base64
from datetime import datetime

from .dog_face_cropper import DogFaceCropper

from src.util import eliminar_archivos_temporales, download_image

dfc = DogFaceCropper('./src/cropper/detectors')

class DogFaceCropperService():

    def __init__(self):
        pass

    def obtener_nombre_archivos(self):
        if not os.path.exists('./temp_crop/'):
            os.mkdir('./temp_crop/')

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
                resultado_imagen = base64.b64encode(img)#.decode('utf-8')
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
    
    def descargar_imagenes_mascota(self, list_img_url):
        print('Inicio de descarga de imágenes de mascota')
        results={}
        imagenes_recortadas_base64 = []
        list_img_paths = [] # Ubicación de los archivos en disco
        try:
            if len(list_img_url) == 0:
                results['mensaje'] = 'Debe cargar al menos una imagen de mascota a recortar.'
                results['codigo'] = 400
                return False, [], [], results
            
            for img_url in list_img_url:
                try:
                    nombre_imagen_a_recortar, nombre_imagen_recortada = self.obtener_nombre_archivos()
                    
                    flag, img_path = download_image(img_url, nombre_imagen_a_recortar)
                    print(nombre_imagen_a_recortar, img_path)

                    if flag:
                        try:
                            flag = dfc.process_file(nombre_imagen_a_recortar, nombre_imagen_recortada)
                            if flag:
                                list_img_paths.append(nombre_imagen_recortada)

                                # Arreglo de Bytes64
                                with open(nombre_imagen_recortada,'rb') as file:
                                    img_base64_encode = base64.b64encode(file.read())
                                    imagenes_recortadas_base64.append(img_base64_encode)
                                codigo, mensaje  = 200, 'La foto contiene un rostro de perro.'
                            else:
                                codigo, mensaje  = 400, 'La foto no contiene un rostro de perro.'
                            results['mensaje'] = mensaje
                            results['codigo'] = codigo
                        except Exception as e:
                            eliminar_archivos_temporales(nombre_imagen_a_recortar)
                            print('Hubo un error durante el recorte de las imágenes de mascota ({}): {}'.format(datetime.now(), e))
                            results['mensaje'] = 'Hubo un error durante el recorte de las imágenes de mascota.'
                            results['codigo'] = 503
                            return False, [], [], results

                    eliminar_archivos_temporales(nombre_imagen_a_recortar)
                except Exception as e:
                    print('Hubo un error al descargar una imagen de mascota: ({}) {}'.format(datetime.now(), e))
                    eliminar_archivos_temporales(nombre_imagen_a_recortar)
                    return False, [], [], results
            print('Fin de descarga de imágenes de mascota')
            return True, list_img_paths, imagenes_recortadas_base64, results
        except Exception as e:
            print('Hubo un error durante el proceso de descarga de imagen de mascota: ({}) {}'.format(datetime.now(), e))
            return False, [], [], results

    def recortar_imagenes_mascota(self, list_imagen_bytes):
        print('Inicio de Service para recortar las imágenes ({})'.format(datetime.now()))
        results={}
        imagenes_recortadas_base64 = []
        list_img_paths = [] # Ubicación de los archivos en disco
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
            
            print('Fin de Service para recortar las {} imágenes de mascota ({})'.format(len(imagenes_recortadas_base64), datetime.now()))
            return flag_aux, list_img_paths, imagenes_recortadas_base64, results
        except Exception as e:
            print('Hubo un error durante el recorte de las imágenes de mascota ({}): {}'.format(datetime.now(), e))
            results['mensaje'] = 'Hubo un error durante el recorte de las imágenes de mascota.'
            results['codigo'] = 503
            return False, None, None, results