### Descripción de la aplicación Expo Manager

Esta aplicación está diseñada para automatizar y facilitar el procesamiento de galerías de imágenes destinadas a una aplicación de cartelería digital, todo ello integrando el almacenamiento en Google Drive como parte esencial del flujo de trabajo. La aplicación se centra en la gestión eficiente de imágenes, permitiendo a los usuarios organizar, personalizar y preparar contenido visual para su despliegue en pantallas de diferentes formatos.


2. **Módulo de Descarga:**
Esta clase proporciona una forma sencilla de descargar una carpeta completa desde Google Drive a una ubicación específica en el sistema local, creando la estructura de carpetas necesaria si no existe.
La clase `DownloadFiles` contiene un método estático llamado `download_files` que se encarga de descargar archivos desde una URL de Google Drive a una carpeta local específica. Aquí está el desglose detallado de su funcionamiento:

    2.1. **Parámetros del método:**
    - `url`: La URL de la carpeta de Google Drive que se desea descargar.
    - `output_folder`: El nombre de la carpeta donde se guardarán los archivos descargados.

    2.2. **Creación de la carpeta de salida:**
    - Construye la ruta completa de la carpeta de salida combinando:
        - El directorio de trabajo actual (`os.getcwd()`)
        - Una subcarpeta llamada 'expos'
        - El nombre de la carpeta especificada en `output_folder`
    - Verifica si esta carpeta ya existe usando `os.path.exists()`
    - Si no existe, la crea utilizando `os.makedirs()`

    2.3. **Descarga de archivos:**
    - Utiliza la función `gdown.download_folder()` de la biblioteca `gdown` para descargar todos los archivos y subcarpetas de la URL de Google Drive especificada.
    - Los archivos se guardan en la carpeta de salida creada anteriormente.

**Tareas pendientes:**
- mostrar el progreso de la descarga



3. **ExcelProcessor**
Esta clase automatiza el proceso de tomar un archivo Excel con información básica sobre obras de arte, enriquecerlo con datos extraídos de las imágenes correspondientes, y generar un nuevo archivo Excel con toda esta información consolidada y formateada.
La clase `ExcelProcessor` se encarga de procesar un archivo Excel que contiene información sobre obras de arte y generar un nuevo archivo Excel con datos adicionales. Aquí está el desglose de sus funcionalidades principales:

    3.1. **Inicialización:**
    - El constructor `__init__` recibe un parámetro `output_folder` que se almacena como atributo de la instancia.

    3.2. **Método `get_image_info`:**
    - Este método extrae información de una imagen, incluyendo dimensiones, resolución y orientación.
    - Utiliza la biblioteca PIL (Python Imaging Library) para abrir y analizar la imagen.
    - Intenta obtener la información de DPI (puntos por pulgada) de los metadatos EXIF si están disponibles.
    - Calcula la orientación (horizontal o vertical) basándose en las dimensiones de la imagen.
    - Devuelve un diccionario con la información extraída.

    3.3. **Método `process_excel`:**
    - Este es el método principal que procesa el archivo Excel.
    - Pasos del procesamiento:
        a. Localiza y abre el archivo Excel "Formulario obras.xlsx" en la carpeta especificada.
        b. Lee el contenido del Excel, omitiendo la primera fila.
        c. Asigna nombres específicos a las columnas del DataFrame.
        d. Realiza varias operaciones de limpieza y transformación de datos:
            - Rellena valores vacíos en la columna 'PANTALLA'.
            - Elimina filas con datos incompletos o irrelevantes.
            - Formatea los números de pantalla.
            - Crea una nueva columna 'FICHERO' combinando información.
        e. Agrega columnas nuevas para la información de las imágenes.
        f. Itera sobre cada fila del DataFrame:
            - Busca el archivo de imagen correspondiente.
            - Si lo encuentra, extrae la información de la imagen usando `get_image_info`.
            - Actualiza el DataFrame con la información extraída.
        g. Convierte las columnas numéricas al tipo de dato adecuado.
        h. Guarda el DataFrame procesado en un nuevo archivo Excel llamado "Resumen obras.xlsx".

    3.4. **Manejo de errores y logging:**
    - Incluye mensajes de print para informar sobre el progreso y posibles errores durante el procesamiento.

**Tareas pendientes:**
- detectar ficheros que no coinciden entre el excel y los ficheros descargados
- detectar orientaciones que no coinciden entre el fichero y el formato de la pantalla
- detectar resoluciones o formatos que no coinciden entre el fichero y el formato de la pantalla

