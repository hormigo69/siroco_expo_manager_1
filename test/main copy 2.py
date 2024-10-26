import os
import glob
import shutil
import re
import pandas as pd
from PIL import Image, ExifTags
import subprocess
import json

#activar el entorno virtual
#source venv/bin/activate   

class FileManager:
    @staticmethod
    #Asegura que la carpeta exista, si no, la crea
    def ensure_directory(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def unzip_output(zip_path, output_path):
        import zipfile
        import os

        obras_path = os.path.join(output_path, 'Obras')
        os.makedirs(obras_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.startswith('__MACOSX') or file_info.filename.startswith('.'):
                    continue  # Skip macOS-specific files and hidden files
                
                # Remove the root folder name if it exists
                parts = file_info.filename.split('/', 1)
                if len(parts) > 1:
                    relative_path = parts[1]
                else:
                    relative_path = file_info.filename

                # Skip empty filenames or directories
                if not relative_path or relative_path.endswith('/'):
                    continue

                # Extract the file
                target_path = os.path.join(obras_path, relative_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                try:
                    with zip_ref.open(file_info) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    print(f"Error extracting {file_info.filename}: {str(e)}")

        print(f"Contenido descomprimido en: {obras_path}")


    @staticmethod
    #Copia los ficheros de la carpeta origen a la carpeta destino, renombrando los ficheros según el formato de la pantalla
    def process_files(carpeta_origen, carpeta_destino, id_expo):
        FileManager.ensure_directory(carpeta_destino)
        varios_folder = os.path.join(carpeta_destino, 'varios')
        FileManager.ensure_directory(varios_folder)
        
        for root, _, files in os.walk(carpeta_origen):
            for file_name in files:
                if file_name == '.DS_Store':
                    continue
                
                file_path = os.path.join(root, file_name)
                parent_folder = os.path.basename(os.path.dirname(file_path))
                
                if parent_folder.startswith('PANTALLA'):
                    pantalla_num = parent_folder.split()[1].zfill(3)
                    new_file_name = f"{id_expo}_P{pantalla_num}_{file_name}"
                    new_file_path = os.path.join(carpeta_destino, new_file_name)
                else:
                    new_file_path = os.path.join(varios_folder, file_name)
                
                try:
                    shutil.copy2(file_path, new_file_path)
                except Exception as e:
                    print(f"Error al copiar {file_path}: {str(e)}")

    @staticmethod
    #Mueve los ficheros que no coinciden con el formato de la pantalla a la carpeta varios
    def move_non_matching_files(carpeta_destino, varios_folder, expo_id):
        patron = re.compile(f"^{expo_id}_P\d{{3}}_")
        for file in os.listdir(carpeta_destino):
            file_path = os.path.join(carpeta_destino, file)
            if os.path.isfile(file_path) and not patron.match(file):
                destino = os.path.join(varios_folder, file)
                try:
                    shutil.move(file_path, destino)
                except Exception as e:
                    print(f"Error al mover {file}: {str(e)}")

    @staticmethod
    def is_video(file_path):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        return any(file_path.lower().endswith(ext) for ext in video_extensions)

class ImageInfo:
    @staticmethod
    def get_image_info(file_path):
        '''
        Obtiene la información de una imagen individual.
        '''
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                dpi = img.info.get('dpi', (None, None))
                img_format = img.format
                file_size = os.path.getsize(file_path)
                #convierte a KB
                file_size_kb = file_size / 1024
                #convierte a MB
                #file_size_mb = file_size / (1024 * 1024)  # Convertir a MB
                
                # Determinar orientación
                orientation = 'H' if width > height else 'V'
                
                # Intentar obtener DPI desde los metadatos EXIF si no está disponible
                if (dpi[0] is None or dpi[1] is None) and hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = ExifTags.TAGS.get(tag_id, tag_id)
                            if tag == 'XResolution':
                                dpi_x = value[0] / value[1] if isinstance(value, tuple) else value
                            elif tag == 'YResolution':
                                dpi_y = value[0] / value[1] if isinstance(value, tuple) else value
                        dpi = (dpi_x, dpi_y)
                
                return {
                    'ANCHO': width,
                    'ALTO': height,
                    'RESOLUCION_X': dpi[0],
                    'RESOLUCION_Y': dpi[1],
                    'ORIENTACION': orientation,
                    'FORMATO': img_format,
                    'TAMAÑO_MB': round(file_size_kb, 2)  # Redondear a 2 decimales
                }
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
            return None

    @staticmethod
    def get_images_info_from_directory(directory_path):
        '''
        Recorre solo el directorio raíz especificado y crea un DataFrame con las características de las imágenes.
        '''
        images_info = []
        
        for file_name in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file_name)
            
            # Ignorar subdirectorios
            if os.path.isdir(file_path):
                continue
            
            # Intentar abrir el archivo como imagen
            try:
                with Image.open(file_path):
                    pass  # Si no lanza una excepción, es una imagen
            except IOError:
                # No es una imagen o está corrupta
                print(f"Archivo no es una imagen o está corrupto: {file_path}")
                continue
            
            # Obtener información de la imagen
            info = ImageInfo.get_image_info(file_path)
            if info:
                info['NOMBRE_ARCHIVO'] = file_name
                
                # Extraer el número de pantalla
                match = re.search(r'_P(\d{3})_', file_name)
                if match:
                    info['NUMERO_PANTALLA'] = int(match.group(1))
                else:
                    info['NUMERO_PANTALLA'] = None
                
                images_info.append(info)
    
        return pd.DataFrame(images_info)

class VideoInfo:
    @staticmethod
    def get_video_info(file_path):
        '''
        Obtiene la información de un archivo de video usando ffprobe.
        '''
        try:
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path], 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            probe = json.loads(result.stdout)
            
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            
            if video_stream:
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                re
                orientation = 'H' if width > height else 'V'
                frame_rate = eval(video_stream['r_frame_rate'])
                duration = float(probe['format']['duration'])
                #duración en segundos
                duration_seconds = int(duration)
                bit_rate = int(probe['format']['bit_rate'])
                video_codec = video_stream['codec_name']
                # Extraer el formato basado en la extensión del archivo
                file_extension = os.path.splitext(file_path)[1][1:].lower()

                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)  # Convertir a MB

                return {
                    'ANCHO': width,
                    'ALTO': height,
                    'ORIENTACION': orientation,
                    'DURACION_SEG': duration_seconds,
                    'FPS': frame_rate,
                    #'FORMATO': probe['format']['format_name'],
                    'FORMATO': file_extension,
                    'TAMAÑO_MB': round(file_size_mb, 2),
                    'TASA_BITS': bit_rate,
                    'CÓDEC_VIDEO': video_codec,
                    'NOMBRE_ARCHIVO': os.path.basename(file_path)
                }
        except Exception as e:
            print(f"Error procesando el video {file_path}: {e}")
            return None

