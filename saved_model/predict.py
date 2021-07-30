
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import tensorflow as tf
import os
import numpy as np
import skimage as sk
import matplotlib.pyplot as plt
import tensorflow.keras.backend as K
import io
import itertools
from datetime import datetime
import base64
from PIL import Image
from saved_model.model_configuracion import ModelConfig
#from saved_model.online_training import predict_generator
from src.config import SIZE
from src.mongodb_config import MongoDB_Config
from src.util import obtener_nombre_nueva_imagen

h,w,c = SIZE
model_config = ModelConfig()
mongodb = MongoDB_Config()


def load_images(filenames):
    """
    Use scikit-image library to load the pictures from files to numpy array.
    """
    h,w,c = SIZE
    images = np.empty((len(filenames),h,w,c))
    for i,img_path in enumerate(filenames):
        # Base64
        with open(img_path,'rb') as image_file:
            img_base64_encode = base64.b64encode(image_file.read())
            img_base64 = base64.b64decode(img_base64_encode)
            images[i] = np.array(Image.open(io.BytesIO(img_base64)))/255.0 # Reducción en distancia
        #images[i] = sk.io.imread(img_path)/255.0 # SI
    return images

def predict_generator(filenames, batch_size=32):
    """
    Prediction generator.
    filenames: Lista de rutas de los archivos
    """
    for i in range(0,len(filenames),batch_size):
        #print(f'predict_generator: {i} de {len(filenames)}')
        images_batch = load_images(filenames[i:i+batch_size])
        yield images_batch

def distance(v1, v2):
    diff = np.square(v1-v2)
    dist = np.sum(diff)
    return dist

def _predict_tensorflow_array(model, img_arrays):
    print('Inicio predict_tensorflow array {}'.format(datetime.now()))
    print(f"{img_arrays.shape}")
    if img_arrays.size == 0:
        return np.empty((0,32))
    predict = model.predict(img_arrays)
    print('Fin predict_tensorflow array {}'.format(datetime.now()))
    return predict

def _predict_tensorflow(model, filenames_test):
    print('Inicio predict_tensorflow {}'.format(datetime.now()))
    
    #generator = predict_generator(filenames_test, 64) # filenames_test, batch=32
    #steps = np.ceil(len(filenames_test)/64) # all
    #predict = model.predict_generator(generator, steps=steps)
    #predict = model.predict(generator, steps=steps)
    #if filenames_test.size == 0:
    #    return np.empty((0,32))
    
    #predict = model.predict(filenames_test)
    
    generator = predict_generator(filenames_test, batch_size=len(filenames_test))
    predict = model.predict_generator(generator, steps=1)

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
            image = np.array(Image.open(io.BytesIO(bytestring)))/255.0
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
    print('Inicio obtener indices de las imágenes más cercanas')
    try:
        seen = set()
        seen_add = seen.add
        prueba = []
        for indice_ruta, (array_img, label, distancia) in enumerate(list_rutas):
            # Retornar lista con los 3 primeros elementos
            if len(prueba) > 3:
                break
            
            if not (label in seen or seen_add(label)):
                if indice_ruta > 0:
                    distancia_aux = np.sum([prueba[-1][2], np.float32(0.000001)])
                    if distancia_aux <= distancia:
                        prueba.append((array_img, label, distancia))

                if indice_ruta == 0:
                    prueba.append((array_img, label, distancia))
        
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

def predict_data(list_img_paths, imagenes_recortadas_base64, mascota_datos, azure_storage_cliente_mascotas):
    results={}
    try:
        # Consulta por Latitud y Longitud
        global predict_tensorflow_db_imagenes
        global filenames_test
        global image_array
        global labels
        global nbof_classes
        filenames_test, image_array, labels, nbof_classes = _obtener_ruta_de_imagen(mascota_datos.geolocalizacion_reportado, mascota_datos.estado)
        predict_tensorflow_db_imagenes = _predict_tensorflow_array(model, image_array)

        list_img_arrays = np.empty((len(imagenes_recortadas_base64),h,w,c))
        
        list_img_paths.sort()
        for indice, img_path in enumerate(list_img_paths):
            list_img_arrays[indice] = sk.io.imread(img_path)/255.0
        
        predict_tensorflow_imagenes_cargadas = _predict_tensorflow(model, list_img_paths)
        
        if predict_tensorflow_db_imagenes.size > 0:
            flag, images_and_distances = _query_image_tensorflow(predict_tensorflow_imagenes_cargadas, predict_tensorflow_db_imagenes, image_array, labels, nbof_classes)
            if not flag:
                return results

            flag, id_images_and_distances = _obtener_label_imagenes_cercanas([(img_array, label, distancia) for _, img_array, label, distancia in images_and_distances])
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
def add_image_to_memory_predictions(list_img_paths, label):

    global predict_tensorflow_db_imagenes
    global filenames_test
    global image_array
    global labels
    global nbof_classes
    
    images = np.empty((len(list_img_paths),h,w,c))
    # Base64
    for i,img_path in enumerate(list_img_paths):
        with open(img_path,'rb') as image_file:
            img_base64_encode = base64.b64encode(image_file.read())
            img_base64 = base64.b64decode(img_base64_encode)
            image = np.array(Image.open(io.BytesIO(img_base64)))/255.0 # Reducción en distancia
            images[i] = image
            #images[i] = sk.io.imread(img_path)/255.0

    predict_tensorflow_imagen_cargada = _predict_tensorflow(model, list_img_paths)
    
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