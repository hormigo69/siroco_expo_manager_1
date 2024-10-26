import os
import glob
import shutil
import re
import pandas as pd
from PIL import Image, ExifTags
import subprocess
import json
import concurrent.futures
from tqdm import tqdm
import time
import platform
import sys
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo


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

        # Buscar todos los archivos zip en la carpeta
        zip_files = glob.glob(os.path.join(output_path, "*.zip"))
        
        for zip_path in zip_files:
            print(f"Procesando archivo zip: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.startswith('__MACOSX') or file_info.filename.startswith('.'):
                        continue  # Saltar archivos específicos de macOS y archivos ocultos
                    
                    # Mantener la estructura de carpetas interna
                    target_path = os.path.join(obras_path, file_info.filename)
                    
                    # Saltar directorios vacíos
                    if file_info.filename.endswith('/'):
                        continue

                    # Extraer el archivo
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    try:
                        with zip_ref.open(file_info) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                    except Exception as e:
                        print(f"Error al extraer {file_info.filename}: {str(e)}")

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
        # Importar las librerías necesarias
        from openpyxl import load_workbook
        from openpyxl.worksheet.table import Table, TableStyleInfo

        df = get_files_info_from_directory(self.carpeta_destino)
        
        if not df.empty:
            if 'NUMERO_PANTALLA' in df.columns:
                df = df.sort_values('NUMERO_PANTALLA')
            
            excel_path = os.path.join(self.full_output_path, 'Resumen obras.xlsx')
            
            # Guardar primero con pandas
            df.to_excel(excel_path, index=False)
            
            # Abrir el archivo con openpyxl para añadir el formato de tabla
            wb = load_workbook(excel_path)
            ws = wb.active
            
            # Obtener el rango de la tabla
            tabla_ref = f"A1:{chr(64 + len(df.columns))}{len(df.index) + 1}"
            
            # Crear la tabla con estilo
            tabla = Table(displayName="TablaObras", ref=tabla_ref)
            estilo = TableStyleInfo(
                name="TableStyleMedium2", 
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False
            )
            tabla.tableStyleInfo = estilo
            
            # Añadir la tabla a la hoja
            ws.add_table(tabla)
            
            # Ajustar el ancho de las columnas
            for column in ws.columns:
                max_length = 0
                column = list(column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column[0].column_letter].width = adjusted_width
            
            # Guardar los cambios
            wb.save(excel_path)
            print("Proceso de resumen de archivos completado con formato de tabla.")
        else:
            print("No se encontraron archivos para procesar.")

class Recodificador:
    def __init__(self, expo_id):
        self.expo_id = expo_id
        self.full_output_path = os.path.join(os.getcwd(), 'expos', self.expo_id)
        self.carpeta_origen = os.path.join(self.full_output_path, 'ficheros_salida')
        self.carpeta_destino = os.path.join(self.full_output_path, 'procesados')
        self.excel_path = os.path.join(self.full_output_path, 'Resumen obras.xlsx')
        # Optimización para Mac: usar cores efectivos
        self.max_workers = max(1, min(os.cpu_count() - 1, 4))

    def crear_carpeta_procesados(self):
        if not os.path.exists(self.carpeta_destino):
            os.makedirs(self.carpeta_destino)
            print(f"Carpeta '{self.carpeta_destino}' creada.")
        else:
            # Verificar si la carpeta tiene contenido
            if os.listdir(self.carpeta_destino):
                respuesta = input("La carpeta 'procesados' ya existe y contiene archivos. ¿Desea volver a procesar los archivos? (s/n): ")
                if respuesta.lower() != 's':
                    print("Saltando el proceso de recodificación...")
                    return False
            print(f"La carpeta '{self.carpeta_destino}' ya existe.")
        return True

    def procesar_archivos(self):
        archivos = os.listdir(self.carpeta_origen)
        total_archivos = len(archivos)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for archivo in archivos:
                ruta_archivo = os.path.join(self.carpeta_origen, archivo)
                if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                    futures.append(executor.submit(self.procesar_imagen, ruta_archivo))
                elif archivo.lower().endswith('.mp4'):
                    futures.append(executor.submit(self.procesar_video, ruta_archivo))

            with tqdm(total=total_archivos, desc="Progreso global") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    pbar.update(1)

    def procesar_imagen(self, ruta_archivo):
        nombre_archivo = os.path.basename(ruta_archivo)
        with tqdm(total=1, desc=f"Procesando imagen: {nombre_archivo}", leave=False) as pbar:
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
                        print(f" Imagen copiada sin procesar: {nuevo_nombre}")

                time.sleep(0.1)  # Simulación de procesamiento
                pbar.update(1)
            except Exception as e:
                print(f"Error al procesar la imagen {os.path.basename(ruta_archivo)}: {str(e)}")
            return nombre_archivo

    def procesar_video(self, ruta_archivo):
        try:
            nombre_archivo = os.path.basename(ruta_archivo)
            with tqdm(total=100, desc=f"Procesando video: {nombre_archivo}", leave=False) as pbar:
                # Verificar si es Mac con Apple Silicon
                is_apple_silicon = platform.processor() == 'arm'
                
                probe = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                                     '-show_format', '-show_streams', ruta_archivo], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                info = json.loads(probe.stdout)
                
                video_stream = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
                
                if video_stream:
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    fps = eval(video_stream.get('r_frame_rate', '0/1'))
                    codec = video_stream.get('codec_name', '')
                    
                    necesita_procesamiento = False
                    if (width, height) not in [(2160, 3840), (3840, 2160)] or fps > 30 or codec not in ['hevc', 'h264']:
                        necesita_procesamiento = True
                    
                    bitrate = info['format'].get('bit_rate', 'N/A')
                    if bitrate != 'N/A':
                        bitrate = int(bitrate)
                        if bitrate < 30_000_000 or bitrate > 60_000_000:
                            necesita_procesamiento = True
                    else:
                        necesita_procesamiento = True
                    
                    if necesita_procesamiento:
                        nuevo_nombre = os.path.splitext(nombre_archivo)[0] + '_procesado.mp4'
                        ruta_destino = os.path.join(self.carpeta_destino, nuevo_nombre)
                        
                        new_size = '3840:2160' if width > height else '2160:3840'
                        
                        # Configuración base de FFmpeg
                        cmd = [
                            'ffmpeg', '-i', ruta_archivo,
                            '-vf', f'fps=30,scale={new_size}:flags=bicubic',
                            '-c:a', 'aac',
                            '-b:v', '45M',
                            '-maxrate', '60M',
                            '-bufsize', '60M',
                            '-movflags', '+faststart',
                            '-progress', 'pipe:1'
                        ]

                        # Configuración específica para Mac
                        if is_apple_silicon:
                            # Usar el codificador de hardware de Apple Silicon
                            cmd.extend([
                                '-c:v', 'hevc_videotoolbox',
                                '-allow_sw', '1',
                                '-q:v', '50',  # Calidad para VideoToolbox (0-100, mayor es mejor)
                                '-tag:v', 'hvc1'
                            ])
                        else:
                            # Para Mac Intel usar libx265 optimizado
                            cmd.extend([
                                '-c:v', 'libx265',
                                '-preset', 'medium',
                                '-crf', '23',
                                '-x265-params', f'pools=*:frame-threads={self.max_workers}',
                                '-tag:v', 'hvc1'
                            ])

                        cmd.append(ruta_destino)
                        
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                                 universal_newlines=True)
                        
                        duration = float(info['format'].get('duration', 0))
                        for line in process.stdout:
                            if 'out_time_ms' in line:
                                try:
                                    time = int(line.split('=')[1]) / 1000000
                                    if duration > 0:
                                        progress = min(int((time / duration) * 100), 100)
                                        pbar.update(progress - pbar.n)
                                except ValueError:
                                    pbar.update(1)
                        
                        process.wait()
                        if process.returncode != 0:
                            raise subprocess.CalledProcessError(process.returncode, cmd)
                        
                        pbar.update(100 - pbar.n)
                    else:
                        shutil.copy2(ruta_archivo, os.path.join(self.carpeta_destino, nombre_archivo))
                        pbar.update(100)

                return nombre_archivo

        except subprocess.CalledProcessError as e:
            print(f"Error al procesar el video {nombre_archivo}: {str(e)}")
        except Exception as e:
            print(f"Error inesperado al procesar el video {nombre_archivo}: {str(e)}")

    def actualizar_excel(self):
        try:
            # Leer el Excel existente
            df = pd.read_excel(self.excel_path)
            
            # Obtener información actualizada de los archivos procesados
            archivos_procesados = get_files_info_from_directory(self.carpeta_destino)
            
            # Crear un diccionario para mapear nombres de archivo a sus nuevos datos
            nuevos_datos = {row['NOMBRE_ARCHIVO']: row for _, row in archivos_procesados.iterrows()}
            
            # Columnas para los datos recodificados
            columnas_recodificadas = ['ANCHO_RECODIFICADO', 'ALTO_RECODIFICADO', 'RESOLUCION_X_RECODIFICADO', 
                                      'RESOLUCION_Y_RECODIFICADO', 'ORIENTACION_RECODIFICADO', 'FORMATO_RECODIFICADO', 
                                      'TAMAÑO_MB_RECODIFICADO', 'DURACION_SEG_RECODIFICADO', 'FPS_RECODIFICADO', 
                                      'TASA_BITS_RECODIFICADO', 'CÓDEC_VIDEO_RECODIFICADO']
            
            # Añadir columnas para los datos recodificados
            for columna in columnas_recodificadas:
                if columna not in df.columns:
                    df[columna] = None
            
            # Actualizar el DataFrame con los nuevos datos
            for index, row in df.iterrows():
                nombre_archivo = row['NOMBRE_ARCHIVO']
                nombre_procesado = nombre_archivo.replace('.', '_procesado.')
                
                if nombre_procesado in nuevos_datos:
                    df.at[index, 'PROCESADO'] = 'Sí'
                    for columna in columnas_recodificadas:
                        columna_original = columna.replace('_RECODIFICADO', '')
                        if columna_original in nuevos_datos[nombre_procesado]:
                            df.at[index, columna] = nuevos_datos[nombre_procesado][columna_original]
                else:
                    df.at[index, 'PROCESADO'] = 'No'
            
            # Guardar primero con pandas
            df.to_excel(self.excel_path, index=False)
            
            # Abrir el archivo con openpyxl para añadir el formato de tabla
            wb = load_workbook(self.excel_path)
            ws = wb.active
            
            # Obtener el rango de la tabla
            tabla_ref = f"A1:{chr(64 + len(df.columns))}{len(df.index) + 1}"
            
            # Crear la tabla con estilo
            tabla = Table(displayName="TablaObras", ref=tabla_ref)
            estilo = TableStyleInfo(
                name="TableStyleMedium2", 
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False
            )
            tabla.tableStyleInfo = estilo
            
            # Añadir la tabla a la hoja
            ws.add_table(tabla)
            
            # Ajustar el ancho de las columnas
            for column in ws.columns:
                max_length = 0
                column = list(column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column[0].column_letter].width = adjusted_width
            
            # Guardar los cambios
            wb.save(self.excel_path)
            print(f"Excel actualizado con formato de tabla: {self.excel_path}")
        
        except Exception as e:
            print(f"Error al actualizar el Excel: {str(e)}")

