import os
import base64
from datetime import datetime
from saved_model.predict import add_image_to_memory_predictions, delete_image_from_memory_predictions
from src.util import eliminar_archivos_temporales, obtener_nombre_nueva_imagen, siguiente_numero_carpeta_imagen


def empadronar(mongodb,mascota,azure_storage_cliente_mascotas):
    fecha_busqueda = datetime.now()
    print('Inicio de reportar desaparición: {}'.format(fecha_busqueda))
    try:
        # Crear archivo temporal
        if not os.path.exists('./static/'):
            os.mkdir('./static/')
        
        current_date = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S.%f')[:-3]
        lista_nombre_imagen_a_predecir = list()
        
        lista_imagenes_bytes = mascota.lista_imagenes_bytes
        caracteristicas = mascota.caracteristicas
        geolocalizacion = mascota.geolocalizacion_reportado
        fecha_perdida = mascota.fecha_perdida
        barrio_nombre = mascota.barrio_nombre
        genero = mascota.genero
        nombre = mascota.nombre
        comportamiento = mascota.comportamiento
        datos_adicionales = mascota.datos_adicionales
        estado = mascota.estado

        if len(lista_imagenes_bytes) > 0:
            for index_imagen_bytes, imagen_bytes in enumerate(lista_imagenes_bytes):
                nombre_imagen_a_predecir = './static/image_{}_{}.jpg'.format(index_imagen_bytes, current_date)
                lista_nombre_imagen_a_predecir.append(nombre_imagen_a_predecir)
                with open(nombre_imagen_a_predecir, 'wb') as f:
                    f.write(base64.b64decode(imagen_bytes))
        
        # Obtener label y nombre de archivo para persistir en base de datos
        label = siguiente_numero_carpeta_imagen(azure_storage_cliente_mascotas)
        full_file_name, file_name = obtener_nombre_nueva_imagen(label)
        
        try:
            for indice_img, nombre_imagen_a_predecir in enumerate(lista_nombre_imagen_a_predecir):
                #
                # Guardar imagen en Azure Storage
                #
                # Nombre con el que se guardará en Azure Storage
                full_file_name, file_name = obtener_nombre_nueva_imagen(label, indice_img)
                azure_storage_cliente_mascotas.upload_image(full_file_name, nombre_imagen_a_predecir)
        except Exception as e:
            print('Hubo un error al cargar la imagen ({}): {}'.format(datetime.now(), e))
            eliminar_archivos_temporales(lista_nombre_imagen_a_predecir)
            return False, 'Hubo un error al cargar la imagen.', None
        
        list_encoded_string = list()
        #
        # Guardar en base de datos
        #
        for nombre_imagen_a_predecir in lista_nombre_imagen_a_predecir:
            with open(nombre_imagen_a_predecir, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                list_encoded_string.append(encoded_string)
        
        flag, respuesta, identificador = mongodb.registrar_mascota_reportada(list_encoded_string=list_encoded_string, full_file_name=full_file_name, 
                image_path=file_name, label=label, caracteristicas=caracteristicas, 
                ubicacion=geolocalizacion, fecha_perdida=fecha_perdida,
                barrio_nombre=barrio_nombre, genero=genero,
                nombre=nombre, comportamiento=comportamiento,
                datos_adicionales=datos_adicionales,
                estado=estado,
                dueno=mascota.dueno)
        
        eliminar_archivos_temporales(lista_nombre_imagen_a_predecir)
        print('Fin de empadronamiento de mascota: {}'.format(datetime.now()))
        return flag, respuesta, (full_file_name, file_name, label, identificador)
    except Exception as e:
        print('Hubo un error al empadronar la mascota ({}): {}'.format(datetime.now(), e))
        eliminar_archivos_temporales(lista_nombre_imagen_a_predecir)
        return False, 'Hubo un error al empadronar la mascota.', None


def reportar_mascota_desaparecida(mongodb, mascota_desaparecida, azure_storage_cliente_mascotas, list_img_paths):
    fecha_busqueda = datetime.now()
    print('Inicio de reportar desaparición: {}'.format(fecha_busqueda))
    try:
        # Crear archivo temporal
        if not os.path.exists('./static/'):
            os.mkdir('./static/')
        
        current_date = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S.%f')[:-3]
        
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
        full_file_name, file_name = obtener_nombre_nueva_imagen(label)
        
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
        
        list_encoded_string = list()
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
        if flag:
            add_image_to_memory_predictions(list_img_paths, label)
        
        eliminar_archivos_temporales(list_img_paths)
        print('Fin de reportar mascota desaparecida: {}'.format(datetime.now()))
        return flag, respuesta, (full_file_name, file_name, label, identificador)
    except Exception as e:
        print('Hubo un error al reportar desaparición ({}): {}'.format(datetime.now(), e))
        eliminar_archivos_temporales(list_img_paths)
        return False, 'Hubo un error al reportar desaparición.', None

def eliminar_mascota_de_memoria(label):
    try:
        delete_image_from_memory_predictions(label)
        return True, 'Se logró eliminar mascota.'
    except Exception as e:
        print('Hubo un error al eliminar mascota ({}): {}'.format(datetime.now(), e))
        return False, 'Hubo un error al eliminar mascota.'

def reportar_mascota_encontrada(label):
    try:
        delete_image_from_memory_predictions(label)
        return True, 'Operación exitosa.'
    except Exception as e:
        print('Hubo un error al reportar mascota encontrada ({}): {}'.format(datetime.now(), e))
        return False, 'Hubo un error al reportar mascota encontrada.'