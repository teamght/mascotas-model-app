from flask import Flask, request, jsonify
from datetime import datetime
import os
import json

from src.azure_storage import AzureStorageClienteMascotas
from src.cropper.dog_face_cropper_service import DogFaceCropperService
from saved_model.predict import predict_data
from src.mascota_service import MascotaService
from src.mascota import Mascota
from src.mascota_dueno import MascotaDueno
from src.util import NumpyValuesEncoder, retornar_valor_campo_en_diccionario, existe_campo_en_diccionario

azure_storage_cliente_mascotas = AzureStorageClienteMascotas()
dog_face_cropper_service = DogFaceCropperService()
mascota_service = MascotaService()

port = int(os.environ.get("PORT", 5000))

app = Flask(__name__)


@app.route('/')
def index():
    return "Index Page",200

@app.route('/mascotas/busqueda', methods=['POST'])
def predict():
    dict_respuesta = {}
    print('Inicio de búsqueda de mascota: {}'.format(datetime.now()))
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 400},400
        else:
            # Datos del dueño
            dueno = retornar_valor_campo_en_diccionario(data, 'dueno')
            if not dueno is None:
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')  # Número telefónico de la persona que reportó desaparición
                email = retornar_valor_campo_en_diccionario(data['dueno'], 'email') # Correo electrónico de la persona que reportó desaparición
                contacto = retornar_valor_campo_en_diccionario(data['dueno'], 'contacto')  # Números de teléfonos asociados al perro desaparecido
                mascota_dueno_datos = MascotaDueno(identificador, email, contacto)
            
            geolocalizacion_persona = (0, 0)
            if existe_campo_en_diccionario(data, 'geolocalizacion'):
                if existe_campo_en_diccionario(data['geolocalizacion'], 'x'):
                    geolocalizacion_persona = (data['geolocalizacion']['x'], data['geolocalizacion']['y'])

            caracteristicas = retornar_valor_campo_en_diccionario(data, 'caracteristicas')
            fecha_perdida = retornar_valor_campo_en_diccionario(data, 'fecha_de_perdida')
            barrio_nombre = retornar_valor_campo_en_diccionario(data, 'barrio_nombre')
            genero = retornar_valor_campo_en_diccionario(data, 'genero') # Hembra (0) / Macho (1)
            perro_nombre = retornar_valor_campo_en_diccionario(data, 'nombre')
            comportamiento = retornar_valor_campo_en_diccionario(data, 'comportamiento')
            datos_adicionales = retornar_valor_campo_en_diccionario(data, 'datos_adicionales')
            estado = retornar_valor_campo_en_diccionario(data, 'estado')
            
            request_lista_imagenes = list()
            lista_imagenes_recortadas_base64 = []
            
            # Opción para recuperar lista de imágenes en arreglo de bytes
            if existe_campo_en_diccionario(data, 'lista_imagenes_bytes'):
                request_lista_imagenes = data['lista_imagenes_bytes']

                if len(request_lista_imagenes) == 0:
                    return {'mensaje':'Debe ingresar al menos una imagen (arreglo de base64).', 'codigo': 400},400
            
                # Detección y recorte de rostro del perro
                flag, list_img_paths, imagenes_recortadas_base64, respuesta = dog_face_cropper_service.recortar_imagenes_mascota(request_lista_imagenes)
                if flag:
                    lista_imagenes_recortadas_base64 = imagenes_recortadas_base64
                
            # Opción para recuperar lista de imágenes en arreglo de URL's
            if existe_campo_en_diccionario(data, 'lista_imagenes_url'):
                request_lista_imagenes = data['lista_imagenes_url']

                if len(request_lista_imagenes) == 0:
                    return {'mensaje':'Debe ingresar al menos una imagen (URL de imagen).', 'codigo': 400},400
                
                # Detección y recorte de rostro del perro
                flag, list_img_paths, imagenes_recortadas_base64, respuesta = dog_face_cropper_service.obtener_imagenes_recortadas(request_lista_imagenes)
                lista_imagenes_recortadas_base64 = imagenes_recortadas_base64 if flag else []
                
            if lista_imagenes_recortadas_base64:
                # Se logró identificar rostros de perros en las imagenes
                try:
                    mascota_datos = Mascota(mascota_dueno_datos, geolocalizacion_persona, lista_imagenes_recortadas_base64, caracteristicas, fecha_perdida, 
                                                    barrio_nombre, genero, perro_nombre, comportamiento, datos_adicionales, estado)
                    respuesta = predict_data(list_img_paths, mascota_datos, azure_storage_cliente_mascotas)
                    
                    dict_respuesta = respuesta
                except Exception as e:
                    print('Hubo un error en la búsqueda de mascota ({}): {}'.format(datetime.now(), e))
                    return {'mensaje':'Hubo un error en la predicción.', 'codigo': 400},400

                # Registrar en base de datos la mascota
                flag, mensaje, datos_mascota = mascota_service.reportar_mascota_desaparecida(mascota_datos, azure_storage_cliente_mascotas, list_img_paths)
                
                if not flag:
                    return {'mensaje':'Hubo un error al reportar mascota desaparecida.', 'codigo': 500},500
                
                # Seteo de los valores a retornar
                full_file_name, file_name, label, id_denuncia = datos_mascota
                dict_mascota = {'id':id_denuncia,
                                'file_name':file_name,
                                'label':label,
                                'full_file_name':full_file_name}
                
                dict_respuesta.update({'mascota':dict_mascota,'codigo':200,'mensaje':"{} {}".format(str(mensaje),dict_respuesta['mensaje'])})

                flag, data_mascotas, mensaje = mascota_service.obtener_data_by_id(id_denuncia, azure_storage_cliente_mascotas)
                
                if data_mascotas:
                    if data_mascotas['list_encoded_string']:
                        dict_respuesta['list_encoded_string'] = data_mascotas['list_encoded_string']
                else:
                    dict_respuesta['codigo'] = 503
                dict_respuesta["imagenes_recortadas"] = [img_base64.decode("utf-8") for img_base64 in lista_imagenes_recortadas_base64]
                print('Fin de búsqueda de mascota ({}). Ingresaron {} imagen(es) y se recortó {} imagen(es).'.format(datetime.now(), len(request_lista_imagenes), len(lista_imagenes_recortadas_base64)))
                return app.response_class(
                    response=json.dumps(dict_respuesta, cls=NumpyValuesEncoder),
                    status=200,
                    mimetype='application/json'
                )
            
            return json.dumps(respuesta, cls=NumpyValuesEncoder),200
    except Exception as e:
        print('Hubo un error al identificar las mascotas más parecidas ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al identificar las mascotas más parecidas.', 'codigo': 503},503

