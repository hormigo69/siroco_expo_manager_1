# Descripción de la aplicación Expo Manager

Esta aplicación está diseñada para automatizar y facilitar el procesamiento de galerías de imágenes y vídeos destinadas a una aplicación de cartelería digital. La aplicación se centra en la gestión eficiente de obras artísticas, permitiendo a los usuarios revisar y preparar contenido visual para su despliegue en pantallas de diferentes formatos.


### Configuración Inicial:
Activa un entorno virtual (comentado en el código, indica que esto se puede hacer externamente).

### Gestión de Archivos:
FileManager: Descomprime archivos ZIP, asegura la existencia de directorios, copia y mueve archivos entre carpetas, y verifica si un archivo es un video.
ImageInfo y VideoInfo: Obtienen metadatos de imágenes y videos, como dimensiones, resolución, formato, y tamaño.

### Procesamiento de Exposiciones:
ExpoProcessor: Coordina el flujo de procesamiento de las exposiciones. Esto incluye preparar directorios, descomprimir archivos, procesar y mover archivos a carpetas adecuadas, generar resúmenes en formato Excel.
Recodificador: Procesa y ajusta imágenes y videos a especificaciones requeridas antes de su despliegue.

### Interfaz Web con Flask:
Sirve una interfaz web para interactuar con el sistema, permitiendo cargar, procesar y desplegar los archivos.
Maneja rutas para cargar imágenes, procesar exposiciones y recodificar archivos.

### Procesamiento Paralelo:
Utiliza ThreadPoolExecutor para procesar archivos de manera concurrente, optimizando el uso de recursos del sistema.

### Almacenamiento de Resultados:
Guarda un resumen de los archivos procesados en un archivo Excel, incluyendo metadatos sobre cada archivo y el estado del procesamiento.

### Interfaz de Usuario (index.html):
Proporciona una página HTML que sirve de interfaz de usuario para mostrar resultados, cargar ficheros, y posiblemente interactuar para manejo y visualización de imágenes y videos.


## Pasos que realiza `main`:
En conjunto, `main.py` proporciona una robusta funcionalidad para la preparación automática de multimedia para exposiciones digitales, asegurando gestionar los ficheros de manera ordenada y conforme a especificaciones técnicas requeridas.


### Principales Componentes y Funcionalidades

#### 1. FileManager:
- **ensure_directory(path)**: Verifica la existencia de un directorio y lo crea si no está presente.
- **unzip_output(zip_path, output_path)**: Descomprime archivos ZIP en un directorio especificado, ignorando archivos de sistema no deseados (e.g., `__MACOSX`).
- **process_files(carpeta_origen, carpeta_destino, id_expo)**: Copia archivos de una carpeta origen a un destino, renombrando los que cumplen con ciertas condiciones.
- **move_non_matching_files(carpeta_destino, varios_folder, expo_id)**: Mueve archivos que no cumplen con el formato esperado a una carpeta designada.
- **is_video(file_path)**: Determina si un archivo es un video basado en su extensión.

#### 2. ImageInfo:
- **get_image_info(file_path)**: Extrae información de una imagen, como tamaño, formato, resolución y orientación.
- **get_images_info_from_directory(directory_path)**: Recolecta información de todas las imágenes en un directorio y las compila en un `DataFrame` de pandas.

#### 3. VideoInfo:
- **get_video_info(file_path)**: Utiliza `ffprobe` para obtener información técnica detallada de un video.

#### 4. Funciones Generales:
- **get_file_info(file_path)**: Clasifica un archivo como imagen o video y obtiene información detallada.
- **get_files_info_from_directory(directory_path)**: Compila un `DataFrame` con la información de todos los archivos en un directorio.

#### 5. ExpoProcessor:
- Inicializa las rutas necesarias y organiza el procesamiento completo de archivos de una exposición, incluyendo descomprimir archivos ZIP y mover los archivos a sus directorios correctos.
- **generate_summary()**: Crea un reporte en Excel de los archivos procesados, incluyendo la creación de tablas con formato.

####   6. Recodificador:
- Procesa archivos asegurando que cumplan con las especificaciones necesarias para la visualización.
- **procesar_imagen** y **procesar_video**: Procesa cada imagen o video para garantizar que cumplen con los requisitos preestablecidos en cuanto a resolución y formato.
- **actualizar_excel()**: Actualiza el archivo Excel de resumen con la nueva información después del procesamiento.

---

### Flujo Principal (`main()`):

1. **Gestión de Exposiciones**: Identifica exposiciones por su ID (`expo_id`), establece el entorno de trabajo, y ejecuta el procesamiento de archivos, ya sea inicial o reprocesamiento si es necesario.

2. **Procesamiento Condicional**: Si se detectan archivos previamente procesados, el programa pregunta si se deben reprocesar, ofreciendo solo actualizar el resumen en Excel si es elegido no reprocesar.

3. **Recodificación**: Después del procesamiento inicial, realiza una recodificación de los archivos para ajustarse a requerimientos específicos de visualización.

---




