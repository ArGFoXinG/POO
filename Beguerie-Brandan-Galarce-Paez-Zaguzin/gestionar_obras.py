import pandas as pd
from modelo_orm import *
from datetime import datetime
import peewee
import unicodedata 

print(f"Versión de Peewee utilizada: {peewee.__version__}")

class GestionarObra:
    _db_initialized = False

    @classmethod
    def conectar_db(cls):
        # Establece la conexión a la base de datos si aún no está abierta.

        if db.is_closed():
            try:
                db.connect()
            except OperationalError as e:
                print(f"Error de conexión a la base de datos: {e}")
            except Exception as e:
                print(f"Error inesperado al conectar a la base de datos: {e}")

    @classmethod
    def mapear_orm(cls):
        # Crea las tablas en la base de datos si aún no existen.

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
        # Extrae datos del archivo CSV.

        try:
            with open('observatorio-de-obras-urbanas.csv', 'r', encoding='UTF-8') as f:
                primera_linea = f.readline()
                print("Encabezados del CSV (crudos):", primera_linea.strip())

            df = pd.read_csv(
                'observatorio-de-obras-urbanas.csv',
                encoding='UTF-8',
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
        # Limpia los datos del DataFrame: elimina filas vacías, procesa fechas y montos.

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

            # CORRECCIÓN: Quitamos dayfirst=True para el formato AAAA-MM-DD
            df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'], errors='coerce').dt.date
            df['fecha_fin_inicial'] = pd.to_datetime(df['fecha_fin_inicial'], errors='coerce').dt.date

            if 'monto_contrato' in df.columns:
                df['monto_contrato'] = pd.to_numeric(
                    df['monto_contrato'].astype(str).str.replace('$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.'),
                    errors='coerce'
                )

            # CORRECCIÓN: Siempre devolvemos True/False, no None
            if 'destacada' in df.columns:
                df['destacada'] = df['destacada'].astype(str).str.lower().apply(lambda x: True if x == 'si' else False)
            if 'ba_elige' in df.columns:
                df['ba_elige'] = df['ba_elige'].astype(str).str.lower().apply(lambda x: True if x == 'si' else False)

           # Normalización de la columna 'etapa'
        if 'etapa' in df.columns:
            # conversion al bajo registro
            df['etapa'] = df['etapa'].astype(str).str.lower().str.strip()

            # dictionario para normalizar
            etapa_mapping = {
                'anteproyecto': 'proyecto',
                'en ejecucion': 'en ejecucion',
                'en ejecución': 'en ejecucion',
                'en obra': 'en ejecucion', 
                'en curso': 'en ejecucion',
                'en proyecto': 'proyecto',
                'en contratacion': 'en contratacion',
                'adjudicada': 'adjudicada',
                'finalizada': 'finalizada',
                'proyecto finalizado': 'finalizada',
                'rescindida': 'rescindida',
                'rescisión': 'rescindida',
                'paralizada': 'paralizada',
                'neutralizada': 'paralizada',
                'desestimada': 'desestimada',
            }
            df['etapa'] = df['etapa'].replace(etapa_mapping)

            # convertimos al registro alto
            df['etapa'] = df['etapa'].str.title()
            int_cols_to_fill = ['plazo_meses', 'porcentaje_avance', 'mano_obra', 'licitacion_anio']
            for col in int_cols_to_fill:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # sin NaN
            df.dropna(subset=['nombre', 'barrio'], inplace=True)
            print(f"Filas después de dropna: {len(df)}") # Para depuración

            #normalizacion de barrios
            if 'barrio' in df.columns:
                print("Normalizando nombres de barrios...") # Para depuración
                df['barrio'] = df['barrio'].astype(str).apply(
                    lambda x: unicodedata.normalize('NFKD', x)
                                         .encode('ascii', 'ignore')
                                         .decode('utf-8')
                                         .lower()
                                         .strip()
                )

            print(f"Datos limpiados. Cantidad de filas inicial: {initial_rows}. Después de la limpieza: {len(df)}")
            return df
        return None

    @classmethod
    def cargar_datos(cls):
        # Carga los datos limpios del DataFrame a la base de datos.

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
                    
                    # Usamos el nombre de barrio normalizado para buscar/crear
                    barrio_obj, _ = Barrio.get_or_create(nombre=fila['barrio']) 

                    obra_existente = Obra.get_or_none(Obra.nombre == fila['nombre'], Obra.barrio == barrio_obj)

                    if obra_existente:
                        print(f"Error de integridad de datos al cargar fila {index+1}: Obra con nombre '{fila['nombre']}' y barrio '{fila['barrio']}' ya existe. Saltada.")
                        continue

                    Obra.create(
                        entorno=fila.get('entorno'),
                        nombre=fila.get('nombre'),
                        etapa=fila.get('etapa'), # Por defecto será "Proyecto" si el CSV no lo contiene
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
                        # CORRECCIÓN: Convertimos NaT a None
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
                    print(f"Error de integridad de datos al cargar fila {index+1}: {e}. Posiblemente duplicado. Saltada.")
                except KeyError as e:
                    print(f"Columna faltante: {str(e)} - Fila omitida. Index: {index+1}")
                    continue
                except Exception as e:
                    print(f"Error al procesar fila {index+1}: {e}. Fila omitida.")
                    continue
        db.close()
        print("Carga de datos completada.")


    @classmethod
    def nueva_obra(cls):
        # Crea una nueva obra de forma interactiva y la devuelve
        print("\nCrear nueva obra")
        nombre = input("Ingrese el nombre de la obra: ")

        cls.conectar_db()
        if Obra.select().where(Obra.nombre == nombre).exists():
            print(f"Una obra con el nombre '{nombre}' ya existe. Por favor, elija otro nombre.")
            db.close()
            return None
        db.close()

        entorno = input("Ingrese el entorno (ej. 'Vía Pública', 'Edificio'): ")
        descripcion = input("Ingrese una descripción de la obra: ")

        tipo_obra_obj = None
        while tipo_obra_obj is None:
            input_tipo = input("Ingrese el tipo de obra (ej. 'Escuela', 'Hospital') o 'lista' para ver existentes: ")
            if input_tipo.lower() == 'lista':
                cls.conectar_db()
                tipos = [t.nombre for t in TipoObra.select()]
                db.close()
                if tipos:
                    print("Tipos de obra existentes:", ", ".join(tipos))
                else:
                    print("No hay tipos de obra en la base de datos.")
            else:
                cls.conectar_db()
                tipo_obra_obj, created = TipoObra.get_or_create(nombre=input_tipo)
                db.close()
                if created:
                    print(f"Nuevo tipo de obra creado: {tipo_obra_obj.nombre}")
                else:
                    print(f"Usando tipo de obra existente: {tipo_obra_obj.nombre}")

        area_responsable_obj = None
        while area_responsable_obj is None:
            input_area = input("Ingrese el área responsable (ej. 'Ministerio de Educación') o 'lista': ")
            if input_area.lower() == 'lista':
                cls.conectar_db()
                areas = [a.nombre for a in AreaResponsable.select()]
                db.close()
                if areas:
                    print("Áreas responsables existentes:", ", ".join(areas))
                else:
                    print("No hay áreas responsables en la base de datos.")
            else:
                cls.conectar_db()
                area_responsable_obj, created = AreaResponsable.get_or_create(nombre=input_area)
                db.close()
                if created:
                    print(f"Nueva área responsable creada: {area_responsable_obj.nombre}")
                else:
                    print(f"Usando área responsable existente: {area_responsable_obj.nombre}")

        barrio_obj = None
        while barrio_obj is None:
            input_barrio = input("Ingrese el barrio o 'lista': ")
            if input_barrio.lower() == 'lista':
                cls.conectar_db()
                barrios = [b.nombre for b in Barrio.select()]
                db.close()
                if barrios:
                    print("Barrios existentes:", ", ".join(barrios))
                else:
                    print("No hay barrios en la base de datos.")
            else:
                # Normaliza la entrada del usuario antes de buscar/crear el barrio
                normalized_barrio_input = unicodedata.normalize('NFKD', input_barrio).encode('ascii', 'ignore').decode('utf-8').lower().strip()
                
                cls.conectar_db()
                barrio_obj, created = Barrio.get_or_create(nombre=normalized_barrio_input)
                db.close()
                if created:
                    print(f"Nuevo barrio creado: {barrio_obj.nombre}")
                else:
                    print(f"Usando barrio existente: {barrio_obj.nombre}")

        direccion = input("Ingrese la dirección: ")
        comuna = input("Ingrese el número de comuna (opcional, deje en blanco si no aplica): ")
        if not comuna:
            comuna = None

        nueva_obra_instance = Obra(
            nombre=nombre,
            entorno=entorno,
            descripcion=descripcion,
            tipo=tipo_obra_obj,
            area=area_responsable_obj,
            barrio=barrio_obj,
            direccion=direccion,
            comuna=comuna
        )

        cls.conectar_db()
        try:
            nueva_obra_instance.save()
            nueva_obra_instance.nuevo_proyecto(tipo_obra_obj, area_responsable_obj, barrio_obj)
            print(f"Obra '{nombre}' creada exitosamente en la etapa '{nueva_obra_instance.etapa}'.")
            return nueva_obra_instance
        except Exception as e:
            print(f"Error al crear la nueva obra: {e}")
            return None
        finally:
            db.close()


    @classmethod
    def _menu_gestion_obra(cls, obra_id):
        # Presenta un menú interactivo para gestionar las etapas de una obra específica.
        # Permite al usuario seleccionar acciones y salir en cualquier momento.

        while True:
            cls.conectar_db()
            try:
                obra_a_actualizar = Obra.get(Obra.id == obra_id)
            except Obra.DoesNotExist:
                print(f"Obra con ID {obra_id} no encontrada.")
                db.close()
                return # Salir si la obra no se encuentra

            current_etapa = obra_a_actualizar.etapa
            print(f"\nGestión de etapas para la obra: {obra_a_actualizar.nombre} (ID: {obra_id})")
            print(f"Etapa actual: {current_etapa}")

            print("\nOpciones:")

            # Ofrecemos opciones dependiendo de la etapa actual
            if current_etapa == 'Proyecto':
                print("1. Iniciar Contratación")
            elif current_etapa == 'En Contratacion':
                print("1. Adjudicar Obra")
            elif current_etapa == 'Adjudicada':
                print("1. Iniciar Obra (En Ejecución)")
            elif current_etapa == 'En Ejecucion':
                print("1. Actualizar porcentaje de avance")
                print("2. Incrementar plazo")
                print("3. Incrementar mano de obra")
                print("4. Finalizar Obra")
                print("5. Rescindir Obra")
            elif current_etapa in ['Finalizada', 'Rescindida']:
                print(f"La obra ya está {current_etapa.lower()}. No se pueden realizar más cambios de etapa.")

            print("0. Volver al menú principal")

            opcion_etapa = input("Seleccione una opción: ")

            cls.conectar_db() # Reconectamos dentro del bucle para operaciones de guardado
            try:
                if opcion_etapa == '0':
                    print(f"Volviendo al menú principal. La obra '{obra_a_actualizar.nombre}' permanece en etapa '{obra_a_actualizar.etapa}'.")
                    break # Salir del bucle de gestión de etapas

                elif current_etapa == 'Proyecto' and opcion_etapa == '1':
                    print("Ingrese datos para la etapa 'Contratación':")
                    tipo_contratacion_val = input("Tipo de contratación: ")
                    nro_contratacion_val = input("Número de contratación: ")
                    obra_a_actualizar.iniciar_contratacion(tipo_contratacion_val, nro_contratacion_val)

                elif current_etapa == 'En Contratacion' and opcion_etapa == '1':
                    print("Ingrese datos para la etapa 'Adjudicación':")
                    empresa_val = input("Nombre de la empresa licitante: ")
                    nro_expediente_val = input("Número de expediente: ")
                    obra_a_actualizar.adjudicar_obra(empresa_val, nro_expediente_val)

                elif current_etapa == 'Adjudicada' and opcion_etapa == '1':
                    print("Ingrese datos para la etapa 'Inicio de Obra':")
                    destacada_val = input("¿Obra destacada? (True/False): ").lower() == 'true'
                    fecha_inicio_str = input("Fecha de inicio (AAAA-MM-DD): ")
                    fecha_fin_inicial_str = input("Fecha estimada de finalización (AAAA-MM-DD): ")
                    fuente_financiamiento_val = input("Fuente de financiación: ")
                    try:
                        mano_obra_val = int(input("Cantidad de mano de obra: "))
                    except ValueError:
                        print("Entrada inválida para la cantidad de mano de obra. Usando 0.")
                        mano_obra_val = 0

                    try:
                        fecha_inicio_dt = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                        fecha_fin_inicial_dt = datetime.strptime(fecha_fin_inicial_str, '%Y-%m-%d').date()
                    except ValueError:
                        print("Formato de fecha inválido. La obra no avanzará de etapa.")
                        db.close()
                        continue

                    obra_a_actualizar.iniciar_obra(destacada_val, fecha_inicio_dt, fecha_fin_inicial_dt, fuente_financiamiento_val, mano_obra_val)

                elif current_etapa == 'En Ejecucion':
                    if opcion_etapa == '1':
                        try:
                            print(f"Porcentaje de avance actual: {obra_a_actualizar.porcentaje_avance}%")
                            porcentaje_avance_val = int(input("Ingrese el porcentaje de avance (ej. 50): "))
                            obra_a_actualizar.actualizar_porcentaje_avance(porcentaje_avance_val)
                        except ValueError:
                            print("Entrada inválida para el porcentaje de avance.")
                    elif opcion_etapa == '2':
                        try:
                            meses_adicional = int(input("¿En cuántos meses desea incrementar el plazo? "))
                            obra_a_actualizar.incrementar_plazo(meses_adicional)
                        except ValueError:
                            print("Entrada inválida para los meses.")
                    elif opcion_etapa == '3':
                        try:
                            cantidad_adicional_mano_obra = int(input("¿En cuánto desea incrementar la mano de obra? "))
                            obra_a_actualizar.incrementar_mano_obra(cantidad_adicional_mano_obra)
                        except ValueError:
                            print("Entrada inválida para la cantidad de mano de obra.")
                    elif opcion_etapa == '4':
                        obra_a_actualizar.finalizar_obra()
                        break # Salir del bucle después de finalizar
                    elif opcion_etapa == '5':
                        obra_a_actualizar.rescindir_obra()
                        break # Salir del bucle después de rescindir
                    else:
                        print("Opción inválida para la etapa actual.")

                elif current_etapa in ['Finalizada', 'Rescindida']:
                    print("Esta obra ya ha finalizado o ha sido rescindida. No se pueden realizar más cambios de etapa.")
                    break # Salir del bucle ya que no se permiten más cambios

                else:
                    print("Opción inválida.")

            except Exception as e:
                print(f"Ocurrió un error: {e}")
            finally:
                db.close()


    @classmethod
    def _avanzar_etapa_obra_existente(cls):
        # Permite seleccionar una obra existente y avanzar su etapa.
        # Invoca a _menu_gestion_obra para la gestión interactiva.

        print("\nCambiar etapa de obra existente")
        cls.conectar_db()
        obras = Obra.select().order_by(Obra.id)
        if not obras:
            print("No hay obras en la base de datos.")
            db.close()
            return

        print("Lista de obras:")
        for obra in obras:
            print(f"ID: {obra.id}, Nombre: {obra.nombre}, Etapa actual: {obra.etapa}")
        db.close()

        try:
            obra_id = int(input("Ingrese el ID de la obra que desea modificar: "))
        except ValueError:
            print("ID inválido. Por favor, ingrese un número.")
            return

        # Llamamos directamente al menú interactivo para la obra seleccionada
        cls._menu_gestion_obra(obra_id)


    @classmethod
    def obtener_indicadores(cls):
        cls.conectar_db()
        try:
            print(f"\n--- Indicadores de Obras ---")

            print("\na. Listado de todas las áreas responsables:")
            areas = AreaResponsable.select().order_by(AreaResponsable.nombre)
            for area in areas:
                print(f"   - {area.nombre}")
            if not areas:
                print("   No hay áreas responsables.")

            print("\nb. Listado de todos los tipos de obra:")
            tipos_obra = TipoObra.select().order_by(TipoObra.nombre)
            for tipo in tipos_obra:
                print(f"   - {tipo.nombre}")
            if not tipos_obra:
                print("   No hay tipos de obra.")

            print("\nc. Cantidad de obras por etapa:")
            etapas = Obra.select(Obra.etapa, fn.COUNT(Obra.id).alias('count')).group_by(Obra.etapa)
            for etapa in etapas:
                print(f"   - {etapa.etapa}: {etapa.count}")
            if not etapas:
                print("   No hay obras en ninguna etapa.")

            print("\nd. Cantidad de obras y monto total de inversión por tipo de obra:")
            tipos_inversion = (Obra.select(TipoObra.nombre, fn.COUNT(Obra.id).alias('cantidad_obras'), fn.SUM(Obra.monto_contrato).alias('monto_total'))
                                .join(TipoObra)
                                .group_by(TipoObra.nombre))
            for tipo in tipos_inversion:
                monto = f"${tipo.monto_total:,.2f}" if tipo.monto_total else "N/A"
                print(f"   - {tipo.tipo.nombre}: Cantidad = {tipo.cantidad_obras}, Inversión Total = {monto}")
            if not tipos_inversion:
                print("   No hay datos de obras por tipo para calcular la inversión.")

            # e. Listado de barrios en Comunas seleccionadas (INTERACTIVO)
            print("\ne. Listado de barrios en comunas seleccionadas:")
            
            cls.conectar_db() # Asegurarse de que la conexión está abierta para esta parte
            comunas_disponibles = Obra.select(Obra.comuna).distinct().where(Obra.comuna.is_null(False)).order_by(Obra.comuna)
            if comunas_disponibles.count() > 0:
                print("Comunas disponibles:", ", ".join([str(c.comuna) for c in comunas_disponibles]))
                comunas_input = input("Ingrese los números de comuna (ej. '1,2,3' o 'todas'): ").strip()
                
                if comunas_input.lower() == 'todas':
                    comunas_a_filtrar = [str(c.comuna) for c in comunas_disponibles]
                else:
                    comunas_raw = [c.strip() for c in comunas_input.split(',')]
                    comunas_a_filtrar = []
                    for c in comunas_raw:
                        if c.isdigit() and int(c) > 0 and int(c) <= 15:
                            comunas_a_filtrar.append(c)
                        else:
                            print(f"Advertencia: '{c}' no es un número de comuna válido (1-15) y será ignorado.")
                
                if not comunas_a_filtrar:
                    print("   No se ingresaron comunas válidas para filtrar.")
                else:
                    barrios_comunas = (Barrio.select(Barrio.nombre)
                                    .join(Obra)
                                    .where(Obra.comuna.in_(comunas_a_filtrar))
                                    .distinct()
                                    .order_by(Barrio.nombre))
                    
                    if barrios_comunas.count() > 0:
                        print(f"   Barrios en comunas {', '.join(comunas_a_filtrar)}:")
                        for barrio in barrios_comunas:
                            print(f"      - {barrio.nombre.title()}") 
                    else:
                        print(f"   No hay barrios asociados a obras en las comunas {', '.join(comunas_a_filtrar)}.")
            else:
                print("   No hay información de comunas en la base de datos.")


            print("\nf. Cantidad de obras finalizadas en un plazo menor o igual a 24 meses:")
            obras_finalizadas_en_plazo = Obra.select().where(
                (Obra.etapa == 'Finalizada') &
                (Obra.plazo_meses <= 24)
            ).count()
            print(f"   - Cantidad de obras: {obras_finalizadas_en_plazo}")

            print("\ng. Monto total de inversión:")
            total_inversion_general = Obra.select(fn.SUM(Obra.monto_contrato)).scalar()
            if total_inversion_general is not None:
                print(f"   - Monto total general: ${total_inversion_general:,.2f}")
            else:
                print("   No hay información de inversión disponible.")
            
            print("\n--- Fin de Indicadores ---")
        except Exception as e:
            print(f"Error al obtener indicadores: {e}")
        finally:
            db.close()

# Bloque principal de ejecución del programa
if __name__ == '__main__':
    GestionarObra.mapear_orm()

    GestionarObra.conectar_db()
    if Obra.select().count() == 0:
        print("Base de datos vacía. Cargando datos desde CSV...")
        GestionarObra.cargar_datos()
        print("Datos cargados desde CSV.")
    else:
        print(f"La base de datos ya contiene {Obra.select().count()} registros. Se omite la carga desde CSV.")
    db.close()

    while True:
        print("\nMenú del Sistema de Gestión de Obras")
        print("1. Crear nueva obra y gestionar sus etapas")
        print("2. Gestionar etapas de una obra existente")
        print("3. Mostrar indicadores y volver al menú")
        print("4. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == '1':
            nueva_obra_obj = GestionarObra.nueva_obra()
            if nueva_obra_obj:
                # Invocamos el menú interactivo
                GestionarObra._menu_gestion_obra(nueva_obra_obj.id)
        elif opcion == '2':
            # Esta función se encargará de llamar a _menu_gestion_obra
            GestionarObra._avanzar_etapa_obra_existente()
        elif opcion == '3':
            print("Mostrando indicadores...")
            GestionarObra.obtener_indicadores()
            # No hay 'break' aquí, el bucle 'while True' continuará
        elif opcion == '4':
            print("Saliendo del programa. ¡Hasta luego!")
            break
        else:
            print("Opción inválida. Por favor, seleccione un número del 1 al 5.")