@app.route('/mascotas/data', methods=['POST'])
def mascota_empadronar():
    dict_respuesta = {}
    print('Inicio de empadronar mascota: {}'.format(datetime.now()))
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 400},400
        else:
            # Datos del dueño
            dueno = retornar_valor_campo_en_diccionario(data, 'dueno')
            if not dueno is None:
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')  # Número telefónico de la persona que reportó desaparición
                email = retornar_valor_campo_en_diccionario(data['dueno'], 'email') # Correo electrónico de la persona que reportó desaparición
                contacto = retornar_valor_campo_en_diccionario(data['dueno'], 'contacto')  # Números de teléfonos asociados al perro desaparecido
                mascota_dueno_datos = MascotaDueno(identificador, email, contacto)
            
            geolocalizacion_persona = (0, 0)
            if existe_campo_en_diccionario(data, 'geolocalizacion'):
                if existe_campo_en_diccionario(data['geolocalizacion'], 'x'):
                    geolocalizacion_persona = (data['geolocalizacion']['x'], data['geolocalizacion']['y'])
            
            caracteristicas = retornar_valor_campo_en_diccionario(data, 'caracteristicas')
            fecha_perdida = retornar_valor_campo_en_diccionario(data, 'fecha_de_perdida')
            barrio_nombre = retornar_valor_campo_en_diccionario(data, 'barrio_nombre')
            genero = retornar_valor_campo_en_diccionario(data, 'genero') # Hembra (0) / Macho (1)
            perro_nombre = retornar_valor_campo_en_diccionario(data, 'nombre')
            comportamiento = retornar_valor_campo_en_diccionario(data, 'comportamiento')
            datos_adicionales = retornar_valor_campo_en_diccionario(data, 'datos_adicionales')
            estado = retornar_valor_campo_en_diccionario(data, 'estado')
            
            request_lista_imagenes = list()
            
            # Opción para recuperar lista de imágenes en arreglo de bytes
            if existe_campo_en_diccionario(data, 'lista_imagenes_bytes'):
                request_lista_imagenes = data['lista_imagenes_bytes']

                if len(request_lista_imagenes) == 0:
                    return {'mensaje':'Debe ingresar al menos una imagen (arreglo de base64).', 'codigo': 400},400

                # Detección y recorte de rostro del perro
                flag, list_img_paths, imagenes_recortadas_base64, respuesta = dog_face_cropper_service.recortar_imagenes_mascota(request_lista_imagenes)
                if flag:
                    lista_imagenes_recortadas_base64 = imagenes_recortadas_base64
                
            # Opción para recuperar lista de imágenes en arreglo de URL's
            if existe_campo_en_diccionario(data, 'lista_imagenes_url'):
                request_lista_imagenes = data['lista_imagenes_url']

                if len(request_lista_imagenes) == 0:
                    return {'mensaje':'Debe ingresar al menos una imagen (URL de imagen).', 'codigo': 400},400
                
                flag, list_img_paths, imagenes_recortadas_base64, respuesta = dog_face_cropper_service.obtener_imagenes_recortadas(request_lista_imagenes)
                lista_imagenes_recortadas_base64 = imagenes_recortadas_base64 if flag else []

            if lista_imagenes_recortadas_base64:
                # Se logró identificar rostros de perros en las imagenes
                try:
                    mascota_datos = Mascota(mascota_dueno_datos, geolocalizacion_persona, lista_imagenes_recortadas_base64, caracteristicas, fecha_perdida, 
                                                    barrio_nombre, genero, perro_nombre, comportamiento, datos_adicionales, estado)
                    flag, mensaje, datos = mascota_service.reportar_mascota_desaparecida(mascota_datos, azure_storage_cliente_mascotas, list_img_paths)

                    if not flag:
                        return {'mensaje':'Hubo un error al empadronar mascota.', 'codigo': 500},500
                    print("00000")
                    print(mensaje)
                    # Seteo de los valores a retornar
                    full_file_name, file_name, label, id_denuncia = datos
                    dict_respuesta = {'id':id_denuncia,
                                      'file_name':file_name,
                                      'label':label,
                                      'full_file_name':full_file_name,
                                      'codigo':200,
                                      'mensaje':'Se logró empadronar.'}
                    
                    flag, data_mascotas, mensaje = mascota_service.obtener_data_by_id(id_denuncia, azure_storage_cliente_mascotas)
                    if not flag:
                        dict_respuesta['codigo'] = 503
                    else:
                        dict_respuesta['list_encoded_string'] = data_mascotas['list_encoded_string']
                except Exception as e:
                    print('Hubo un error al empadronar la mascota ({}): {}'.format(datetime.now(), e))
                    return {'mensaje':'Hubo un error en el empadronamiento', 'codigo': 400},400
                
                print('Fin de empadronamiento de mascota ({}). Ingresaron {} imagen(es) y se recortó {} imagen(es).'.format(datetime.now(), len(request_lista_imagenes), len(imagenes_recortadas_base64)))
                return json.dumps(dict_respuesta, cls=NumpyValuesEncoder),200
            
            return json.dumps(respuesta, cls=NumpyValuesEncoder),200
    except Exception as e:
        print('Hubo un error al empadronar la mascota({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al empadronar la mascota', 'codigo': 503},503

