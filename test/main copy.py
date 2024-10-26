import os
import sys
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

def main():
    expo_id = 'E990'
    output_folder = expo_id
    full_output_path = os.path.join(os.getcwd(), 'expos', output_folder)

    #Asegura que las carpetas existan, si no, las crea
    FileManager.ensure_directory(os.path.join(full_output_path, 'Obras'))
    FileManager.ensure_directory(os.path.join(full_output_path, 'ficheros_salida'))

    #Busca el archivo zip en la carpeta y lo descomprime
    zip_files = glob.glob(os.path.join(full_output_path, "*.zip"))
    if zip_files:
        zip_path = zip_files[0]
        print(f"Archivo zip encontrado: {zip_path}")
        FileManager.unzip_output(zip_path, full_output_path)
    else:
        print("No se encontraron archivos .zip en la carpeta.")

    carpeta_origen = os.path.join(full_output_path, 'Obras')
    carpeta_destino = os.path.join(full_output_path, 'ficheros_salida')
    
    FileManager.process_files(carpeta_origen, carpeta_destino, expo_id)

    varios_folder = os.path.join(full_output_path, 'ficheros_salida', 'varios')
    FileManager.ensure_directory(varios_folder)

    FileManager.move_non_matching_files(carpeta_destino, varios_folder, expo_id)

    shutil.rmtree(os.path.join(full_output_path, 'Obras'))

    print("Proceso de movimiento de archivos completado.")

    # Extrae la información de las imágenes y videos
    # Crear un DataFrame vacío con las columnas necesarias
    columnas = [
        'NUMERO_PANTALLA', 'NOMBRE_ARCHIVO', 'TIPO', 'ANCHO', 'ALTO', 'ORIENTACION',
        'FORMATO','TAMAÑO_MB', 'RESOLUCION_X', 'RESOLUCION_Y', 'DURACION_SEG', 
        'FPS', 'TASA_BITS', 'CÓDEC_VIDEO', 'CÓDEC_AUDIO'
    ]

    df = pd.DataFrame(columns=columnas)
    # relleno el df con la info de las imágenes y videos
    df = pd.concat([df, get_files_info_from_directory(carpeta_destino)])
    
    # Ordena el DataFrame por número de pantalla si la columna existe
    if 'NUMERO_PANTALLA' in df.columns:
        df = df.sort_values('NUMERO_PANTALLA')
    
    # Guarda el dataframe en un excel
    df.to_excel(os.path.join(full_output_path, 'Resumen obras.xlsx'), index=False)

    print("Proceso de resumen de archivos completado.")


if __name__ == "__main__":
    main()
