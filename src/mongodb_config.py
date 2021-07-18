import pymongo
from datetime import datetime
import pytz
from bson.objectid import ObjectId

from src.config import DB_URI, DB_NAME, DB_COLECCION, DISTANCIA_KILOMETROS
from src.util import obtener_valor_estado_mascota


class MongoDB_Config():

    client = pymongo.MongoClient(DB_URI)
    db = client[DB_NAME]
    
    def __init__(self):
        pass
    
    def obtener_mascotas_reportadas(self):
        print('Inicio obtener data mascotas de base de datos ({})'.format(datetime.now()))
        try:
            lista = list(self.db[DB_COLECCION].find(
                # La búsqueda no posee filtros
                {},
                # Consulta retorna sólo los campos con valor 1
                {'file_name':1, 'label':1, 'list_encoded_string':1, '_id':0}))
            print('Cantidad de registros {}'.format(len(lista)))
            print('Fin obtener data mascotas de base de datos ({})'.format(datetime.now()))
            return lista
        except Exception as e:
            print('Hubo un error en obtener data mascotas de base de datos ({}): {}'.format(datetime.now(), e))
            return list()
    
    def obtener_mascotas_perdidas(self, geolocalizacion_persona, estado):
        '''
        Valores de estado:
        - 1: perdido (persona que perdió su perro)
        - 2: encontrado (persona encuentra un perro en la calle)
        - 3: baja logica  (cuando el perro hizo el match)
        - 0: empadronado
        '''
        print('Inicio obtener data mascotas de base de datos ({})'.format(datetime.now()))
        try:
            try:
                estado_aux = obtener_valor_estado_mascota(estado)
                
                filtro = {'estado': estado_aux}
                
                lista = list(self.db[DB_COLECCION].find(
                    # La búsqueda posee filtros
                    filtro,
                    # Consulta retorna sólo los campos con valor 1
                    {'file_name':1, 'label':1, 'list_encoded_string':1, '_id':0}))
                print('Cantidad de registros {}'.format(len(lista)))
                print('Fin obtener data mascotas de base de datos ({})'.format(datetime.now()))
                return lista
            except Exception as e:
                print('Hubo un error al buscar mascotas en base de datos ({}): {}'.format(datetime.now(), e))
                return list()
        except Exception as e:
            print('Hubo un error en obtener data mascotas de base de datos ({}): {}'.format(datetime.now(), e))
            return list()

    def obtener_mascotas_reportadas_por_geolocalizacion(self, geolocalizacion_persona, estado):
        print('Inicio obtener data mascotas de base de datos ({})'.format(datetime.now()))
        try:
            x, y = geolocalizacion_persona
            radio_kilometros = DISTANCIA_KILOMETROS
            
            if DISTANCIA_KILOMETROS is None:
                radio_kilometros = 1
            radio = 0.00918252 * int(radio_kilometros)
            longitud_rango_inferior = (-1 * radio) + x
            longitud_rango_superior = radio + x
            latitud_rango_inferior = (-1 * radio) + y
            latitud_rango_superior = radio + y
            
            try:
                print('Longitud: Mayor que {}. Menor que {}'.format(longitud_rango_inferior, longitud_rango_superior))
                print('Latitud: Mayor que {}. Menor que {}'.format(latitud_rango_inferior, latitud_rango_superior))
                
                filtro = {'ubicacion.x': {'$gte':longitud_rango_inferior, '$lte':longitud_rango_superior}, 
                    'ubicacion.y': {'$gte':latitud_rango_inferior, '$lte':latitud_rango_superior},
                    'estado': obtener_valor_estado_mascota(estado) }
                
                lista = list(self.db[DB_COLECCION].find(
                    # La búsqueda posee filtros
                    filtro,
                    # Consulta retorna sólo los campos con valor 1
                    {'file_name':1, 'label':1, 'list_encoded_string':1, '_id':0}))
                print('Cantidad de registros {}'.format(len(lista)))
                print('Fin obtener data mascotas de base de datos ({})'.format(datetime.now()))
                return lista
            except Exception as e:
                print('Hubo un error al buscar por ubicación latitud y longitud de las mascotas en base de datos ({}): {}'.format(datetime.now(), e))
                return list()
        except Exception as e:
            print('Hubo un error en obtener data mascotas de base de datos ({}): {}'.format(datetime.now(), e))
            return list()

    def obtener_mascota(self, label):
        '''
        Obtiene los datos de la mascota a partir de la etiqueta label
        '''
        print('Inicio obtener data mascota {} de base de datos ({})'.format(label, datetime.now()))
        try:
            mascota = self.db[DB_COLECCION].find_one(
                # Búsqueda por campo label
                {'label':label}
                )
            print('Fin obtener data mascota {} de base de datos ({})'.format(label, datetime.now()))
            if mascota:
                mascota['id'] = str(mascota['_id'])
                del mascota['_id']
                return True, mascota, None
            return False, None, None
        except Exception as e:
            mensaje = 'Hubo un error en obtener data mascota de base de datos'
            print('Hubo un error. {} ({}): {}'.format(mensaje, datetime.now(), e))
            return False, None, mensaje

    def obtener_mascota_by_id(self, id):
        '''
        Obtiene los datos de la mascota a partir del ID
        '''
        print('Inicio obtener data mascota {} de base de datos ({})'.format(id, datetime.now()))
        try:
            mascota = self.db[DB_COLECCION].find_one({'_id': ObjectId(id)})
            print('Fin obtener data mascota {} de base de datos ({})'.format(id, datetime.now()))
            if mascota:
                mascota['id'] = str(mascota['_id'])
                del mascota['_id']
                mascota['list_encoded_string'] = [encoded_string.decode("utf-8") for encoded_string in mascota['list_encoded_string']]
                return True, mascota, 'Se encontró mascota con la denuncia ingresada.'
            return False, None, 'No se encontró mascota con la denuncia ingresada.'
        except Exception as e:
            mensaje = 'Hubo un error en obtener data mascota de base de datos'
            print('Hubo un error. {} ({}): {}'.format(mensaje, datetime.now(), e))
            return False, None, mensaje

    def obtener_mascotas(self, dueno_identificador):
        '''
        Obtiene las mascotas reportadas a partir de un identificador del dueño
        '''
        print('Inicio obtener data mascota del dueño identificado con {} ({})'.format(dueno_identificador, datetime.now()))
        try:
            mascotas = list(self.db[DB_COLECCION].find(
                # Búsqueda por campo dueno.identificador
                {'dueno.identificador':dueno_identificador}
                ))
            print('Fin obtener data mascota {} de base de datos ({})'.format(dueno_identificador, datetime.now()))
            
            if len(mascotas) == 0:
                return True, [], 'No se encontraron mascotas reportadas con el identificador.'
            lista_mascotas = list()
            for mascota in mascotas:
                if mascota:
                    mascota['id'] = str(mascota['_id'])
                    del mascota['_id']
                    mascota['list_encoded_string'] = [encoded_string.decode("utf-8") for encoded_string in mascota['list_encoded_string']]
                    lista_mascotas.append(mascota)
            return True, lista_mascotas, '{} mascota(s) encontradas.'.format(len(lista_mascotas))
        except Exception as e:
            mensaje = 'Hubo un error en obtener las mascotas de base de datos que fueron reportadas por el dueño'
            print('Hubo un error. {} ({}): {}'.format(mensaje, datetime.now(), e))
            return False, None, mensaje
    
    def registrar_mascota_reportada(self, list_encoded_string, full_file_name, image_path, label, caracteristicas, ubicacion, fecha_perdida, 
                barrio_nombre, genero, nombre, comportamiento, datos_adicionales, estado, dueno):
        print('Inicio obtener data mascotas de base de datos ({})'.format(datetime.now()))
        try:
            timestamp_registro = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
            
            identificador = self.db[DB_COLECCION].insert_one({
                'list_encoded_string':list_encoded_string, 
                'file_name':image_path,
                'full_file_name':full_file_name,
                'label':label,
                'caracteristicas':caracteristicas,
                'ubicacion': {'x':ubicacion[0], 'y':ubicacion[1]},
                'fecha_perdida':fecha_perdida,
                'timestamp_registro':timestamp_registro,
                'barrio_nombre':barrio_nombre, 
                'genero':genero,
                'nombre':nombre, 
                'comportamiento':comportamiento,
                'datos_adicionales':datos_adicionales,
                'estado':estado,
                'dueno': {'identificador':dueno.identificador, 'email':dueno.email, 'contacto':dueno.contacto}})
            identificador = str(identificador.inserted_id)
            print('Fin de obtener data mascotas de base de datos ({})'.format(datetime.now()))
            return True, 'Se logró registrar mascota como desaparecida.', identificador
        except Exception as e:
            print('Hubo un error al registrar mascota desaparecida en base de datos ({}): {}'.format(datetime.now(), e))
            return False, None, 0
    
    def actualizar_mascota(self, id, mascota):
        print('Inicio actualizar datos de mascota en base de datos ({})'.format(datetime.now()))
        try:
            self.db[DB_COLECCION].update_one({
                    '_id': ObjectId(id)
                },{
                    '$set': {
                        'ubicacion': {'x':mascota.geolocalizacion_reportado[0], 'y':mascota.geolocalizacion_reportado[1]},
                        'caracteristicas': mascota.caracteristicas,
                        'fecha_perdida': mascota.fecha_perdida,
                        'barrio_nombre': mascota.barrio_nombre, 
                        'genero': mascota.genero,
                        'nombre': mascota.nombre, 
                        'comportamiento': mascota.comportamiento,
                        'datos_adicionales': mascota.datos_adicionales,
                        'estado': mascota.estado,
                        'dueno': mascota.dueno.__dict__
                    }
                }, upsert=False)
            
            print('Fin de actualizar data mascota de base de datos ({})'.format(datetime.now()))
            return True, 'Se logró actualizar datos de mascota.'
        except Exception as e:
            print('Hubo un error al actualizar datos de mascota en base de datos ({}): {}'.format(datetime.now(), e))
            return False, 'Hubo un error al actualizar datos de mascota en base de datos.'
    
    def eliminar_mascota(self, id=None, label=None):
        print('Inicio eliminar mascota de base de datos ({})'.format(datetime.now()))
        try:
            nombre_carpeta = None
            if id is not None:
                mascota = self.db[DB_COLECCION].find_one(
                    # Búsqueda por campo _id
                    {'_id': ObjectId(id)}
                )
                
                nombre_carpeta = mascota['label']
                
                self.db[DB_COLECCION].delete_one(
                    {'_id': ObjectId(id)}
                )
            if label is not None:
                mascota = self.db[DB_COLECCION].find_one(
                    # Búsqueda por campo label
                    {'label': label}
                )
                
                nombre_carpeta = mascota['label']
                
                self.db[DB_COLECCION].delete_one(
                    {'label': label}
                )
            print('Fin de eliminar data de mascota de base de datos ({})'.format(datetime.now()))
            return True, 'Se logró eliminar data de mascota.', nombre_carpeta
        except Exception as e:
            print('Hubo un error al eliminar data de mascota en base de datos ({}): {}'.format(datetime.now(), e))
            return False, 'Error al eliminar mascota en base de datos.', None

    def encontrar_mascota(self, id):
        print('Inicio actualizar data de mascota encontrada en base de datos ({})'.format(datetime.now()))
        try:
            # Consultar si existe registro con el ID
            flag_buscar = self.db[DB_COLECCION].find_one(
                    {'_id': ObjectId(id)},
                    # Consulta retorna sólo los campos con valor 1
                    {'file_name':1, 'label':1, '_id':0})
            if flag_buscar is None:
                return False, 'Número de denuncia no existe.', None
            
            flag_validar = self.db[DB_COLECCION].find_one(
                    {'_id': ObjectId(id), 'estado': 3},
                    # Consulta retorna sólo los campos con valor 1
                    {'file_name':1, 'label':1, '_id':0})
            if flag_validar is not None:
                return False, 'El perro ya fue encontrado.', None
            
            timestamp_encontrado = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
            
            flag_update = self.db[DB_COLECCION].update_one({
                    '_id': ObjectId(id)
                },{
                    '$set': {
                        'estado': 3,
                        'timestamp_encontrado': timestamp_encontrado
                    }
                }, upsert=False)
            
            mascota = self.db[DB_COLECCION].find_one({'_id': ObjectId(id)})
            label = mascota['label']
            
            print('Fin de actualizar data de mascota encontrada en base de datos ({})'.format(datetime.now()))
            return True, 'Se logró actualizar data de mascota encontrada.', label
        except Exception as e:
            mensaje = 'Hubo un error al actualizar data de mascota encontrada en base de datos'
            print('{}} ({}): {}'.format(mensaje, datetime.now(), e))
            return False, mensaje, None