@app.route('/mascotas', methods=['POST'])
def report():
    print('Inicio de reportar mascota desaparecida: {}'.format(datetime.now()))
    dict_respuesta = {}
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 400},400
        else:
            # Datos del dueño
            dueno = retornar_valor_campo_en_diccionario(data, 'dueno')
            if not dueno is None:
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')  # Número telefónico de la persona que reportó desaparición
                email = retornar_valor_campo_en_diccionario(data['dueno'], 'email') # Correo electrónico de la persona que reportó desaparición
                contacto = retornar_valor_campo_en_diccionario(data['dueno'], 'contacto')  # Números de teléfonos asociados al perro desaparecido
                mascota_dueno_datos = MascotaDueno(identificador, email, contacto)
            
            # Almacenar geolocalización como objeto
            geolocalizacion_persona = (0, 0)
            if existe_campo_en_diccionario(data, 'geolocalizacion'):
                if existe_campo_en_diccionario(data['geolocalizacion'], 'x'):
                    geolocalizacion_persona = (data['geolocalizacion']['x'], data['geolocalizacion']['y'])
            lista_imagenes_bytes = data['lista_imagenes_bytes']
            if lista_imagenes_bytes == None:
                return {'mensaje':'Debe ingresar al menos una imagen.', 'codigo': 400},400

            caracteristicas = data['caracteristicas']
            fecha_perdida = data['fecha_de_perdida'] if 'fecha_de_perdida' in data else ''
            barrio_nombre = retornar_valor_campo_en_diccionario(data, 'barrio_nombre')
            genero = retornar_valor_campo_en_diccionario(data, 'genero') # Hembra (0) / Macho (1)
            perro_nombre = retornar_valor_campo_en_diccionario(data, 'nombre')
            comportamiento = retornar_valor_campo_en_diccionario(data, 'comportamiento')
            datos_adicionales = retornar_valor_campo_en_diccionario(data, 'datos_adicionales')
            estado = retornar_valor_campo_en_diccionario(data, 'estado')
            
            mascota_datos = Mascota(mascota_dueno_datos, geolocalizacion_persona, lista_imagenes_bytes, caracteristicas, fecha_perdida, 
                                            barrio_nombre, genero, perro_nombre, comportamiento, datos_adicionales, estado)
            flag, mensaje, datos_mascota = mascota_service.reportar_mascota_desaparecida(mascota_datos, azure_storage_cliente_mascotas, None)
            
            if not flag:
                return {'mensaje':'Hubo un error al reportar mascota desaparecida.', 'codigo': 500},500
            
            # Seteo de los valores a retornar
            full_file_name, file_name, label, id_denuncia = datos_mascota
            dict_respuesta['id'] = id_denuncia
            dict_respuesta['file_name'] = file_name
            dict_respuesta['label'] = label
            dict_respuesta['full_file_name'] = full_file_name
            dict_respuesta['codigo'] = 200
            dict_respuesta['mensaje'] = mensaje
    except Exception as e:
        print('Hubo un error al reportar mascota desaparecida ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al reportar desaparición.', 'codigo': 503},503

    print('Fin de reportar mascota desaparecida: {}'.format(datetime.now()))
    return json.dumps(dict_respuesta, cls=NumpyValuesEncoder),200