def main():
    expo_id = 'E992'
    recodificador = Recodificador(expo_id)
    carpeta_procesados = os.path.join(os.getcwd(), 'expos', expo_id, 'procesados')
    
    # Verificar si ya existen archivos procesados
    if os.path.exists(carpeta_procesados) and os.listdir(carpeta_procesados):
        while True:
            print("Se encontraron archivos procesados. ¿Quieres volver a procesar los archivos? (s/n): ", end='', flush=True)
            try:
                # Leemos la línea completa y eliminamos espacios y saltos de línea
                respuesta = input().strip()
                
                if respuesta == 's':
                    break
                elif respuesta == 'n':
                    print("Actualizando solo el Excel con los archivos existentes...")
                    recodificador.actualizar_excel()
                    return
                print("Por favor, introduce 's' o 'n'")
            except EOFError:
                continue


    # Si no hay archivos procesados o el usuario quiere reprocesar, continuar con el flujo normal
    processor = ExpoProcessor(expo_id)
    processor.setup_directories()
    processor.unzip_files()
    processor.process_and_move_files()
    processor.generate_summary()

    # Proceso de recodificación
    recodificador.crear_carpeta_procesados()
    recodificador.procesar_archivos()
    recodificador.actualizar_excel()

if __name__ == "__main__":
    main()

