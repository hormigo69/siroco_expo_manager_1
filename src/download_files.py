import os
import gdown
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
import qrcode
import PIL
import sys
import io
print(f"Versión de Python: {sys.version}")
print(f"Versión de Pillow: {PIL.__version__}")


class DownloadFiles:
    def download_files(url, output_folder):

        # Crear la carpeta de salida si no existe dentro de la carpeta expos/ en el raiz
        output_folder = os.path.join(os.getcwd(), 'expos', output_folder)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        gdown.download_folder(url, output=output_folder)


class ExcelProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def get_image_info(self, file_path):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                dpi = img.info.get('dpi', (None, None))
                
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'XResolution':
                                dpi = (value, value)
                                break
                
                if dpi[0] is None and hasattr(img, 'physicalDimensions'):
                    physical_width, physical_height = img.physicalDimensions
                    if physical_width > 0 and physical_height > 0:
                        dpi_x = width / (physical_width / 25.4)
                        dpi_y = height / (physical_height / 25.4)
                        dpi = (dpi_x, dpi_y)
                
                orientation = 'H' if width > height else 'V'
                
                return {
                    'ANCHO': width,
                    'ALTO': height,
                    'RESOLUCION_X': dpi[0],
                    'RESOLUCION_Y': dpi[1],
                    'ORIENTACION': orientation
                }
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
            return None

    def process_excel(self):
        # Usar self.output_folder en lugar de pasar como parámetro
        excel_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Formulario obras.xlsx')
        print(f"Procesando archivo Excel: {excel_path}")

        # Verificar si el archivo existe
        if not os.path.exists(excel_path):
            print(f"El archivo Excel no se encuentra en la ruta: {excel_path}")
            return

        df = pd.read_excel(excel_path, skiprows=1)
        
        # Definir las columnas correctas basadas en leer_excel.py
        columns = ['PANTALLA', 'ID', 'ARTISTA', 'TÍTULO', 'NOMBRE FICHERO', 'TÉCNICA', 'PRECIO', 'LINK']
        
        # Asignar los nombres de columnas
        df.columns = columns
        
        df['PANTALLA'] = df['PANTALLA'].ffill().infer_objects()
        df = df[df['ARTISTA'] != 'NOMBRE ARTISTA'].dropna(subset=['ARTISTA'])
        df['PANTALLA'] = df['PANTALLA'].str.replace(r'PANTALLA (\d+).*', lambda x: 'P' + x.group(1).zfill(3), regex=True)
        df['FICHERO'] = df['NOMBRE FICHERO']  # Cambiamos esta línea
        df = df.drop(columns=['ID'])
        
        # Modificar esta parte para incluir RESOLUCION_X y RESOLUCION_Y
        for column in ['RESOLUCION_X', 'RESOLUCION_Y', 'ORIENTACION', 'ANCHO', 'ALTO']:
            df[column] = ''

        # Aquí deberías implementar la función get_image_info si es necesaria
        for i, row in df.iterrows():
            # Cambiar la ruta para buscar en la carpeta 'obras'
            file_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Obras', row['NOMBRE FICHERO'])
            if os.path.exists(file_path):
                info = self.get_image_info(file_path)
                if info:
                    for key, value in info.items():
                        df.at[i, key] = value
            else:
                print(f"No se encontró el archivo: {file_path}")

        numeric_columns = ['ANCHO', 'ALTO', 'RESOLUCION_X', 'RESOLUCION_Y']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Ajustar la ruta de salida para el nuevo archivo Excel
        output_excel_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Resumen obras.xlsx')
        df.to_excel(output_excel_path, index=False)

        print("Procesamiento de Excel completado.")
        print(df)