@app.route('/mascotas/data', methods=['PUT'])
def update():
    print('Inicio de actualización de datos de mascota desaparecida: {}'.format(datetime.now()))
    dict_respuesta = {}
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 400},400
        else:
            # Actualización de datos de mascota
            id = data['id']
            
            # Datos del dueño
            dueno = retornar_valor_campo_en_diccionario(data, 'dueno')
            if not dueno is None:
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')  # Número telefónico de la persona que reportó desaparición
                email = retornar_valor_campo_en_diccionario(data['dueno'], 'email') # Correo electrónico de la persona que reportó desaparición
                contacto = retornar_valor_campo_en_diccionario(data['dueno'], 'contacto')  # Números de teléfonos asociados al perro desaparecido
            
            geolocalizacion_persona = (0, 0)
            if existe_campo_en_diccionario(data, 'geolocalizacion'):
                if existe_campo_en_diccionario(data['geolocalizacion'], 'x'):
                    geolocalizacion_persona = (data['geolocalizacion']['x'], data['geolocalizacion']['y'])
            caracteristicas = data['caracteristicas']
            fecha_perdida = data['fecha_de_perdida'] if 'fecha_de_perdida' in data else ''
            barrio_nombre = retornar_valor_campo_en_diccionario(data, 'barrio_nombre')
            genero = retornar_valor_campo_en_diccionario(data, 'genero') # Hembra (0) / Macho (1)
            perro_nombre = retornar_valor_campo_en_diccionario(data, 'nombre')
            comportamiento = retornar_valor_campo_en_diccionario(data, 'comportamiento')
            datos_adicionales = retornar_valor_campo_en_diccionario(data, 'datos_adicionales')
            estado = retornar_valor_campo_en_diccionario(data, 'estado')
            
            mascota_dueno_datos = MascotaDueno(identificador, email, contacto)
            mascota_datos = Mascota(mascota_dueno_datos, geolocalizacion_persona, None, caracteristicas, fecha_perdida, 
                                    barrio_nombre, genero, perro_nombre, comportamiento, datos_adicionales,
                                    estado=estado)
            
            flag, mensaje = mascota_service.actualizar_datos(id, mascota_datos)
            
            if not flag:
                dict_respuesta['codigo'] = 500
            else:
                dict_respuesta['codigo'] = 200
            dict_respuesta['mensaje'] = mensaje

            print('Fin de actualización de datos de mascota desaparecida: {}'.format(datetime.now()))
            return jsonify(dict_respuesta),dict_respuesta['codigo']
    except Exception as e:
        print('Hubo un error al actualizar datos de mascota desaparecida ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al actualizar datos de mascota.', 'codigo': 503},503

