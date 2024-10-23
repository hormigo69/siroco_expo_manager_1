## Descripción de la aplicación Expo Manager

Esta aplicación está diseñada para automatizar y facilitar el procesamiento de galerías de imágenes y vídeos destinadas a una aplicación de cartelería digital, todo ello integrando el almacenamiento en Google Drive como parte esencial del flujo de trabajo. La aplicación se centra en la gestión eficiente de obras artísticas, permitiendo a los usuarios organizar, personalizar y preparar contenido visual para su despliegue en pantallas de diferentes formatos.


Resumen del flujo en main:
    1. Configura las variables para la exposición.
    2. Verifica la existencia de la carpeta de salida y descarga los archivos si es necesario.
    3. Guarda un archivo JSON con la lista de archivos de la exposición.
    4. Procesa el archivo Excel para completar la información de las obras.
    5. Verifica la existencia de la carpeta de imágenes (`Obras`).
    6. Configura la fuente para personalizar las imágenes.
    7. Procesa cada imagen y la guarda en el formato deseado.
    8. Comprime los archivos procesados en un ZIP.
    9. Informa la finalización del procesamiento.


### Pasos que realiza `main`:

1. **Definir la URL de la carpeta de Google Drive y las variables para la exposición**:
   - `drive_url_img_folder`: URL de la carpeta en Google Drive que contiene las imágenes de la exposición.
   - `output_folder`: Identificador de la exposición que se utilizará para nombrar directorios y archivos.
   - `expo_id`: Mismo identificador que `output_folder`, usado para mantener la consistencia en el nombre de la exposición.

2. **Comprobar si la carpeta de salida ya existe**:
   - `full_output_path` se define como la ruta donde se guardará el contenido descargado, utilizando el directorio actual (`os.getcwd()`) más el subdirectorio `expos/output_folder`.
   - Si la carpeta `full_output_path` no existe, se llama a `FileManager.download_files` para descargar los archivos de Google Drive.
     - **`FileManager.download_files(url, output_folder)`**: Este método descarga la carpeta especificada desde Google Drive y la guarda en la ruta `full_output_path`, creando el directorio si es necesario.
   - Si la carpeta ya existe, se notifica que no se volverán a descargar los archivos.

3. **Guardar un archivo JSON con la lista de archivos en la carpeta `Obras`**:
   - Se llama a `FileManager.save_file_list_json(full_output_path, expo_id)`.
     - **`FileManager.save_file_list_json(expo_folder, expo_id)`**: Este método crea un archivo JSON en el directorio de la exposición, que contiene la lista de archivos en la subcarpeta `Obras`, marcando cada archivo como `True` para que se genere un QR. 
     [ ] Más adelante hay que poder modificar este fichero para indicar qué ficheros no se van a generar QR

4. **Procesar el archivo Excel con la información de las obras**:
   - Se crea una instancia de `ExcelProcessor` con `output_folder` como argumento, y luego se llama a `excel_processor.process_excel()`.
     - **`ExcelProcessor.__init__(self, output_folder)`**: Inicializa un objeto `ExcelProcessor`, estableciendo el nombre de la carpeta de salida.
     - **`ExcelProcessor.process_excel()`**: Procesa el archivo Excel (`Formulario obras.xlsx`) ubicado en la carpeta de la exposición. Los pasos dentro de este método incluyen:
       - Verificar la existencia del archivo Excel.
       - Cargar el contenido del Excel y ajustar las columnas según el formato esperado.
       - Completar la información faltante y obtener detalles adicionales de las imágenes (ancho, alto, resolución, orientación).
       - Guardar los datos actualizados en un nuevo archivo Excel (`Resumen obras.xlsx`) en la carpeta `ficheros_salida`.

5. **Verificar la existencia de la carpeta `Obras`**:
   - Comprueba si la subcarpeta `Obras` existe dentro de `full_output_path`. Si no está presente, muestra un mensaje de error y se recomienda asegurarse de que las imágenes estén en la carpeta correcta.
   - Si la carpeta existe, muestra su contenido para confirmar la presencia de las imágenes.

6. **Configurar la ruta de la fuente para personalizar las imágenes**:
   - La ruta `font_path` se construye con la ubicación relativa del archivo de fuente `helvetica.ttf`.
   - Verifica la existencia de este archivo. Si no se encuentra, muestra un mensaje de error y finaliza el programa (`sys.exit(1)`).

