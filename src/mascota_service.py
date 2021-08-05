import os
import base64
from datetime import datetime
from src.util import eliminar_archivos_temporales, obtener_nombre_nueva_imagen, siguiente_numero_carpeta_imagen, read_bytes_from_file
from src.mongodb_config import MongoDB_Config

mongodb = MongoDB_Config()

class MascotaService():

    def __init__(self):
        # Crear archivo temporal
        if not os.path.exists('./static/'):
            os.mkdir('./static/')
    
    def obtener_label_img_mascotas(self, geolocalizacion_persona, estado):
        '''
        Retorna una lista de tupla (label,img_base64)
        '''
        #lista_mascotas_reportadas = mongodb.obtener_mascotas_reportadas_por_geolocalizacion(geolocalizacion_persona, estado)
        lista_mascotas_reportadas = mongodb.obtener_mascotas_perdidas(geolocalizacion_persona, estado)
        list_data_mascota = [(data_mascota['label'],data_mascota['file_name'],img_base64) for data_mascota in lista_mascotas_reportadas for img_base64 in data_mascota['list_encoded_string']]
        return list_data_mascota
    
    def obtener_public_urls(self, azure_storage_cliente_mascotas,full_file_name,list_encoded_string):
        return [azure_storage_cliente_mascotas.get_file_public_url(
                f'{full_file_name.split("_")[0]}_{indice}.jpg')
                for indice, _ in enumerate(list_encoded_string)]
    
    def obtener_data(self, label_image, distancia, azure_storage_cliente_mascotas):
        flag, data_mascota, mensaje = mongodb.obtener_mascota(str(label_image))
        if flag:
            full_file_name_aux = str(data_mascota['full_file_name'])
            data_mascota['list_encoded_string'] = self.obtener_public_urls(azure_storage_cliente_mascotas,
                                                                    full_file_name_aux,
                                                                    data_mascota['list_encoded_string'])
            data_mascota.update({'label':label_image,'distancia':distancia})
            return flag, data_mascota, mensaje
        return flag, None, mensaje
    
    def obtener_data_by_id(self, id_denuncia, azure_storage_cliente_mascotas):
        i = 1
        while i < 5:
            flag, data_mascota, mensaje = mongodb.obtener_mascota_by_id(str(id_denuncia))
            print(f"Resultado de la búsqueda de la denuncia {id_denuncia} (intento {i}): {flag}")
            if flag:
                break
            i += 1
        
        if flag:
            full_file_name_aux = str(data_mascota['full_file_name'])
            data_mascota['list_encoded_string'] = self.obtener_public_urls(azure_storage_cliente_mascotas,
                                                                    full_file_name_aux,
                                                                    data_mascota['list_encoded_string'])
            print(f"Tamaño de la lista de URL's publicas de la denuncia {id_denuncia}: {len(data_mascota['list_encoded_string'])}")
            return flag, data_mascota, mensaje
        return flag, mensaje, mensaje
    
    def reportar_mascota_desaparecida(self, mascota_desaparecida, azure_storage_cliente_mascotas, list_img_paths):
        print('Inicio de reportar desaparición: {}'.format(datetime.now()))
        try:
            lista_imagenes_bytes = mascota_desaparecida.lista_imagenes_bytes
            caracteristicas = mascota_desaparecida.caracteristicas
            geolocalizacion = mascota_desaparecida.geolocalizacion_reportado
            fecha_perdida = mascota_desaparecida.fecha_perdida
            barrio_nombre = mascota_desaparecida.barrio_nombre
            genero = mascota_desaparecida.genero
            nombre = mascota_desaparecida.nombre
            comportamiento = mascota_desaparecida.comportamiento
            datos_adicionales = mascota_desaparecida.datos_adicionales
            estado = mascota_desaparecida.estado

            # Obtener label y nombre de archivo para persistir en base de datos
            label = siguiente_numero_carpeta_imagen(azure_storage_cliente_mascotas)
            
            try:
                for indice_img, nombre_imagen_a_predecir in enumerate(list_img_paths):
                    #
                    # Guardar imagen en Azure Storage
                    #
                    # Nombre con el que se guardará en Azure Storage
                    full_file_name, file_name = obtener_nombre_nueva_imagen(label, indice_img)
                    azure_storage_cliente_mascotas.upload_image(full_file_name, nombre_imagen_a_predecir)
            except Exception as e:
                print('Hubo un error al cargar la imagen ({}): {}'.format(datetime.now(), e))
                eliminar_archivos_temporales(list_img_paths)
                return False, 'Hubo un error al cargar la imagen.', None
            
            #
            # Guardar en base de datos
            #
            flag, respuesta, identificador = mongodb.registrar_mascota_reportada(list_encoded_string=lista_imagenes_bytes, full_file_name=full_file_name, 
                    image_path=file_name, label=label, caracteristicas=caracteristicas, 
                    ubicacion=geolocalizacion, fecha_perdida=fecha_perdida,
                    barrio_nombre=barrio_nombre, genero=genero,
                    nombre=nombre, comportamiento=comportamiento,
                    datos_adicionales=datos_adicionales,
                    estado=estado,
                    dueno=mascota_desaparecida.dueno)
            #if flag:
            #    add_image_to_memory_predictions(list_img_paths, label)
            
            eliminar_archivos_temporales(list_img_paths)
            print('Fin de reportar mascota desaparecida: {}'.format(datetime.now()))
            return flag, respuesta, (full_file_name, file_name, label, identificador)
        except Exception as e:
            print('Hubo un error al reportar desaparición ({}): {}'.format(datetime.now(), e))
            eliminar_archivos_temporales(list_img_paths)
            return False, 'Hubo un error al reportar desaparición.', None

    def eliminar_mascota(self, id, label, azure_storage_cliente_mascotas):
        try:
            try:
                flag, mensaje, label_mascota = mongodb.eliminar_mascota(id=id, label=label)
            except Exception as e:
                print('Error al eliminar mascota en base de datos ({}): {}'.format(datetime.now(), e))
                return False, mensaje
            
            if flag:
                flag, mensaje = azure_storage_cliente_mascotas.eliminar_carpeta(label_mascota)
                if not flag:
                    return False, mensaje
                #delete_image_from_memory_predictions(label)
            return True, 'Se logró eliminar mascota.'
        except Exception as e:
            print('Hubo un error al eliminar mascota ({}): {}'.format(datetime.now(), e))
            return False, 'Hubo un error al eliminar mascota.'

    def reportar_mascota_encontrada(self, id):
        try:
            flag, mensaje, label = mongodb.encontrar_mascota(id)
            if flag:
                #delete_image_from_memory_predictions(label)
                return True, 'Operación exitosa.'
            return False, mensaje
        except Exception as e:
            print('Hubo un error al reportar mascota encontrada ({}): {}'.format(datetime.now(), e))
            return False, 'Hubo un error al reportar mascota encontrada.'
    
    def actualizar_datos(self, id, mascota_datos):
        flag, mensaje = mongodb.actualizar_mascota(id, mascota_datos)
        return flag, mensaje
