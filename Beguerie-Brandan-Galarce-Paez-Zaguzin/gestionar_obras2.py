from abc import ABC, abstractmethod
import pandas as pd # Necesitamos importar pandas para trabajar con DataFrames
from modelo_orm import db, Obra
from peewee import fn
# Definimos la clase abstracta GestionarObra.
class GestionarObra(ABC):

    # a. Método para extraer datos del CSV
    @classmethod # Indicamos que es un método de clase. Lo llamamos con GestionarObra.extraer_datos()
    def extraer_datos(cls, nombre_archivo_csv='observatorio-de-obras-urbanas.csv'):
        """
        Extrae datos de un archivo CSV usando pandas y los carga en un DataFrame.
        Retorna el DataFrame de pandas.
        """
        try:
            # pd.read_csv lee el archivo CSV y lo convierte en un DataFrame.
            # Es la forma más simple de cargar datos desde un CSV.
            df = pd.read_csv(nombre_archivo_csv)
            print(f"Dataset '{nombre_archivo_csv}' extraído exitosamente. Total de registros: {len(df)}")
            return df
        except FileNotFoundError:
            # Si el archivo no se encuentra, mostramos un mensaje de error claro.
            print(f"Error: El archivo '{nombre_archivo_csv}' no se encontró.")
            print("Asegúrate de que esté en la misma carpeta que 'gestionar_obras.py'.")
            return None # Devolvemos None para indicar que hubo un error
        except Exception as e:
            # Capturamos cualquier otro error inesperado durante la lectura.
            print(f"Ocurrió un error al extraer los datos: {e}")
            return None
    
    @classmethod
    def conectar_db(cls):
        """
        Establece la conexión a la base de datos SQLite 'obras_urbanas.db'.
        """
        try:
            # Si la base de datos ya está abierta, no intentamos conectarnos de nuevo.
            # Esto previene errores y es más eficiente.
            if db.is_closed(): # 'is_closed()' es un método de Peewee para saber si la conexión está cerrada.
                db.connect() # 'connect()' abre la conexión a la base de datos.
                print("Conexión a la base de datos 'obras_urbanas.db' establecida.")
            else:
                print("La base de datos ya está conectada.")
        except Exception as e:
            # Capturamos cualquier error que pueda ocurrir durante la conexión.
            print(f"Error al conectar a la base de datos: {e}")
    
    @classmethod
    def mapear_orm(cls):
        """
        Crea la estructura de la base de datos (tablas y relaciones)
        utilizando el modelo ORM definido en 'modelo_orm.py'.
        """
        # Primero nos aseguramos de que la base de datos esté conectada
        cls.conectar_db() # Reutilizamos el método que ya definimos

        try:
            # db.create_tables([Obra]) es el método de Peewee.
            # Toma una lista de modelos (nuestra clase Obra) y crea
            # las tablas correspondientes en la base de datos si no existen.
            db.create_tables([Obra])
            print("Estructura de la base de datos (tabla 'obras') creada/verificada.")
        except Exception as e:
            print(f"Error al mapear el ORM y crear tablas: {e}")
        finally:
            # Es buena práctica cerrar la conexión de la base de datos
            # una vez que terminamos una operación, especialmente si no se va a usar de inmediato.
            # Verificamos si no está ya cerrada.
            if not db.is_closed():
                db.close()
                print("Conexión a la base de datos cerrada después de mapear ORM.")
        

    @classmethod
    def limpiar_datos(cls, df):
        """
        Realiza la limpieza de datos nulos y 'no accesibles' del DataFrame.
        Reemplaza valores comunes de "vacío" o "sin dato" por None.
        Intenta convertir a numérico si es posible para ciertas columnas.
        Retorna el DataFrame limpio.
        """
        if df is None or df.empty:
            print("No hay DataFrame para limpiar o está vacío.")
            return df

        print("Iniciando limpieza de datos simple...")

        # Valores comunes que representan datos faltantes o "no accesibles"
        # Los convertiremos a NaN de pandas para que sean tratados como nulos.
        valores_a_reemplazar = ['ND', '-', '', 'Sin Dato', 's/d', 'N/A']

        # Columnas en nuestro modelo Obra que vamos a limpiar y procesar
        columnas_a_procesar = [
            'nombre', 'etapa', 'tipo_obra', 'area_responsable', 'estado',
            'comuna', 'barrio', 'latitud', 'longitud',
            'fecha_inicio', 'fecha_fin_inicial'
        ]

        for col in columnas_a_procesar:
            if col in df.columns:
                # Primero: Reemplazar los valores problemáticos por el valor nulo de Pandas (pd.NA)
                df[col] = df[col].replace(valores_a_reemplazar, pd.NA)

                # Segundo: Intentar convertir a tipo numérico para 'comuna', 'latitud', 'longitud'
                # Si la conversión falla, pondrá NaN.
                if col in ['comuna', 'latitud', 'longitud']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Aseguramos que los enteros puedan tener nulos
                    if col == 'comuna':
                         df[col] = df[col].astype('Int64', errors='ignore') # 'Int64' permite enteros con NaN

                # Tercero: Convertir cualquier valor nulo de Pandas (pd.NA o NaN) a None.
                # Peewee guardará None como NULL en la base de datos.
                df[col] = df[col].where(pd.notna(df[col]), None)
            else:
                print(f"Advertencia: La columna '{col}' del modelo no se encontró en el CSV.")

        print("Limpieza de datos completada.")
        return df
    
    @classmethod
    def cargar_datos(cls, df):
        """
        Persiste los datos limpios del DataFrame en la tabla 'obras' de la base de datos SQLite.
        Utiliza el método de clase Model.create() de Peewee.
        """
        if df is None or df.empty:
            print("No hay datos en el DataFrame para cargar o está vacío.")
            return

        print(f"Cargando {len(df)} registros en la base de datos. Esto puede llevar un momento...")

        cls.conectar_db() # Nos aseguramos de estar conectados

        try:
            # Iteramos fila por fila del DataFrame
            for index, row in df.iterrows():
                try:
                    # Mapeamos los nombres de las columnas del CSV a los atributos del modelo Obra.
                    # ¡ESTO ES CRÍTICO Y USA TUS NOMBRES EXACTOS DEL CSV!
                    # Asegúrate de que los atributos de tu modelo Obra en modelo_orm.py
                    # están definidos para recibir estos valores (Charfield, IntField, FloatField, etc.)
                    Obra.create(
                        nombre=row.get('nombre', None), # Columna 'nombre' en CSV
                        etapa=row.get('etapa', None),   # Columna 'etapa' en CSV
                        tipo_obra=row.get('tipo', None), # Columna 'tipo' en CSV -> a 'tipo_obra' en modelo
                        area_responsable=row.get('area_responsable', None), # Columna 'area_responsable' en CSV
                        # 'estado' no parece estar en tu CSV. Si no existe, Peewee pondrá None.
                        estado=None, # Asignamos None si no hay una columna 'estado' en el CSV
                        comuna=row.get('comuna', None), # Columna 'comuna' en CSV
                        barrio=row.get('barrio', None), # Columna 'barrio' en CSV
                        latitud=row.get('lat', None), # Columna 'lat' en CSV -> a 'latitud' en modelo
                        longitud=row.get('lng', None), # Columna 'lng' en CSV -> a 'longitud' en modelo
                        fecha_inicio=row.get('fecha_inicio', None), # Columna 'fecha_inicio' en CSV
                        fecha_fin_inicial=row.get('fecha_fin_inicial', None) # Columna 'fecha_fin_inicial' en CSV
                    )
                except KeyError as ke:
                    # Si una columna no existe en el DataFrame, lo indicamos
                    print(f"Error: Columna '{ke}' faltante en el CSV para el registro {index}. Saltando este registro.")
                except Exception as e:
                    # Para cualquier otro error al crear un registro, lo indicamos
                    # Intentamos obtener el nombre de la obra para el mensaje de error si es posible
                    obra_nombre_error = row.get('nombre', 'N/D')
                    print(f"Error al cargar el registro {index} (obra: {obra_nombre_error}). Error: {e}. Saltando este registro.")

            print("Carga de datos completada exitosamente.")

        except Exception as e:
            print(f"Error general durante la carga de datos: {e}")
        finally:
            if not db.is_closed():
                db.close()
                print("Conexión a la base de datos cerrada después de cargar datos.")

    @classmethod
    def nueva_obra(cls):
        """
        Permite al usuario ingresar los datos de una nueva obra por teclado
        y la persiste en la base de datos.
        Retorna la nueva instancia de Obra creada.
        """
        print("\n--- Ingrese los datos de la nueva obra ---")

        # 1. Recopilar todos los valores como texto.
        # Los campos están ordenados según tu modelo Obra.
        nombre = input("Nombre de la obra (requerido): ").strip()
        etapa = input("Etapa (Ej: En proceso, Finalizada): ").strip()
        tipo_obra = input("Tipo de obra (Ej: Vivienda, Salud) [Será validado si ya existe]: ").strip()
        area_responsable = input("Área responsable [Será validado si ya existe]: ").strip()
        estado = input("Estado de la obra: ").strip()
        comuna_str = input("Comuna (número entero, dejar vacío si no aplica): ").strip()
        barrio = input("Barrio [Será validado si ya existe]: ").strip()
        latitud_str = input("Latitud (número decimal, ej: -34.6, dejar vacío si no aplica): ").strip()
        longitud_str = input("Longitud (número decimal, ej: -58.4, dejar vacío si no aplica): ").strip()
        fecha_inicio = input("Fecha de inicio (YYYY-MM-DD, dejar vacío si no aplica): ").strip()
        fecha_fin_inicial = input("Fecha de fin inicial (YYYY-MM-DD, dejar vacío si no aplica): ").strip()

        # 2. Conectar a la base de datos para realizar las validaciones y el guardado.
        cls.conectar_db()
        try:
            # 3. Realizar validaciones de "tablas relacionadas" (existencia en Obra)
            #    Esto simula la búsqueda de FK de forma sencilla.
            def validar_existencia(campo_modelo, valor_ingresado):
                if not valor_ingresado: # Si el usuario no ingresó nada, es válido (se guardará como NULL)
                    return None # Retornamos None para que se guarde como NULL

                # Buscar si el valor ingresado YA existe en la base de datos en alguna obra.
                # Usamos .where() para filtrar y .count() para saber si hay resultados.
                existe = Obra.select().where(getattr(Obra, campo_modelo) == valor_ingresado).count() > 0
                if existe:
                    print(f"'{valor_ingresado}' para {campo_modelo.replace('_', ' ')} encontrado en datos existentes.")
                    return valor_ingresado
                else:
                    print(f"'{valor_ingresado}' para {campo_modelo.replace('_', ' ')} NO encontrado en datos existentes.")
                    while True:
                        confirmacion = input(f"¿Desea guardar '{valor_ingresado}' de todas formas como nuevo valor (s/n)? ").lower()
                        if confirmacion == 's':
                            return valor_ingresado
                        elif confirmacion == 'n':
                            # Si el usuario dice 'n', le pedimos que ingrese de nuevo
                            return None # Indicamos que se necesita re-ingresar o se asignará None si no lo hace.
                        else:
                            print("Opción inválida. Ingrese 's' o 'n'.")

            # Aplicar la validación simplificada
            # Usamos los nombres de los atributos del modelo Obra
            tipo_obra_validado = validar_existencia('tipo_obra', tipo_obra)
            area_responsable_validado = validar_existencia('area_responsable', area_responsable)
            barrio_validado = validar_existencia('barrio', barrio)

            # Si el usuario eligió no guardar un valor nuevo y se le pidió re-ingresar,
            # y no lo hizo, el valor resultante de validar_existencia sería None.
            # Aseguramos que si son None aquí, los usamos como None.

            # 4. Convertir a los tipos de datos correctos
            # int() y float() lanzarán un ValueError si la cadena está vacía o no es un número.
            # Usamos try-except para manejar esto y asignar None.
            comuna = None
            if comuna_str:
                try:
                    comuna = int(comuna_str)
                except ValueError:
                    print("Comuna ingresada no es un número válido. Se guardará como vacío.")

            latitud = None
            if latitud_str:
                try:
                    latitud = float(latitud_str)
                except ValueError:
                    print("Latitud ingresada no es un número decimal válido. Se guardará como vacío.")

            longitud = None
            if longitud_str:
                try:
                    longitud = float(longitud_str)
                except ValueError:
                    print("Longitud ingresada no es un número decimal válido. Se guardará como vacío.")

            # 5. Crear la nueva instancia de Obra y persistirla.
            # El requisito dice usar .save(), Obra.create() lo hace internamente.
            # Podríamos también hacer:
            # nueva_obra_obj = Obra(...)
            # nueva_obra_obj.save()
            # Pero .create() es más conciso y cumple la función.

            nueva_obra_obj = Obra.create(
                nombre=nombre if nombre else None, # Si el nombre está vacío, lo guardamos como None
                etapa=etapa if etapa else None,
                tipo_obra=tipo_obra_validado, # Usamos el valor validado
                area_responsable=area_responsable_validado, # Usamos el valor validado
                estado=estado if estado else None,
                comuna=comuna, # Ya convertido o None
                barrio=barrio_validado, # Usamos el valor validado
                latitud=latitud, # Ya convertido o None
                longitud=longitud, # Ya convertido o None
                fecha_inicio=fecha_inicio if fecha_inicio else None,
                fecha_fin_inicial=fecha_fin_inicial if fecha_fin_inicial else None
            )
            print(f"\nNueva obra '{nueva_obra_obj.nombre}' (ID: {nueva_obra_obj.id}) creada y guardada exitosamente.")
            return nueva_obra_obj # Retornamos la instancia creada

        except Exception as e:
            print(f"Error al crear la nueva obra: {e}")
            return None
        finally:
            # Asegurarse de que la conexión se cierre.
            if not db.is_closed():
                db.close()
                print("Conexión a la base de datos cerrada después de crear nueva obra.")
    
    def obtener_indicadores(cls):
        """
        Obtiene y muestra indicadores básicos de las obras existentes en la base de datos.
        """
        print("\n--- Obteniendo indicadores de obras ---")
        cls.conectar_db() # Nos aseguramos de estar conectados a la BD

        try:
            # 1. Cantidad total de obras
            total_obras = Obra.select().count()
            print(f"1. Cantidad total de obras: {total_obras}")

            # 2. Obras por tipo
            # SELECT tipo_obra, COUNT(id) FROM obras GROUP BY tipo_obra;
            print("\n2. Obras por tipo:")
            # .dicts() convierte los resultados en diccionarios Python, más fácil de manejar.
            obras_por_tipo = (Obra
                                .select(Obra.tipo_obra, fn.COUNT(Obra.id).alias('cantidad'))
                                .group_by(Obra.tipo_obra)
                                .order_by(fn.COUNT(Obra.id).desc()) # Ordenamos de mayor a menor
                                .dicts()) # Obtener los resultados como diccionarios

            if not obras_por_tipo:
                print("   No hay obras registradas por tipo.")
            else:
                for item in obras_por_tipo:
                    tipo = item['tipo_obra'] if item['tipo_obra'] else "Sin Tipo (Nulo)"
                    cantidad = item['cantidad']
                    print(f"   - {tipo}: {cantidad}")

            # 3. Obras por área responsable
            print("\n3. Obras por área responsable:")
            obras_por_area = (Obra
                                .select(Obra.area_responsable, fn.COUNT(Obra.id).alias('cantidad'))
                                .group_by(Obra.area_responsable)
                                .order_by(fn.COUNT(Obra.id).desc())
                                .dicts())

            if not obras_por_area:
                print("   No hay obras registradas por área responsable.")
            else:
                for item in obras_por_area:
                    area = item['area_responsable'] if item['area_responsable'] else "Sin Área (Nulo)"
                    cantidad = item['cantidad']
                    print(f"   - {area}: {cantidad}")

            # 4. Obras por estado
            print("\n4. Obras por estado:")
            obras_por_estado = (Obra
                                .select(Obra.estado, fn.COUNT(Obra.id).alias('cantidad'))
                                .group_by(Obra.estado)
                                .order_by(fn.COUNT(Obra.id).desc())
                                .dicts())

            if not obras_por_estado:
                print("   No hay obras registradas por estado.")
            else:
                for item in obras_por_estado:
                    estado = item['estado'] if item['estado'] else "Sin Estado (Nulo)"
                    cantidad = item['cantidad']
                    print(f"   - {estado}: {cantidad}")

            print("\nGeneración de indicadores completada.")
            # Este método no necesita retornar un diccionario, solo imprime.
            # Si en el futuro lo necesitaras, puedes descomentar la línea
            # que crea y retorna el diccionario 'indicadores'.
            # return indicadores

        except Exception as e:
            print(f"Error al obtener indicadores de obras: {e}")
            return None # Retorna None si hubo un error grave
        finally:
            if not db.is_closed():
                db.close()
                print("Conexión a la base de datos cerrada después de obtener indicadores.")

    @classmethod
    def nueva_obra(cls):
            """
            Permite al usuario ingresar los datos de una nueva obra por teclado
            y la persiste en la base de datos, con validaciones sencillas.
            Retorna la nueva instancia de Obra creada.
            """
            print("\n--- Ingrese los datos de la nueva obra ---")

            nombre = input("Nombre de la obra (requerido): ").strip()
            if not nombre:
                print("El nombre de la obra no puede estar vacío. Cancelando creación.")
                return None

            etapa = input("Etapa (Ej: En proceso, Finalizada - si la dejas vacía, `nuevo_proyecto` la pondrá en 'Proyecto'): ").strip()

            cls.conectar_db()
            try:
                def validar_o_confirmar_nuevo_valor(campo_modelo, prompt_texto):
                    valor_ingresado = input(prompt_texto).strip()
                    if not valor_ingresado:
                        return None

                    # Buscamos si el valor ya existe en la BD
                    existe = Obra.select().where(getattr(Obra, campo_modelo) == valor_ingresado).count() > 0

                    if existe:
                        print(f"'{valor_ingresado}' para '{campo_modelo.replace('_', ' ')}' encontrado en datos existentes.")
                        return valor_ingresado
                    else:
                        # Si no existe, preguntamos si de todas formas quiere usarlo
                        print(f"'{valor_ingresado}' para '{campo_modelo.replace('_', ' ')}' NO encontrado en datos existentes.")
                        confirmacion = input(f"¿Desea guardar '{valor_ingresado}' de todas formas como nuevo valor (s/n)? ").lower()
                        if confirmacion == 's':
                            return valor_ingresado
                        else:
                            print(f"Dejando '{campo_modelo.replace('_', ' ')}' vacío o asignando 'N/A' si no se fuerza el valor.")
                            return None

                tipo_obra = validar_o_confirmar_nuevo_valor('tipo_obra', "Tipo de obra (Ej: Vivienda, Salud): ")
                area_responsable = validar_o_confirmar_nuevo_valor('area_responsable', "Área responsable: ")
                barrio = validar_o_confirmar_nuevo_valor('barrio', "Barrio: ")
                tipo_contratacion = validar_o_confirmar_nuevo_valor('tipo_contratacion', "Tipo de Contratación (Ej: Licitación Pública, Contratación Directa): ")
                nro_contratacion = input("Número de Contratación (opcional): ").strip()

                # --- NUEVA VALIDACIÓN PARA PUNTO 10: Empresa y Expediente ---
                empresa_adjudicada = validar_o_confirmar_nuevo_valor('empresa_adjudicada', "Empresa Adjudicada (debe existir o confirmar nuevo): ")
                nro_expediente = input("Número de Expediente (opcional): ").strip()

                estado = input("Estado de la obra: ").strip()
                comuna_str = input("Comuna (número entero, dejar vacío si no aplica): ").strip()
                latitud_str = input("Latitud (número decimal, ej: -34.6, dejar vacío si no aplica): ").strip()
                longitud_str = input("Longitud (número decimal, ej: -58.4, dejar vacío si no aplica): ").strip()
                fecha_inicio = input("Fecha de inicio (YYYY-MM-DD, dejar vacío si no aplica): ").strip()
                fecha_fin_inicial = input("Fecha de fin inicial (YYYY-MM-DD, dejar vacío si no aplica): ").strip()

                comuna = None
                if comuna_str:
                    try:
                        comuna = int(comuna_str)
                    except ValueError:
                        print("Comuna ingresada no es un número válido. Se guardará como vacío.")

                latitud = None
                if latitud_str:
                    try:
                        latitud = float(latitud_str)
                    except ValueError:
                        print("Latitud ingresada no es un número decimal válido. Se guardará como vacío.")

                longitud = None
                if longitud_str:
                    try:
                        longitud = float(longitud_str)
                    except ValueError:
                        print("Longitud ingresada no es un número decimal válido. Se guardará como vacío.")

                nueva_obra_obj = Obra.create(
                    nombre=nombre if nombre else None,
                    etapa=etapa if etapa else None,
                    tipo_obra=tipo_obra,
                    area_responsable=area_responsable,
                    estado=estado if estado else None,
                    comuna=comuna,
                    barrio=barrio,
                    latitud=latitud,
                    longitud=longitud,
                    fecha_inicio=fecha_inicio if fecha_inicio else None,
                    fecha_fin_inicial=fecha_fin_inicial if fecha_fin_inicial else None,
                    tipo_contratacion=tipo_contratacion,
                    nro_contratacion=nro_contratacion if nro_contratacion else None,
                    empresa_adjudicada=empresa_adjudicada, # Nuevo campo
                    nro_expediente=nro_expediente if nro_expediente else None # Nuevo campo
                )
                print(f"\nNueva obra '{nueva_obra_obj.nombre}' (ID: {nueva_obra_obj.id}) creada y guardada exitosamente.")
                return nueva_obra_obj

            except Exception as e:
                print(f"Error al crear la nueva obra: {e}")
                return None
            finally:
                if not db.is_closed():
                    db.close()
                    print("Conexión a la base de datos cerrada después de crear nueva obra.")