7. **Crear una instancia de `ImageProcessor` y procesar las imágenes**:
   - Se crea un objeto `ImageProcessor` con los siguientes parámetros: 
     - `expo_dir`: Ruta de la carpeta de exposición.
     - `font_path`: Ruta del archivo de fuente.
     - `status_callback`: Función de devolución de llamada para reportar el estado de procesamiento.
     - `expo_id`: Identificador de la exposición.
   - Se llama a `image_processor.process_all_images()`.
     - **`ImageProcessor.__init__(self, expo_dir, font_path, status_callback, expo_id)`**: Inicializa el objeto y prepara el entorno de trabajo, asegurándose de que la carpeta `ficheros_salida` exista.
     - **`ImageProcessor.process_all_images()`**: Procesa todas las imágenes listadas en el archivo Excel (`Resumen obras.xlsx`). Los pasos en este método incluyen:
       - Cargar el archivo Excel con la información de las imágenes.
       - Iterar sobre cada fila del archivo y llamar a `process_image` para procesar cada imagen individualmente.
         - **`process_image(row)`**: Este método realiza las siguientes acciones:
           - Personaliza la imagen añadiendo un fondo negro, el nombre del artista, el título de la obra y un código QR con un enlace proporcionado.
           - Ajusta el tamaño de la imagen original y la centra en el fondo.
           - Renombra la imagen con el formato de exposición (`expo_id_PXXX_nombreoriginal`).
           - Guarda la imagen procesada en la carpeta `ficheros_salida`, preservando los metadatos originales y utilizando el formato adecuado.

8. **Comprimir el contenido procesado en un archivo ZIP**:
   - La carpeta `ficheros_salida`, que contiene las imágenes procesadas, se comprime en un archivo ZIP con el nombre `expo_id.zip`.
   - **`FileManager.compress_output(source_dir, output_filename)`**: Este método comprime el contenido del directorio `source_dir` y lo guarda en `output_filename`.

9. **Finalización del programa**:
   - Se imprime un mensaje indicando que el procesamiento de imágenes ha finalizado.








## Tareas pendientes

**Módulo de Descarga:**
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



**ExcelProcessor**
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










https://drive.google.com/drive/folders/10oBtG589CN11SVtVfGqo7YHQwhU4K7m8



995 Artista con obras en imágenes: 18V_oct_SARA VÁZQUEZ__E016-20241016T090443Z-001
https://drive.google.com/drive/folders/1kf6xoSjxvcPbaA68JuyCLwy2ly2zh0wC?usp=sharing


994 Artista con obras en vídeo: 05S_oct_ROBERT TIRADO_E013
https://drive.google.com/drive/folders/12vT5mYn4ltauJbrOT3GURQETJRjnFLwa?usp=sharing

993 Artista con obras en vídeo: 12S_oct_ANDRÉS L. CALLE_E014
https://drive.google.com/drive/folders/1noBujfH18Snf4vwFoMMKOi6x8hng4nOh?usp=sharing

992 Artista con obras en vídeo: 06V_sep_Ramón_Redondo_E001
https://drive.google.com/drive/folders/1GUNXoYCGFZc3BPuy4fkv8pQ_GOF9-Z54?usp=sharing


E991 Artista con obras en video: 19S_oct_PÁJARO NEGRO__E017 (Ojo, es muy grande. Me lo descargó en varios zip y tuve que unir a mano y comprimir después)
https://drive.google.com/drive/folders/1ehmehBOT0mLrs2no00xFheGmxr_XRgRx?usp=sharing






Los archivo a visualizarse en nuestras pantallas deben entregarse en los siguientes formatos:


ARCHIVO DE IMÁGEN
. Imagen en fichero formato PNG, JPEG (alta calidad).
. Resolución 2160x3840 píxeles (formato pantalla vertical) y 3840x2160 píxeles (formato pantalla horizontal), a 72pp.
. El formato de la imagen no tiene por qué coincidir con el de la pantalla, en ese caso se rellenará con un fondo negro.
Espacio de Color:
Ideal: sRGB para mantener consistencia en la visualización en los displays.
Profundidad de Color:
Requerida: 8 bits por canal



ARCHIVO DE VÍDEO
.Formato de imagen: 2160x3840 píxeles (formato pantalla vertical) y 3840x2160 píxeles (formato pantalla horizontal)
.Formato: MP4 .
.Frames por segundo: Max 30FPS ¡Importante!
.Codec: H.265 VBR (Para mejor visualización) o H. 264.
.Velocidad de bits: 30-60 Mbps.
Si se quiere el efecto de loop en el video tiene que empezar y acabar con el mismo frame. (bucle continuo).
Tamaño del Archivo:
Recomendación: Mantener archivos de imagen debajo de 100 MB para una buena gestión de las obras.




Advanced Tag/Screen Management
Users of the Pand X Series can now import and export Tag sets created in Excel for each workspace and pre-assign tags to each screen when creating an Excel file for Multi-Screen Enrollment.