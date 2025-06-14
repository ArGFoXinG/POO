import pandas as pd  # Librería para trabajar con datos tipo tabla (como hojas de cálculo)
from modelo_orm import *  # Importamos las clases de la base de datos (modelo_orm.py)
from datetime import datetime  # Para trabajar con fechas
import peewee  # Librería ORM para manejar la base de datos

print(f"Versión de Peewee utilizada: {peewee.__version__}")  # Mostramos la versión actual de peewee


class GestionarObra:
    _db_initialized = False  # Variable para saber si ya inicializamos la base de datos

    @classmethod
    def conectar_db(cls):
        """Conecta con la base de datos si aún no está conectada."""
        if db.is_closed():
            try:
                db.connect()
            except OperationalError as e:
                print(f"Error de conexión a la base de datos: {e}")
            except Exception as e:
                print(f"Error inesperado al conectar a la base de datos: {e}")

    @classmethod
    def mapear_orm(cls):
        """Crea las tablas necesarias en la base de datos si no existen."""
        cls.conectar_db()
        try:
            db.create_tables([TipoObra, AreaResponsable, Barrio, Obra], safe=True)
            print("Estructura de la base de datos creada/actualizada correctamente.")
            cls._db_initialized = True
        except Exception as e:
            print(f"Error al crear las tablas de la base de datos: {e}")
        finally:
            db.close()

    @classmethod
    def extraer_datos(cls):
        """Lee los datos desde el archivo CSV."""
        try:
            with open('observatorio-de-obras-urbanas.csv', 'r', encoding='latin-1') as f:
                primera_linea = f.readline()
                print("Encabezados del CSV (crudos):", primera_linea.strip())

            df = pd.read_csv(
                'observatorio-de-obras-urbanas.csv',
                encoding='latin-1',
                delimiter=';',
                on_bad_lines='skip'
            )
            print("Columnas en el DataFrame (después del parseo):", df.columns.tolist())
            return df
        except Exception as e:
            print(f"Error al leer el archivo: {str(e)}")
            return None

    @classmethod
    def limpiar_datos(cls, df):
        """Limpia los datos eliminando errores, ajustando tipos y eliminando valores vacíos."""
        if df is not None:
            initial_rows = len(df)
            
            df.rename(columns={
                'area_responsable': 'area',
                'tipo': 'tipo_obra',
                'link_interno': 'enlace',
                'expediente-numero': 'nro_expediente',
                'financiamiento': 'fuente_financiamiento',
                'licitacion_oferta_empresa': 'empresa_licitacion',
                'fecha_fin_inicial': 'fecha_fin_inicial'
            }, inplace=True)

            cols_to_drop = [col for col in df.columns if 'Unnamed:' in col]
            df.drop(columns=cols_to_drop, inplace=True)

            df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'], errors='coerce').dt.date
            df['fecha_fin_inicial'] = pd.to_datetime(df['fecha_fin_inicial'], errors='coerce').dt.date

            if 'monto_contrato' in df.columns:
                df['monto_contrato'] = pd.to_numeric(
                    df['monto_contrato'].astype(str).str.replace('$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.'),
                    errors='coerce'
                )

            if 'destacada' in df.columns:
                df['destacada'] = df['destacada'].astype(str).str.lower().apply(lambda x: True if x == 'si' else False)
            if 'ba_elige' in df.columns:
                df['ba_elige'] = df['ba_elige'].astype(str).str.lower().apply(lambda x: True if x == 'si' else False)

            int_cols_to_fill = ['plazo_meses', 'porcentaje_avance', 'mano_obra', 'licitacion_anio']
            for col in int_cols_to_fill:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            df.dropna(subset=['nombre', 'barrio'], inplace=True)

            print(f"Datos limpiados. Cantidad de filas inicial: {initial_rows}. Después de la limpieza: {len(df)}")
            return df
        return None

    @classmethod
    def cargar_datos(cls):
        """Carga los datos limpios del CSV a la base de datos."""
        df = cls.extraer_datos()
        if df is None:
            print("No se pudieron cargar los datos")
            return

        df = cls.limpiar_datos(df)
        if df is None or df.empty:
            print("No hay datos para cargar después de la limpieza.")
            return

        print("Iniciando carga de datos en la base de datos...")
        cls.conectar_db()

        with db.atomic():
            for index, fila in df.iterrows():
                try:
                    tipo_obra_obj, _ = TipoObra.get_or_create(nombre=fila['tipo_obra'])
                    area_responsable_obj, _ = AreaResponsable.get_or_create(nombre=fila['area'])
                    barrio_obj, _ = Barrio.get_or_create(nombre=fila['barrio'])

                    obra_existente = Obra.get_or_none(Obra.nombre == fila['nombre'], Obra.barrio == barrio_obj)
                    if obra_existente:
                        print(f"Obra duplicada '{fila['nombre']}' en barrio '{fila['barrio']}'. Saltada.")
                        continue

                    Obra.create(
                        entorno=fila.get('entorno'),
                        nombre=fila.get('nombre'),
                        etapa=fila.get('etapa'),
                        descripcion=fila.get('descripcion'),
                        beneficiarios=fila.get('beneficiarios'),
                        compromiso=fila.get('compromiso'),
                        destacada=fila.get('destacada'),
                        ba_elige=fila.get('ba_elige'),
                        enlace=fila.get('enlace'),
                        tipo=tipo_obra_obj,
                        area=area_responsable_obj,
                        barrio=barrio_obj,
                        empresa_licitacion=fila.get('empresa_licitacion'),
                        nro_contratacion=fila.get('nro_contratacion'),
                        cuit_contratista=fila.get('cuit_contratista'),
                        contratacion_tipo=fila.get('contratacion_tipo'),
                        nro_expediente=fila.get('nro_expediente'),
                        monto_contrato=fila.get('monto_contrato'),
                        fuente_financiamiento=fila.get('fuente_financiamiento'),
                        porcentaje_avance=fila.get('porcentaje_avance'),
                        fecha_inicio=fila.get('fecha_inicio') if pd.notna(fila.get('fecha_inicio')) else None,
                        fecha_fin_inicial=fila.get('fecha_fin_inicial') if pd.notna(fila.get('fecha_fin_inicial')) else None,
                        plazo_meses=fila.get('plazo_meses'),
                        comuna=fila.get('comuna'),
                        direccion=fila.get('direccion'),
                        latitud=fila.get('lat'),
                        longitud=fila.get('lng'),
                        mano_obra=fila.get('mano_obra')
                    )
                except IntegrityError as e:
                    print(f"Error en fila {index+1}: {e}. Dato duplicado.")
                except KeyError as e:
                    print(f"Falta una columna: {str(e)} - Fila omitida. Index: {index+1}")
                    continue
                except Exception as e:
                    print(f"Error al procesar fila {index+1}: {e}. Fila omitida.")
                    continue
        db.close()
        print("Carga de datos completada.")
