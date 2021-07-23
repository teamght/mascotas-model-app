import io
import numpy as np
import itertools
from datetime import datetime
import base64
from PIL import Image
import tensorflow as tf
from tensorflow import keras
import tensorflow.keras.backend as K
#from geopy import distance

from saved_model.model_configuracion import ModelConfig
from saved_model.online_training import predict_generator
from src.config import SIZE
from src.mongodb_config import MongoDB_Config
from src.util import obtener_nombre_nueva_imagen

h,w,c = SIZE
model_config = ModelConfig()
mongodb = MongoDB_Config()

def _predict_tensorflow(model, filenames_test):
    print('Inicio predict_tensorflow {}'.format(datetime.now()))
    #generator = predict_generator(filenames_test, 64) # filenames_test, batch=32
    #steps = np.ceil(len(filenames_test)/64) # all
    #predict = model.predict_generator(generator, steps=steps)
    #predict = model.predict(generator, steps=steps)
    if filenames_test.size == 0:
        return np.empty((0,32))
    
    predict = model.predict(filenames_test)
    print('Fin predict_tensorflow {}'.format(datetime.now()))
    return predict

def _obtener_ruta_de_imagen(geolocalizacion_persona, estado):
    print('Loading the dataset... {}'.format(datetime.now()))

    #lista_mascotas_reportadas = mongodb.obtener_mascotas_reportadas_por_geolocalizacion(geolocalizacion_persona, estado)
    lista_mascotas_reportadas = mongodb.obtener_mascotas_perdidas(geolocalizacion_persona, estado)

    filenames = np.empty(0)
    labels = np.empty(0)

    image_array = np.empty((len(lista_mascotas_reportadas),h,w,c))

    print('Loading the arrays... {}'.format(datetime.now()))
    for indice, data_mascota in enumerate(lista_mascotas_reportadas):
        if data_mascota:
            filenames = np.append(filenames, data_mascota['file_name'])
            labels = np.append(labels, data_mascota['label'])
            image_db = data_mascota['list_encoded_string'][0]
            bytestring = base64.b64decode(image_db)
            image = np.array(Image.open(io.BytesIO(bytestring)))
            image_array[indice] = image
            
    if len(labels) == 0:
        print('[Warning] No se encontró registros en base de datos.')
        nbof_classes = 0
        return filenames, image_array, labels, nbof_classes

    print('Done. {}'.format(datetime.now()))
    print('Total number of imported pictures: {:d}'.format(len(labels)))

    nbof_classes = len(np.unique(labels))
    print('Total number of classes: {:d}'.format(nbof_classes))
    return filenames, image_array, labels, nbof_classes

def _query_image_tensorflow(predict_imagenes_cargadas, predict, image_array, labels_test, distances):
    print('Inicio  de predecir imagen(es) de rostro(s) de mascota')
    try:
        all_distances = []  # lista de distancias para c/u de las 3 fotos del perro buscado
        for i_image in range(len(predict_imagenes_cargadas)):
            emb1 = predict_imagenes_cargadas[i_image]
            differences = np.square(emb1 - predict)
            distances = np.sum(differences, 1)
            distances = list(distances)
            all_distances.append(distances)
        
        distances = [min(d) for d in zip(*all_distances)]  # para cada una de las fotos de la bd, nos quedamos con la distancia minima entre las 3 fotos del perro buscado
        
        images_and_distances = list(zip(itertools.count(), image_array, labels_test, distances))
        
        i_dog_to_find = 0  # TODO esto no es correcto, pero lo dejamos para no eliminar el if de abajo... previamente era un for que siempre terminaba en la primera iteracion
        
        if i_dog_to_find > 1:
            images_and_distances = [(i, filename, label, distance) for i, filename, label, distance in images_and_distances if i != i_dog_to_find]
        else:
            # Workaround cuando sólo se tiene una imagen en base de datos
            images_and_distances = [(i, filename, label, distance) for i, filename, label, distance in images_and_distances]

        # los ordeno por similitud
        images_and_distances.sort(key=lambda x: x[3])

        #print('images_and_distances: {} '.format(images_and_distances))
        return True, images_and_distances
    except Exception as e:
        print('Hubo un error al obtener las imágenes parecidas ({}): {}'.format(datetime.now(), e))
        return False, None

def _obtener_label_imagenes_cercanas(list_rutas):
    #print('Inicio obtener indices de las imágenes más cercanas {}'.format(list_rutas))
    print('Inicio obtener indices de las imágenes más cercanas')
    try:
        seen = set()
        seen_add = seen.add
        prueba = [(array_img, label, distancia) for array_img, label, distancia in list_rutas if not (label in seen or seen_add(label))]
        #print('Fin obtener indices de las imágenes más cercanas: {}'.format(prueba))
        print('Fin obtener indices de las imágenes más cercanas')
        return True, prueba
    except Exception as e:
        print('Hubo un error al obtener los label de las imagenes')
        print(e)
        return False, None

