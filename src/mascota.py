class Mascota:
    def __init__(self, dueno, geolocalizacion_reportado, lista_imagenes_bytes, caracteristicas, fecha_perdida, 
        barrio_nombre, genero, nombre, comportamiento, datos_adicionales, estado=0, timestamp_registro=None, timestamp_encontrado=None):
        self.dueno = dueno
        self.geolocalizacion_reportado = geolocalizacion_reportado
        self.lista_imagenes_bytes = lista_imagenes_bytes
        self.caracteristicas = caracteristicas
        self.fecha_perdida = fecha_perdida
        self.barrio_nombre = barrio_nombre
        self.genero = genero # Hembra (0) / Macho (1)
        self.nombre = nombre
        self.comportamiento = comportamiento
        self.datos_adicionales = datos_adicionales
        self.estado = estado
        self.timestamp_registro = timestamp_registro
        self.timestamp_encontrado = timestamp_encontrado
