from peewee import *
from datetime import datetime

# Configuramos la base de datos SQLite
db = SqliteDatabase('obras_urbanas.db')

# Modelo base que enlaza todos los modelos a la base de datos
class BaseModel(Model):
    class Meta:
        database = db

# Tabla para tipos de obra (por ejemplo: Escuela, Hospital)
class TipoObra(BaseModel):
    nombre = CharField(unique=True)

# Tabla para áreas responsables (por ejemplo: Ministerio de Educación)
class AreaResponsable(BaseModel):
    nombre = CharField(unique=True)

# Tabla para barrios
class Barrio(BaseModel):
    nombre = CharField(unique=True)

# Modelo principal de Obra
class Obra(BaseModel):
    entorno = CharField(null=True)
    nombre = CharField()
    etapa = CharField(default='Proyecto')
    descripcion = TextField(null=True)
    beneficiarios = TextField(null=True)
    compromiso = TextField(null=True)
    destacada = BooleanField(default=False, null=True)
    ba_elige = BooleanField(default=False)
    enlace = CharField(null=True)

    tipo = ForeignKeyField(TipoObra, backref='obras', null=True)
    area = ForeignKeyField(AreaResponsable, backref='obras', null=True)
    barrio = ForeignKeyField(Barrio, backref='obras', null=True)

    empresa_licitacion = CharField(null=True)
    nro_contratacion = CharField(null=True)
    cuit_contratista = CharField(null=True)
    contratacion_tipo = CharField(null=True)
    nro_expediente = CharField(null=True)

    monto_contrato = FloatField(null=True)
    fuente_financiamiento = CharField(null=True)
    porcentaje_avance = IntegerField(default=0)

    fecha_inicio = DateField(null=True)
    fecha_fin_inicial = DateField(null=True)
    plazo_meses = IntegerField(null=True)

    comuna = CharField(null=True)
    direccion = CharField(null=True)
    latitud = FloatField(null=True)
    longitud = FloatField(null=True)

    mano_obra = IntegerField(null=True)
    creado_en = DateTimeField(default=datetime.now)

    def nuevo_proyecto(self, tipo_obra_obj, area_responsable_obj, barrio_obj):
        self.etapa = "Proyecto"
        self.tipo = tipo_obra_obj
        self.area = area_responsable_obj
        self.barrio = barrio_obj
        self.save()
        print(f"La obra '{self.nombre}' ha sido creada en la etapa: {self.etapa}")

    def iniciar_contratacion(self, tipo_contratacion, nro_contratacion):
        self.etapa = "En Contratacion"
        self.contratacion_tipo = tipo_contratacion
        self.nro_contratacion = nro_contratacion
        self.save()
        print(f"La obra '{self.nombre}' ha pasado a la etapa: {self.etapa}. Número de contratación: {self.nro_contratacion}")

    def adjudicar_obra(self, empresa_licitacion, nro_expediente):
        self.etapa = "Adjudicada"
        self.empresa_licitacion = empresa_licitacion
        self.nro_expediente = nro_expediente
        self.save()
        print(f"La obra '{self.nombre}' ha pasado a la etapa: {self.etapa}. Empresa: {self.empresa_licitacion}")

    def iniciar_obra(self, destacada_val, fecha_inicio_val, fecha_fin_inicial_val, fuente_financiamiento_val, mano_obra_val):
        self.etapa = "En Ejecucion"
        self.destacada = destacada_val
        self.fecha_inicio = fecha_inicio_val
        self.fecha_fin_inicial = fecha_fin_inicial_val
        self.fuente_financiamiento = fuente_financiamiento_val
        self.mano_obra = mano_obra_val
        self.save()
        print(f"La obra '{self.nombre}' ha pasado a la etapa: {self.etapa}. Inicio: {self.fecha_inicio}")

    def actualizar_porcentaje_avance(self, porcentaje):
        self.porcentaje_avance = porcentaje
        self.save()
        print(f"La obra '{self.nombre}' ha actualizado su porcentaje de avance a: {self.porcentaje_avance}%")

    def incrementar_plazo(self, meses):
        if self.plazo_meses is None:
            self.plazo_meses = 0
        self.plazo_meses += meses
        self.save()
        print(f"La obra '{self.nombre}' ha incrementado su plazo en {meses} meses. Nuevo plazo: {self.plazo_meses} meses.")

    def incrementar_mano_obra(self, cantidad):
        if self.mano_obra is None:
            self.mano_obra = 0
        self.mano_obra += cantidad
        self.save()
        print(f"La obra '{self.nombre}' ha incrementado su mano de obra en {cantidad}. Nueva mano de obra: {self.mano_obra}.")

    def finalizar_obra(self):
        self.etapa = "Finalizada"
        self.porcentaje_avance = 100
        self.save()
        print(f"La obra '{self.nombre}' ha pasado a la etapa: {self.etapa}. Porcentaje de avance: {self.porcentaje_avance}%")

    def rescindir_obra(self):
        self.etapa = "Rescindida"
        self.save()
        print(f"La obra '{self.nombre}' ha pasado a la etapa: {self.etapa}.")

    class Meta:
        database = db
        table_name = 'obras'
        indexes = ((('nombre', 'barrio'), True),)

    def inicializar_bd():
        """Inicializa la base de datos y crea las tablas si no existen."""
        db.connect()
        db.create_tables([TipoObra, AreaResponsable, Barrio, Obra], safe=True)
        print("Base de datos inicializada y tablas creadas.")
        db.close()