### Pasos que realiza `app`:

En conjunto, `app.py` actúa como un puente entre la lógica de procesamiento de archivos en `main.py` y la interfaz con la que interactúa el usuario final. Facilita el flujo de trabajo al proporcionar una forma estructurada y accesible para gestionar exposiciones, permitiendo cargar, procesar y visualizar archivos multimedia de manera eficiente y organizada.

---

### Principales Componentes y Funcionalidades

#### 1. Inicialización de Flask:
- **Flask Application**: Se inicializa una aplicación Flask con soporte para CORS mediante la biblioteca `flask_cors`.
- **Configuración de Directorios**: Se especifica la carpeta de plantillas.

#### 2. Funciones Auxiliares:
- **get_thumbnail(image_path, size=(200, 200))**: Genera una miniatura en base64 de una imagen para visualización rápida en la web.
- **convert_to_serializable(obj)**: Convierte objetos no serializables a tipos básicos de Python para que puedan ser enviados en respuestas JSON.

#### 3. Rutas de la Aplicación:
- **/** (*index*): Devuelve la plantilla `index.html`, sirviendo como la página principal de la aplicación.
- **/load_images**: Carga imágenes de una exposición especificada. Busca archivos en `ficheros_salida`, proporcionando información de cada archivo o localizando archivos ZIP para descomprimir.
- **/expos/<expo_id>/ficheros_salida/<filename>**: Sirve archivos estáticos desde el directorio de salida.
- **/process_expo**: Procesa una exposición. Descomprime y organiza archivos si se proporcionan archivos ZIP.
- **/get_images/<expo_id>**: Obtiene y retorna información de imágenes procesadas de una exposición.
- **/recodificar**: Recodifica archivos multimedia según el ID de exposición, utilizando la lógica definida en `Recodificador`.

#### 4. Funcionalidad de Backend:
- **Interfaz con el Procesador**: El archivo utiliza clases y métodos definidos en `main.py`, como `ExpoProcessor`, `ImageInfo`, `VideoInfo` y `Recodificador`, para realizar operaciones de procesamiento y brindar información procesada al front-end.

#### 5. Ejemplo de Desarrollo y Depuración:
- Se configura para ejecutarse en modo debug, lo cual facilita la detección de problemas durante el desarrollo.

---

### Pasos que realiza `index.html`:










### Ficheros de prueba


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


E998 video e imágenes: 25V_oct_FERNANDO NAVAJO__E018
https://drive.google.com/drive/folders/1k_hvDLX_WnXMR_fsI3WXxE_ejfGhgTxP?usp=sharing



### Parámetros de visualización
Los archivo a visualizarse en nuestras pantallas deben entregarse en los siguientes formatos:


#### ARCHIVO DE IMÁGEN
. Imagen en fichero formato PNG, JPEG (alta calidad).
. Resolución 2160x3840 píxeles (formato pantalla vertical) y 3840x2160 píxeles (formato pantalla horizontal), a 72pp.
. El formato de la imagen no tiene por qué coincidir con el de la pantalla, en ese caso se rellenará con un fondo negro.
Espacio de Color:
Ideal: sRGB para mantener consistencia en la visualización en los displays.
Profundidad de Color:
Requerida: 8 bits por canal



#### ARCHIVO DE VÍDEO
.Formato de imagen: 2160x3840 píxeles (formato pantalla vertical) y 3840x2160 píxeles (formato pantalla horizontal)
.Formato: MP4 .
.Frames por segundo: Max 30FPS ¡Importante!
.Codec: H.265 VBR (Para mejor visualización) o H. 264.
.Velocidad de bits: 30-60 Mbps.
Si se quiere el efecto de loop en el video tiene que empezar y acabar con el mismo frame. (bucle continuo).
Tamaño del Archivo:
Recomendación: Mantener archivos de imagen debajo de 100 MB para una buena gestión de las obras.

Los tamaños aproximados por minuto para cada configuración:

H.265 (HEVC):

A 30 Mbps: aproximadamente 225 MB por minuto.
A 60 Mbps: aproximadamente 450 MB por minuto.
H.264:

A 30 Mbps: aproximadamente 337.5 MB por minuto.
A 60 Mbps: aproximadamente 675 MB por minuto.









29/10 19h
Falta:
[x] Recodificar los vídeos y comprobar que funcionan bien
   [x] Comprobar que recodifica bien los archivos
      [x] dimensiones
      [x] fps
      [x] codec
      [x] tamaño
[x] calcular el tamaño correcto de los archivos teniendo en cuenta el codec y los segundos de duración

[ ] Mover los archivos de procesados a ficheros, salida
[ ] Recargar el Front para que se vean los archivos y los datos después de procesar
[ ] Añadir una barra de proceso mientras se decodifica los archivos


- faltan tb algunos arreglos en el Front, como 
[x] poner el logotipo
[x] hacer que el botón de cargar imágenes solo se vea cuando el foco esté en el input
[ ] añadir un botón que nos abra el Finder en la carpeta con los archivos procesados. 
