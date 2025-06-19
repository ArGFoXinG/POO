from peewee import *
# from datetime import date # No la necesitamos si las fechas son CharField

# Configuración de la base de datos SQLite
# Conecta a la base de datos 'obras_urbanas.db'. Si no existe, la crea.
db = SqliteDatabase('obras_urbanas.db')

# Clase base para nuestros modelos
class BaseModel(Model):
    class Meta:
        database = db # Conecta el modelo a la base de datos

# 5. La clase "Obra" con sus atributos y nuevos métodos de instancia
class Obra(BaseModel):
    # Atributos de la tabla 'obras' (columnas)
    id = AutoField() # Clave primaria autoincremental
    nombre = CharField(null=True) # Nombre de la obra, puede ser nulo
    etapa = CharField(null=True) # Etapa actual (ej: "Proyecto", "Contratacion", "En Ejecucion", "Finalizada")
    tipo_obra = CharField(null=True)
    area_responsable = CharField(null=True)
    estado = CharField(null=True) # Estado de la obra (ej: "Activa", "Cancelada", "Suspendida")
    comuna = IntegerField(null=True)
    barrio = CharField(null=True)
    latitud = FloatField(null=True)
    longitud = FloatField(null=True)
    fecha_inicio = CharField(null=True) # Guardamos como texto para simplificar
    fecha_fin_inicial = CharField(null=True) # Guardamos como texto para simplificar
    # Nuevos campos para los métodos, si es necesario.
    # Porcentaje de avance: lo añadimos aquí para que el método e. lo use.
    porcentaje_avance = IntegerField(null=True, default=0)
    # Plazo en meses: para el método f.
    plazo_meses = IntegerField(null=True)
    # Cantidad de mano de obra: para el método g.
    mano_obra = IntegerField(null=True)
    tipo_contratacion = CharField(null=True) # Tipo de contratación de la obra
    nro_contratacion = CharField(null=True) # Número de contratación
    empresa_adjudicada = CharField(null=True) # Nombre de la empresa a la que se adjudicó
    nro_expediente = CharField(null=True) # Número de expediente asociado a la obra


    # Método para representar el objeto (útil para imprimir)
    def __str__(self):
        return f"Obra ID: {self.id}, Nombre: {self.nombre}, Etapa: {self.etapa}, Estado: {self.estado}"

    # 5.a. nuevo_proyecto()
    def nuevo_proyecto(self):
        """
        Marca la obra como 'Nuevo Proyecto'.
        Inicializa etapa a 'Proyecto' y porcentaje_avance a 0.
        """
        self.etapa = "Proyecto"
        self.porcentaje_avance = 0
        self.estado = "Activa" # Una obra nueva suele estar activa
        self.save() # Guarda los cambios en la base de datos
        print(f"Obra '{self.nombre}' (ID: {self.id}) marcada como NUEVO PROYECTO. Etapa: {self.etapa}")

    # 5.b. iniciar_contratacion()
    def iniciar_contratacion(self, tipo_contratacion: str = None, nro_contratacion: str = None):
        """
        Cambia la etapa de la obra a 'Contratacion' y asigna el tipo y número de contratación.
        """
        self.etapa = "Contratacion"
        self.tipo_contratacion = tipo_contratacion
        self.nro_contratacion = nro_contratacion
        self.save() # Guarda los cambios en la base de datos
        print(f"Obra '{self.nombre}' (ID: {self.id}) inició etapa de CONTRATACIÓN.")
        print(f"  Tipo Contratación: {self.tipo_contratacion}, Nro Contratación: {self.nro_contratacion}")

    # 5.c. adjudicar_obra()
    def adjudicar_obra(self, empresa: str = None, nro_expediente: str = None):
        """
        Marca la obra como 'Adjudicada' y asigna la empresa y número de expediente.
        """
        self.etapa = "Adjudicada"
        self.empresa_adjudicada = empresa
        self.nro_expediente = nro_expediente
        self.save() # Guarda los cambios en la base de datos
        print(f"Obra '{self.nombre}' (ID: {self.id}) ha sido ADJUDICADA.")
        print(f"  Empresa Adjudicada: {self.empresa_adjudicada}, Nro Expediente: {self.nro_expediente}")

    # 5.d. iniciar_obra()
    def iniciar_obra(self):
        """
        Marca la obra como 'En Ejecucion'.
        También podría fijar la fecha de inicio si el campo `fecha_inicio` no está seteado.
        """
        self.etapa = "En Ejecucion"
        # Puedes añadir una lógica para setear la fecha de inicio si es la primera vez que se inicia
        # if not self.fecha_inicio:
        #     self.fecha_inicio = date.today().isoformat() # Requiere 'from datetime import date'
        self.save()
        print(f"Obra '{self.nombre}' (ID: {self.id}) INICIÓ EJECUCIÓN. Etapa: {self.etapa}")

    # 5.e. actualizar_porcentaje_avance()
    def actualizar_porcentaje_avance(self, porcentaje: int):
        """
        Actualiza el porcentaje de avance de la obra.
        El porcentaje debe ser un entero entre 0 y 100.
        """
        if 0 <= porcentaje <= 100:
            self.porcentaje_avance = porcentaje
            self.save()
            print(f"Obra '{self.nombre}' (ID: {self.id}) - Porcentaje de avance actualizado: {self.porcentaje_avance}%")
        else:
            print(f"Error: El porcentaje de avance ({porcentaje}) debe ser entre 0 y 100.")

    # 5.f. incrementar_plazo()
    def incrementar_plazo(self, meses_a_sumar: int):
        """
        Incrementa el plazo de la obra en la cantidad de meses especificada.
        Si el plazo_meses es nulo, lo inicializa.
        """
        if meses_a_sumar > 0:
            if self.plazo_meses is None:
                self.plazo_meses = meses_a_sumar # Si no tiene plazo, lo establece
                print(f"Obra '{self.nombre}' (ID: {self.id}) - Plazo inicial establecido en {self.plazo_meses} meses.")
            else:
                self.plazo_meses += meses_a_sumar
                print(f"Obra '{self.nombre}' (ID: {self.id}) - Plazo incrementado en {meses_a_sumar} meses. Nuevo plazo total: {self.plazo_meses} meses.")
            self.save()
        else:
            print("Error: Los meses a sumar deben ser un número positivo.")

    # 5.g. incrementar_mano_obra()
    def incrementar_mano_obra(self, cantidad_adicional: int):
        """
        Incrementa la cantidad de mano de obra de la obra.
        Si mano_obra es nulo, lo inicializa.
        """
        if cantidad_adicional > 0:
            if self.mano_obra is None:
                self.mano_obra = cantidad_adicional # Si no tiene, lo establece
                print(f"Obra '{self.nombre}' (ID: {self.id}) - Mano de obra inicial establecida en {self.mano_obra} personas.")
            else:
                self.mano_obra += cantidad_adicional
                print(f"Obra '{self.nombre}' (ID: {self.id}) - Mano de obra incrementada en {cantidad_adicional} personas. Nueva cantidad: {self.mano_obra} personas.")
            self.save()
        else:
            print("Error: La cantidad adicional de mano de obra debe ser un número positivo.")

    # 5.h. finalizar_obra()
    def finalizar_obra(self):
        """
        Marca la obra como 'Finalizada'.
        Establece el porcentaje_avance a 100 y la etapa a 'Finalizada'.
        También podría fijar la fecha de fin real si el campo `fecha_fin_real` existiera.
        """
        self.etapa = "Finalizada"
        self.estado = "Finalizada" # Un estado más final que 'Activa'
        self.porcentaje_avance = 100
        # if not self.fecha_fin_real: # Si tuvieras un campo fecha_fin_real en el modelo
        #     self.fecha_fin_real = date.today().isoformat()
        self.save()
        print(f"Obra '{self.nombre}' (ID: {self.id}) FINALIZADA. Etapa: {self.etapa}, Avance: {self.porcentaje_avance}%")

    # 5.i. rescindir_obra()
    def rescindir_obra(self):
        """
        Marca la obra como 'Rescindida' (cancelada).
        Establece el estado a 'Rescindida'.
        """
        self.estado = "Rescindida"
        self.etapa = "Rescindida" # La etapa también reflejaría esto
        self.save()
        print(f"Obra '{self.nombre}' (ID: {self.id}) RESCINDIDA. Estado: {self.estado}")