def _obtener_data_mascota(label_image, geolocalizacion_persona, azure_storage_cliente_mascotas):
    flag, data_mascota, mensaje = mongodb.obtener_mascota(str(label_image))
    if flag:
        lista = list()
        full_file_name_aux = str(data_mascota['full_file_name'])
        for indice, _ in enumerate(data_mascota['list_encoded_string']):
            lista.append(azure_storage_cliente_mascotas.get_file_public_url(f'{full_file_name_aux.split("_")[0]}_{indice}.jpg'))

        #data_mascota['list_encoded_string'] = [encoded_string.decode("utf-8") for encoded_string in data_mascota['list_encoded_string']]
        data_mascota['list_encoded_string'] = lista
        return flag, data_mascota
    return flag, mensaje
    
# DECLARAR VARIABLES
model = model_config.cargar_modelo()
#filenames_test, image_array, labels, nbof_classes = _obtener_ruta_de_imagen()
#predict_tensorflow_db_imagenes = _predict_tensorflow(model, image_array)
filenames_test, image_array, labels, nbof_classes = np.empty(0), np.empty((1,h,w,c)), np.empty(0), 0
predict_tensorflow_db_imagenes = np.empty((0,32))

def predict_data(imagenes_recortadas_bytes, mascota_datos, azure_storage_cliente_mascotas):
    results={}
    try:
        # Consulta por Latitud y Longitud
        global predict_tensorflow_db_imagenes
        global filenames_test
        global image_array
        global labels
        global nbof_classes
        filenames_test, image_array, labels, nbof_classes = _obtener_ruta_de_imagen(mascota_datos.geolocalizacion_reportado, mascota_datos.estado)
        predict_tensorflow_db_imagenes = _predict_tensorflow(model, image_array)

        np_images = []
        for imagen_recortada_bytes in imagenes_recortadas_bytes:
            np_image = np.array(Image.open(io.BytesIO(base64.b64decode(imagen_recortada_bytes))))
            np_images.append(np_image)
        
        n_imagenes = len(imagenes_recortadas_bytes)
        array_imagenes_a_predecir = np.empty((n_imagenes,h,w,c))
        for i, np_image in enumerate(np_images):
            array_imagenes_a_predecir[i] = np_image
        predict_tensorflow_imagenes_cargadas = _predict_tensorflow(model, array_imagenes_a_predecir)
        
        #print('predict_tensorflow_imagenes_cargadas {}'.format(len(predict_tensorflow_imagenes_cargadas)))
        #print('predict_tensorflow_db_imagenes {}'.format(len(predict_tensorflow_db_imagenes)))
        if predict_tensorflow_db_imagenes.size > 0:
            flag, images_and_distances = _query_image_tensorflow(predict_tensorflow_imagenes_cargadas, predict_tensorflow_db_imagenes, image_array, labels, nbof_classes)
            if not flag:
                return results
            
            flag, id_images_and_distances = _obtener_label_imagenes_cercanas([(img_array, label, distancia) for _, img_array, label, distancia in images_and_distances[0:10]])
            if not flag:
                return results
            #print('id_images_and_distances', id_images_and_distances)
            list_resultados_parecidos = list()
            for (_, label, distancia) in id_images_and_distances:
                flag, mascota = _obtener_data_mascota(label, mascota_datos.geolocalizacion_reportado, azure_storage_cliente_mascotas)
                if flag:
                    mascota['label'] = label
                    mascota['distancia'] = distancia
                    list_resultados_parecidos.append(mascota)
            #print(list_resultados_parecidos)
            results['resultados'] = list_resultados_parecidos
            results['mensaje'] = 'Si se han encontrado mascotas parecidas.'
            results['codigo'] = 200
        else:
            results['resultados'] = []
            results['mensaje'] = 'No se han encontrado mascotas parecidas.'
            results['codigo'] = 404
    except Exception as e:
        mensaje = 'Hubo un error al predecir la imágen'
        results['resultados'] = []
        results['mensaje'] = mensaje
        results['codigo'] = 503
        print('{} ({})'.format(mensaje, datetime.now()))
        print('Hubo un error. {}'.format(e))
    return results

# este método debe actualizar: predict_tensorflow_db_imagenes, filenames_test, labels, nbof_classes
def add_image_to_memory_predictions(data, label):

    global predict_tensorflow_db_imagenes
    global filenames_test
    global image_array
    global labels
    global nbof_classes
    
    image = np.array(Image.open(data))
    
    array_imagen_a_predecir = np.empty((1,h,w,c))
    
    array_imagen_a_predecir[0] = image
    
    predict_tensorflow_imagen_cargada = _predict_tensorflow(model, array_imagen_a_predecir)
    
    predict_tensorflow_db_imagenes = np.concatenate((predict_tensorflow_db_imagenes, predict_tensorflow_imagen_cargada))
    
    _, file_name = obtener_nombre_nueva_imagen(label)
    image_array = np.concatenate((image_array, image[np.newaxis,:,:]), axis=0)
    filenames_test = np.append(filenames_test, file_name)
    labels = np.append(labels, label)
    nbof_classes += 1
    
def delete_image_from_memory_predictions(label):
    global predict_tensorflow_db_imagenes
    global filenames_test
    global image_array
    global labels
    global nbof_classes
    
    label_indexs = np.where(labels == label)
    if len(label_indexs):
        labels = np.delete(labels, label_indexs[0])

        _, resultado_file_name = obtener_nombre_nueva_imagen(label)
        filenames_test_indexs = np.where(filenames_test == resultado_file_name)
        filenames_test = np.delete(filenames_test, filenames_test_indexs[0])

        nbof_classes -= 1