import os
import shutil
from PIL import Image
import cv2
import numpy as np
import pandas as pd
import json
import subprocess
import re

def crear_carpeta_procesados(expo_id):
    full_output_path = os.path.join(os.getcwd(), 'expos', expo_id)
    carpeta_procesados = os.path.join(full_output_path, 'procesados')
    if not os.path.exists(carpeta_procesados):
        os.makedirs(carpeta_procesados)
        print(f"Carpeta '{carpeta_procesados}' creada.")
    else:
        print(f"La carpeta '{carpeta_procesados}' ya existe.")
    return carpeta_procesados

def procesar_archivos(expo_id):
    full_output_path = os.path.join(os.getcwd(), 'expos', expo_id)
    carpeta_origen = os.path.join(full_output_path, 'ficheros_salida')
    carpeta_destino = os.path.join(full_output_path, 'procesados')

    total_archivos = len(os.listdir(carpeta_origen))
    archivos_procesados = 0

    for archivo in os.listdir(carpeta_origen):
        ruta_archivo = os.path.join(carpeta_origen, archivo)
        
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
            procesar_imagen(ruta_archivo, carpeta_destino)
        elif archivo.lower().endswith('.mp4'):
            procesar_video(ruta_archivo, carpeta_destino)
        
        archivos_procesados += 1
        print(f"Progreso: {archivos_procesados}/{total_archivos} archivos procesados")

def procesar_imagen(ruta_archivo, carpeta_destino):
    try:
        with Image.open(ruta_archivo) as img:
            ancho, alto = img.size
            formato = img.format
            modo = img.mode

            necesita_procesamiento = False

            # Comprobar formato
            if formato not in ['PNG', 'JPEG']:
                necesita_procesamiento = True

            # Comprobar profundidad de color
            if modo != 'RGB':
                necesita_procesamiento = True

            if necesita_procesamiento:
                # Convertir a RGB si es necesario
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Guardar en formato JPEG
                nuevo_nombre = os.path.splitext(os.path.basename(ruta_archivo))[0] + '_procesado.jpg'
                ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                img.save(ruta_destino, 'JPEG', quality=95)
                print(f"Imagen procesada: {nuevo_nombre}")
            else:
                # Copiar la imagen sin procesar
                nuevo_nombre = os.path.basename(ruta_archivo)
                ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                shutil.copy2(ruta_archivo, ruta_destino)
                print(f"Imagen copiada sin procesar: {nuevo_nombre}")

    except Exception as e:
        print(f"Error al procesar la imagen {os.path.basename(ruta_archivo)}: {str(e)}")

def procesar_video(ruta_archivo, carpeta_destino):
    try:
        # Obtener información del video
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
            
            # Comprobar resolución
            if (width, height) not in [(2160, 3840), (3840, 2160)]:
                necesita_procesamiento = True
            
            # Comprobar FPS
            if fps > 30:
                necesita_procesamiento = True
            
            # Comprobar codec
            if codec not in ['hevc', 'h264']:
                necesita_procesamiento = True
            
            # Comprobar bitrate
            bitrate = int(info['format']['bit_rate'])
            if bitrate < 30_000_000 or bitrate > 60_000_000:
                necesita_procesamiento = True
            
            if necesita_procesamiento:
                nuevo_nombre = os.path.splitext(os.path.basename(ruta_archivo))[0] + '_procesado.mp4'
                ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                
                # Ajustar resolución si es necesario
                if (width, height) not in [(2160, 3840), (3840, 2160)]:
                    if width > height:
                        new_size = '3840:2160'
                    else:
                        new_size = '2160:3840'
                else:
                    new_size = f'{width}:{height}'
                
                # Comando FFmpeg corregido
                cmd = [
                    'ffmpeg', '-i', ruta_archivo,
                    '-c:v', 'libx265',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-vf', f'fps=30,scale={new_size}',  # Corregido aquí
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
                # Copiar el video sin procesar
                nuevo_nombre = os.path.basename(ruta_archivo)
                ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                shutil.copy2(ruta_archivo, ruta_destino)
                print(f"Video copiado sin procesar: {nuevo_nombre}")
    
    except subprocess.CalledProcessError as e:
        print(f"Error al procesar el video {os.path.basename(ruta_archivo)}: {str(e)}")
        print(f"Comando que causó el error: {' '.join(cmd)}")  # Añadido para depuración
    except Exception as e:
        print(f"Error inesperado al procesar el video {os.path.basename(ruta_archivo)}: {str(e)}")

def get_file_info(file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Tamaño en MB
    
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return get_image_info(file_path, file_name, file_size)
    elif file_path.lower().endswith('.mp4'):
        return get_video_info(file_path, file_name, file_size)
    else:
        return None

def get_image_info(file_path, file_name, file_size):
    with Image.open(file_path) as img:
        width, height = img.size
        format = img.format
        
        orientation = 'V' if height > width else 'H'
        
        return {
            'NOMBRE_ARCHIVO': file_name,
            'TIPO': 'Imagen',
            'ANCHO': width,
            'ALTO': height,
            'ORIENTACION': orientation,
            'FORMATO': format,
            'TAMAÑO_MB': round(file_size, 2),
            'RESOLUCION_X': 72,
            'RESOLUCION_Y': 72,
        }

def get_video_info(file_path, file_name, file_size):
    try:
        result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        probe = json.loads(result.stdout)
        
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            orientation = 'V' if height > width else 'H'
            frame_rate = eval(video_stream['r_frame_rate'])
            duration = float(probe['format']['duration'])
            bit_rate = int(probe['format']['bit_rate'])
            video_codec = video_stream['codec_name']

            return {
                'NOMBRE_ARCHIVO': file_name,
                'TIPO': 'Video',
                'ANCHO': width,
                'ALTO': height,
                'ORIENTACION': orientation,
                'DURACION_SEG': int(duration),
                'FPS': frame_rate,
                'FORMATO': 'MP4',
                'TAMAÑO_MB': round(file_size, 2),
                'TASA_BITS': bit_rate,
                'CÓDEC_VIDEO': video_codec,
            }
    except Exception as e:
        print(f"Error procesando el video {file_path}: {e}")
        return None

def create_excel_from_processed(expo_id):
    full_output_path = os.path.join(os.getcwd(), 'expos', expo_id)
    processed_folder = os.path.join(full_output_path, 'procesados')
    files_info = []
    
    for file_name in os.listdir(processed_folder):
        file_path = os.path.join(processed_folder, file_name)
        
        if os.path.isfile(file_path):
            info = get_file_info(file_path)
            if info:
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
        return
    
    # Ordenar el DataFrame por número de pantalla si la columna existe
    if 'NUMERO_PANTALLA' in df.columns:
        df = df.sort_values('NUMERO_PANTALLA')
    
    # Guardar el DataFrame en un Excel
    excel_path = os.path.join(full_output_path, 'Resumen obras procesadas.xlsx')
    df.to_excel(excel_path, index=False)
    print(f"Excel creado: {excel_path}")

if __name__ == "__main__":
    expo_id = 'E990'  # Puedes cambiar esto según sea necesario
    carpeta_procesados = crear_carpeta_procesados(expo_id)
    procesar_archivos(expo_id)
    create_excel_from_processed(expo_id)