def get_file_info(file_path):
    if FileManager.is_video(file_path):
        info = VideoInfo.get_video_info(file_path)
        if info:
            info['TIPO'] = 'Video'
        return info
    else:
        info = ImageInfo.get_image_info(file_path)
        if info:
            info['TIPO'] = 'Imagen'
        return info

def get_files_info_from_directory(directory_path):
    files_info = []
    
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        
        # Ignorar subdirectorios
        if os.path.isdir(file_path):
            continue
        
        # Obtener información del archivo
        info = get_file_info(file_path)
        if info:
            info['NOMBRE_ARCHIVO'] = file_name
            
            # Extraer el número de pantalla
            match = re.search(r'_P(\d{3})_', file_name)
            if match:
                info['NUMERO_PANTALLA'] = int(match.group(1))
            else:
                info['NUMERO_PANTALLA'] = None
            
            files_info.append(info)

    df = pd.DataFrame(files_info)
    if df.empty:
        print("No se pudo procesar ningún archivo correctamente.")
        return pd.DataFrame(columns=['NOMBRE_ARCHIVO', 'NUMERO_PANTALLA'])
    return df

class ExpoProcessor:
    def __init__(self, expo_id):
        self.expo_id = expo_id
        self.output_folder = expo_id
        self.full_output_path = os.path.join(os.getcwd(), 'expos', self.output_folder)
        self.carpeta_origen = os.path.join(self.full_output_path, 'Obras')
        self.carpeta_destino = os.path.join(self.full_output_path, 'ficheros_salida')
        self.varios_folder = os.path.join(self.carpeta_destino, 'varios')

    def setup_directories(self):
        FileManager.ensure_directory(os.path.join(self.full_output_path, 'Obras'))
        FileManager.ensure_directory(os.path.join(self.full_output_path, 'ficheros_salida'))
        FileManager.ensure_directory(self.varios_folder)

    def unzip_files(self):
        zip_files = glob.glob(os.path.join(self.full_output_path, "*.zip"))
        if zip_files:
            zip_path = zip_files[0]
            print(f"Archivo zip encontrado: {zip_path}")
            FileManager.unzip_output(zip_path, self.full_output_path)
        else:
            print("No se encontraron archivos .zip en la carpeta.")

    def process_and_move_files(self):
        FileManager.process_files(self.carpeta_origen, self.carpeta_destino, self.expo_id)
        FileManager.move_non_matching_files(self.carpeta_destino, self.varios_folder, self.expo_id)
        shutil.rmtree(self.carpeta_origen)
        print("Proceso de movimiento de archivos completado.")

    def generate_summary(self):
        df = get_files_info_from_directory(self.carpeta_destino)
        
        if not df.empty:
            if 'NUMERO_PANTALLA' in df.columns:
                df = df.sort_values('NUMERO_PANTALLA')
            
            df.to_excel(os.path.join(self.full_output_path, 'Resumen obras.xlsx'), index=False)
            print("Proceso de resumen de archivos completado.")
        else:
            print("No se encontraron archivos para procesar.")