class ImageProcessor:
    def __init__(self, expo_dir, font_path, status_callback):
        self.expo_dir = expo_dir
        self.font_path = font_path
        self.font_size = 35
        self.status_callback = status_callback
        self.output_dir = os.path.join(self.expo_dir, 'ficheros_salida')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        print(f"Carpeta de salida creada: {self.output_dir}")


    def customize_image(self, nombre_fichero, nombre_artista, nombre_obra, orientacion, url):
        print(f"Intentando cargar fuente desde: {self.font_path}")

        if orientacion == 'V':
            background = Image.new('RGB', (2160, 3840), color='black')
        else:
            background = Image.new('RGB', (3840, 2160), color='black')

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype(self.font_path, self.font_size)

        # Generar el código QR
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_size = min(100, background.width // 20)
        qr_img = qr_img.resize((qr_size, qr_size))
        qr_position = (background.width - qr_size - 20, background.height - qr_size - 10)

        # Preparar el texto
        nombre_artista = nombre_artista.upper()
        text = f"{nombre_artista}   \"{nombre_obra}\"" if nombre_obra else nombre_artista
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top

        text_x = max(20, qr_position[0] - text_width - 20)
        text_y = qr_position[1] + (qr_size - text_height) // 2

        # Dibujar el texto y añadir el QR
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        background.paste(qr_img, qr_position)

        return background

    def resize_and_center_image(self, img, background, orientacion):
        img_width, img_height = img.size
        bg_width, bg_height = background.size
        alto_faldon = 74
        
        available_height = bg_height - alto_faldon
        available_width = bg_width

        prop_disponible = 0.96
        width_scale = (available_width * prop_disponible) / img_width
        height_scale = (available_height * prop_disponible) / img_height
        
        scale = min(width_scale, height_scale)
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        x = (bg_width - new_width) // 2
        y = (available_height - new_height) // 2
        
        background.paste(img_resized, (x, y))
        
        return background


    def process_image(self, row):
        nombre_fichero = row['FICHERO']
        nombre_artista = row['ARTISTA']
        nombre_obra = row['TÍTULO']
        orientacion = row['ORIENTACION']
        url = row['LINK']

        img_path = os.path.join(self.expo_dir, 'Obras', nombre_fichero)
        print(f"Intentando abrir imagen: {img_path}")
        
        try:
            img = Image.open(img_path)
            print(f"Imagen abierta correctamente: {img_path}")

            background = self.customize_image(nombre_fichero, nombre_artista, nombre_obra, orientacion, url)
            img_final = self.resize_and_center_image(img, background, orientacion)

            output_path = os.path.join(self.output_dir, nombre_fichero)
            img_final.save(output_path)
            print(f"Imagen procesada guardada: {output_path}")
        except Exception as e:
            print(f"Error al procesar la imagen {img_path}: {str(e)}")

    def process_all_images(self):
        excel_path = os.path.join(self.expo_dir, 'Resumen obras.xlsx')
        if not os.path.exists(excel_path):
            print(f"Error: No se encuentra el archivo Excel en {excel_path}")
            return

        df = pd.read_excel(excel_path)
        total_images = len(df)
        self.status_callback(f"Iniciando procesamiento de {total_images} imágenes")
        
        for index, row in df.iterrows():
            try:
                self.process_image(row)
                self.status_callback(f"Procesada imagen {index + 1} de {total_images}")
            except Exception as e:
                print(f"Error procesando imagen {index + 1}: {str(e)}")
                print(f"Detalles de la fila: {row}")

        self.status_callback("Todas las imágenes han sido procesadas.")

def test_image_open():
    test_img_path = "/Users/ant/Library/CloudStorage/Dropbox/2 actions/Siroco/automatizaciones/expo_manager/expos/E997/Obras/1_miguelrosello_amadmaxcartoon.jpg"
    print(f"Intentando abrir imagen de prueba: {test_img_path}")
    print(f"El archivo existe: {os.path.exists(test_img_path)}")
    print(f"Permisos del archivo: {oct(os.stat(test_img_path).st_mode)[-3:]}")
    print(f"El archivo es legible: {os.access(test_img_path, os.R_OK)}")
    try:
        with Image.open(test_img_path) as img:
            print(f"Imagen abierta correctamente. Tamaño: {img.size}")
    except Exception as e:
        print(f"Error al abrir la imagen: {str(e)}")



if __name__ == "__main__":
    #E998: videos en carpetas
    drive_url_vid = 'https://drive.google.com/drive/folders/14LWksDjSwoZvEarlf4TK7sJDA_3qhKZe'

    #E999: imágenes en carpetas
    drive_url_img = 'https://drive.google.com/drive/folders/11iSMq6f9CnaWWSaBkepAWCKQp9JA0vML'

    #E997: imágenes en una carpeta
    drive_url_img_folder = 'https://drive.google.com/drive/folders/10oBtG589CN11SVtVfGqo7YHQwhU4K7m8'

    url = drive_url_img_folder
    output_folder = 'E997'
    
    test_image_open()

    # Obtén la ruta del directorio del script actual
    script_dir = os.path.dirname(os.path.abspath(__file__))




    # Construir la ruta completa
    full_output_path = os.path.join(os.getcwd(), 'expos', output_folder)

    # Verificar si la carpeta completa existe
    if not os.path.exists(full_output_path):
        DownloadFiles.download_files(url, output_folder)
    else:
        print(f"La carpeta {full_output_path} ya existe. No se descargarán los archivos nuevamente.")
    
    #procesar el excel
    excel_processor = ExcelProcessor(output_folder)
    excel_processor.process_excel()

    # Definir una función de callback para el estado
    def status_callback(message):
        print(message)

    # Verificar la existencia de la carpeta "Obras"
    obras_folder = os.path.join(full_output_path, 'Obras')
    if not os.path.exists(obras_folder):
        print(f"Error: La carpeta 'Obras' no existe en {full_output_path}")
        print("Asegúrate de que las imágenes estén en una carpeta llamada 'Obras'")
    else:
        print(f"Carpeta 'Obras' encontrada en: {obras_folder}")
        print("Contenido de la carpeta 'Obras':")
        for file in os.listdir(obras_folder):
            print(f"  - {file}")

    # Crear una instancia de ImageProcessor y procesar las imágenes
    font_path = os.path.join(script_dir, "..", "static", "fonts", "helvetica.ttf")

    if not os.path.exists(font_path):
        print(f"Error: El archivo de fuente no existe en la ruta: {font_path}")
        # Puedes agregar aquí una lógica para usar una fuente alternativa o terminar el script
        sys.exit(1)


    image_processor = ImageProcessor(full_output_path, font_path, status_callback)
    
    print(f"Iniciando procesamiento de imágenes en: {full_output_path}")
    image_processor.process_all_images()
    print("Procesamiento de imágenes finalizado")

