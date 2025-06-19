from gestionar_obras import GestionarObra
from modelo_orm import Obra, db

def ejecutar_proceso():
    print("--- Inicio del Proceso de Gestión de Obras ---")

    # 1. Asegurarse de que la base de datos y la tabla estén creadas
    GestionarObra.mapear_orm()

    # 2. Intentar cargar datos del CSV (si existe y no hay datos ya)
    GestionarObra.conectar_db()
    try:
        if Obra.select().count() == 0:
            print("\nLa base de datos está vacía. Cargando datos del CSV...")
            df_obras = GestionarObra.extraer_datos()
            if df_obras is not None:
                df_limpio = GestionarObra.limpiar_datos(df_obras)
                if df_limpio is not None:
                    GestionarObra.cargar_datos(df_limpio)
        else:
            print("\nLa base de datos ya contiene obras. No se cargará el CSV de nuevo.")
    except Exception as e:
        print(f"Error al verificar o cargar datos iniciales: {e}")
    finally:
        if not db.is_closed():
            db.close()


    # 3. Crear nuevas instancias de Obra (al menos dos)
    print("\n--- Creación de nuevas obras manualmente ---")

    print("\n**Primera obra (seguir los pasos para ingresarla):**")
    nueva_obra_1 = GestionarObra.nueva_obra()

    print("\n**Segunda obra (seguir los pasos para ingresarla):**")
    nueva_obra_2 = GestionarObra.nueva_obra()

    # 4. Hacer que las nuevas obras pasen por todas las etapas y persistir cambios
    # (La persistencia con .save() ya está manejada dentro de cada método de la clase Obra)
    print("\n--- Simulando el ciclo de vida de las nuevas obras ---")

    # Proceso para la primera obra: ciclo completo hasta finalizar
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

                    existe = Obra.select().where(getattr(Obra, campo_modelo) == valor_ingresado).count() > 0

                    if existe:
                        print(f"'{valor_ingresado}' para '{campo_modelo.replace('_', ' ')}' encontrado en datos existentes.")
                        return valor_ingresado
                    else:
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

                # --- NUEVA VALIDACIÓN PARA PUNTO 9: Tipo Contratacion ---
                tipo_contratacion = validar_o_confirmar_nuevo_valor('tipo_contratacion', "Tipo de Contratación (Ej: Licitación Pública, Contratación Directa): ")
                nro_contratacion = input("Número de Contratación (opcional): ").strip()

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
                    tipo_contratacion=tipo_contratacion, # Nuevo campo
                    nro_contratacion=nro_contratacion if nro_contratacion else None # Nuevo campo
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

    if nueva_obra_1:
        print(f"\n---> Procesando obra: {nueva_obra_1.nombre} (ID: {nueva_obra_1.id}) <---")
        print("  Estado actual:", nueva_obra_1.estado, "- Etapa actual:", nueva_obra_1.etapa)

        print("\n  - Paso 1: Nuevo Proyecto")
        nueva_obra_1.nuevo_proyecto()
        print("  Estado actual:", nueva_obra_1.estado, "- Etapa actual:", nueva_obra_1.etapa)

        print("\n  - Paso 2: Iniciar Contratación")
        nueva_obra_1.iniciar_contratacion(
            tipo_contratacion=nueva_obra_1.tipo_contratacion,
            nro_contratacion=nueva_obra_1.nro_contratacion
        )
        print("  Estado actual:", nueva_obra_1.estado, "- Etapa actual:", nueva_obra_1.etapa)
        print(f"  Tipo Contratación: {nueva_obra_1.tipo_contratacion}, Nro Contratación: {nueva_obra_1.nro_contratacion}")

        print("\n  - Paso 3: Adjudicar Obra")
        # --- CAMBIO AQUI PARA EL PUNTO 10 ---
        nueva_obra_1.adjudicar_obra(
            empresa=nueva_obra_1.empresa_adjudicada,
            nro_expediente=nueva_obra_1.nro_expediente
        )
        print("  Estado actual:", nueva_obra_1.estado, "- Etapa actual:", nueva_obra_1.etapa)
        print(f"  Empresa Adjudicada: {nueva_obra_1.empresa_adjudicada}, Nro Expediente: {nueva_obra_1.nro_expediente}")

        # ... (resto de etapas, se mantienen igual) ...

    # Proceso para la segunda obra: ciclo hasta rescindir
    if nueva_obra_2:
        print(f"\n---> Procesando obra: {nueva_obra_2.nombre} (ID: {nueva_obra_2.id}) <---")
        print("  Estado actual:", nueva_obra_2.estado, "- Etapa actual:", nueva_obra_2.etapa)

        print("\n  - Paso 1: Nuevo Proyecto")
        nueva_obra_2.nuevo_proyecto()
        print("  Estado actual:", nueva_obra_2.estado, "- Etapa actual:", nueva_obra_2.etapa)

        print("\n  - Paso 2: Iniciar Contratación")
        nueva_obra_2.iniciar_contratacion(
            tipo_contratacion=nueva_obra_2.tipo_contratacion,
            nro_contratacion=nueva_obra_2.nro_contratacion
        )
        print("  Estado actual:", nueva_obra_2.estado, "- Etapa actual:", nueva_obra_2.etapa)
        print(f"  Tipo Contratación: {nueva_obra_2.tipo_contratacion}, Nro Contratación: {nueva_obra_2.nro_contratacion}")

        print("\n  - Paso 3: Adjudicar Obra")
        # --- CAMBIO AQUI PARA EL PUNTO 10 ---
        nueva_obra_2.adjudicar_obra(
            empresa=nueva_obra_2.empresa_adjudicada,
            nro_expediente=nueva_obra_2.nro_expediente
        )
        print("  Estado actual:", nueva_obra_2.estado, "- Etapa actual:", nueva_obra_2.etapa)
        print(f"  Empresa Adjudicada: {nueva_obra_2.empresa_adjudicada}, Nro Expediente: {nueva_obra_2.nro_expediente}")

    # 5. Obtener indicadores para ver cómo los cambios afectan las estadísticas
    print("\n--- Indicadores después de simular el ciclo de vida de las obras ---")
    GestionarObra.obtener_indicadores()

    print("\n--- Fin del Proceso ---")

if __name__ == "__main__":
    ejecutar_proceso()