class Recodificador:
    def __init__(self, expo_id):
        self.expo_id = expo_id
        self.full_output_path = os.path.join(os.getcwd(), 'expos', self.expo_id)
        self.carpeta_origen = os.path.join(self.full_output_path, 'ficheros_salida')
        self.carpeta_destino = os.path.join(self.full_output_path, 'procesados')
        self.excel_path = os.path.join(self.full_output_path, 'Resumen obras.xlsx')

    def crear_carpeta_procesados(self):
        if not os.path.exists(self.carpeta_destino):
            os.makedirs(self.carpeta_destino)
            print(f"Carpeta '{self.carpeta_destino}' creada.")
        else:
            print(f"La carpeta '{self.carpeta_destino}' ya existe.")

    def procesar_archivos(self):
        total_archivos = len(os.listdir(self.carpeta_origen))
        archivos_procesados = 0

        for archivo in os.listdir(self.carpeta_origen):
            ruta_archivo = os.path.join(self.carpeta_origen, archivo)
            
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.procesar_imagen(ruta_archivo)
            elif archivo.lower().endswith('.mp4'):
                self.procesar_video(ruta_archivo)
            
            archivos_procesados += 1
            print(f"Progreso: {archivos_procesados}/{total_archivos} archivos procesados")

    def procesar_imagen(self, ruta_archivo):
        try:
            with Image.open(ruta_archivo) as img:
                ancho, alto = img.size
                formato = img.format
                modo = img.mode

                necesita_procesamiento = False

                if formato not in ['PNG', 'JPEG'] or modo != 'RGB':
                    necesita_procesamiento = True

                if necesita_procesamiento:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    nuevo_nombre = os.path.splitext(os.path.basename(ruta_archivo))[0] + '_procesado.jpg'
                    ruta_destino = os.path.join(self.carpeta_destino, nuevo_nombre)
                    img.save(ruta_destino, 'JPEG', quality=95)
                    print(f"Imagen procesada: {nuevo_nombre}")
                else:
                    nuevo_nombre = os.path.basename(ruta_archivo)
                    ruta_destino = os.path.join(self.carpeta_destino, nuevo_nombre)
                    shutil.copy2(ruta_archivo, ruta_destino)
                    print(f"Imagen copiada sin procesar: {nuevo_nombre}")

        except Exception as e:
            print(f"Error al procesar la imagen {os.path.basename(ruta_archivo)}: {str(e)}")

    def procesar_video(self, ruta_archivo):
        try:
            probe = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', ruta_archivo], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            info = json.loads(probe.stdout)
            
            video_stream = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
            
            if video_stream:
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                fps = eval(video_stream['r_frame_rate'])
                codec = video_stream['codec_name']
                
                necesita_procesamiento = False
                
                if (width, height) not in [(2160, 3840), (3840, 2160)] or fps > 30 or codec not in ['hevc', 'h264']:
                    necesita_procesamiento = True
                
                bitrate = int(info['format']['bit_rate'])
                if bitrate < 30_000_000 or bitrate > 60_000_000:
                    necesita_procesamiento = True
                
                if necesita_procesamiento:
                    nuevo_nombre = os.path.splitext(os.path.basename(ruta_archivo))[0] + '_procesado.mp4'
                    ruta_destino = os.path.join(self.carpeta_destino, nuevo_nombre)
                    
                    new_size = '3840:2160' if width > height else '2160:3840'
                    
                    cmd = [
                        'ffmpeg', '-i', ruta_archivo,
                        '-c:v', 'libx265',
                        '-preset', 'medium',
                        '-crf', '23',
                        '-vf', f'fps=30,scale={new_size}',
                        '-c:a', 'aac',
                        '-b:v', '45M',
                        '-maxrate', '60M',
                        '-bufsize', '60M',
                        '-tag:v', 'hvc1',
                        ruta_destino
                    ]
                    
                    print(f"Procesando video: {nuevo_nombre}")
                    subprocess.run(cmd, check=True)
                    print(f"Video procesado: {nuevo_nombre}")
                else:
                    nuevo_nombre = os.path.basename(ruta_archivo)
                    ruta_destino = os.path.join(self.carpeta_destino, nuevo_nombre)
                    shutil.copy2(ruta_archivo, ruta_destino)
                    print(f"Video copiado sin procesar: {nuevo_nombre}")
        
        except subprocess.CalledProcessError as e:
            print(f"Error al procesar el video {os.path.basename(ruta_archivo)}: {str(e)}")
            print(f"Comando que causó el error: {' '.join(cmd)}")
        except Exception as e:
            print(f"Error inesperado al procesar el video {os.path.basename(ruta_archivo)}: {str(e)}")

    def actualizar_excel(self):
        try:
            # Leer el Excel existente
            df = pd.read_excel(self.excel_path)
            
            # Obtener información actualizada de los archivos procesados
            archivos_procesados = get_files_info_from_directory(self.carpeta_destino)
            
            # Crear un diccionario para mapear nombres de archivo a sus nuevos datos
            nuevos_datos = {row['NOMBRE_ARCHIVO']: row for _, row in archivos_procesados.iterrows()}
            
            # Actualizar el DataFrame original con los nuevos datos
            for index, row in df.iterrows():
                nombre_archivo = row['NOMBRE_ARCHIVO']
                nombre_procesado = nombre_archivo.replace('.', '_procesado.')
                
                if nombre_procesado in nuevos_datos:
                    for columna in df.columns:
                        if columna in nuevos_datos[nombre_procesado]:
                            df.at[index, columna] = nuevos_datos[nombre_procesado][columna]
                
                # Añadir una columna para indicar si el archivo fue procesado
                df.at[index, 'PROCESADO'] = 'Sí' if nombre_procesado in nuevos_datos else 'No'
            
            # Guardar el DataFrame actualizado en el mismo archivo Excel
            df.to_excel(self.excel_path, index=False)
            print(f"Excel actualizado: {self.excel_path}")
        
        except Exception as e:
            print(f"Error al actualizar el Excel: {str(e)}")

def main():
    expo_id = 'E990'
    processor = ExpoProcessor(expo_id)
    
    processor.setup_directories()
    processor.unzip_files()
    processor.process_and_move_files()
    processor.generate_summary()

    # Proceso de recodificación
    recodificador = Recodificador(expo_id)
    recodificador.crear_carpeta_procesados()
    recodificador.procesar_archivos()
    recodificador.actualizar_excel()

if __name__ == "__main__":
    main()