@app.route('/mascotas', methods=['DELETE'])
def delete():
    print('Inicio de eliminación de datos de mascota desaparecida: {}'.format(datetime.now()))
    dict_respuesta = {}
    try:
        data = request.json
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 400},400
        else:
            id = retornar_valor_campo_en_diccionario(data, 'id')
            label = retornar_valor_campo_en_diccionario(data, 'label')
            flag, mensaje = mascota_service.eliminar_mascota(id,label,azure_storage_cliente_mascotas)
        
            if not flag:
                dict_respuesta['codigo'] = 500
            else:
                dict_respuesta['codigo'] = 200
            dict_respuesta['mensaje'] = mensaje
    except Exception as e:
        print('Hubo un error al eliminar datos de mascota desaparecida ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al eliminar datos de mascota.', 'codigo': 503},503

    print('Fin de eliminación de datos de mascota desaparecida: {}'.format(datetime.now()))
    return json.dumps(dict_respuesta, cls=NumpyValuesEncoder),dict_respuesta['codigo']

@app.route('/mascotas', methods=['PUT'])
def found():
    print('Inicio de actualización de estado de mascota desaparecida a encontrada: {}'.format(datetime.now()))
    dict_respuesta = {}
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo': 500},500
        else:
            # Datos del dueño
            dueno = retornar_valor_campo_en_diccionario(data, 'dueno')
            if not dueno is None:
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')  # Número telefónico de la persona que reportó desaparición
                email = retornar_valor_campo_en_diccionario(data['dueno'], 'email') # Correo electrónico de la persona que reportó desaparición
                contacto = retornar_valor_campo_en_diccionario(data['dueno'], 'contacto')  # Números de teléfonos asociados al perro desaparecido
            
            if not existe_campo_en_diccionario(data, 'id'):
                return {'mensaje':'Debe enviar el número de denuncia.', 'codigo': 500},500

            id_denuncia = data['id']
            flag, mensaje = mascota_service.reportar_mascota_encontrada(id_denuncia)
            
            if not flag:
                dict_respuesta['codigo'] = 503
            else:
                dict_respuesta['codigo'] = 200
            dict_respuesta['mensaje'] = mensaje
            print('Fin de actualización de estado de mascota desaparecida a encontrada: {}'.format(datetime.now()))
            return jsonify(dict_respuesta),dict_respuesta['codigo']
    except Exception as e:
        print('Hubo un error al actualizar estado de mascota desaparecida a encontrada ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al actualizar estado de mascota desaparecida a encontrada.', 'codigo': 503},503

@app.route('/mascotas/ownerpets', methods=['POST'])
def ownerpets():
    print('Inicio de listar las mascotas de un dueño: {}'.format(datetime.now()))
    dict_respuesta = {}
    try:
        data = request.json
        
        if data == None:
            return {'mensaje':'No se identifico objetos dentro del payload.', 'codigo':500},500
        else:
            id_denuncia = retornar_valor_campo_en_diccionario(data, 'id')
            if id_denuncia is not None:
                id_denuncia = str(id_denuncia)
            
            identificador = None
            if existe_campo_en_diccionario(data, 'dueno'):
                identificador = retornar_valor_campo_en_diccionario(data['dueno'], 'identificador')
                if identificador is not None:
                    identificador = str(identificador)
            
            flag, data_mascotas, mensaje = mascota_service.obtener_data_by_id(id_denuncia, azure_storage_cliente_mascotas)
            
            if not flag:
                dict_respuesta['codigo'] = 503
            else:
                dict_respuesta['codigo'] = 200
                dict_respuesta['mascotas'] = data_mascotas
            dict_respuesta['mensaje'] = mensaje
            print('Fin de listar las mascotas de un dueño: {}'.format(datetime.now()))
            return json.dumps(dict_respuesta, cls=NumpyValuesEncoder),dict_respuesta['codigo']
    except Exception as e:
        print('Hubo un error al listar las mascotas de un dueño ({}): {}'.format(datetime.now(), e))
        return {'mensaje':'Hubo un error al obtener datos de la mascota.', 'codigo': 503},503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, threaded=True)