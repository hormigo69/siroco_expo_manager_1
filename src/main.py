import os
import sys
import gdown
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
import qrcode
import PIL

print(f"Versión de Python: {sys.version}")
print(f"Versión de Pillow: {PIL.__version__}")

class FileManager:
    @staticmethod
    def ensure_directory(path):
        '''
        Crea un directorio si no existe
        '''
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def download_files(url, output_folder):
        '''
        Descarga los archivos de la carpeta de google drive
        '''
        full_output_path = os.path.join(os.getcwd(), 'expos', output_folder)
        FileManager.ensure_directory(full_output_path)
        gdown.download_folder(url, output=full_output_path)

class ImageInfo:
    @staticmethod
    def get_image_info(file_path):
        '''
        Obtiene la información de la imagen
        '''
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

class ExcelProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def process_excel(self):
        '''
        Procesa el archivo excel, obtiene la información de las imágenes y guarda el resumen en un archivo excel
        '''
        excel_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Formulario obras.xlsx')
        print(f"Procesando archivo Excel: {excel_path}")

        if not os.path.exists(excel_path):
            print(f"El archivo Excel no se encuentra en la ruta: {excel_path}")
            return

        df = pd.read_excel(excel_path, skiprows=1)
        
        columns = ['PANTALLA', 'ID', 'ARTISTA', 'TÍTULO', 'NOMBRE FICHERO', 'TÉCNICA', 'PRECIO', 'LINK']
        df.columns = columns
        
        df['PANTALLA'] = df['PANTALLA'].ffill().infer_objects()
        df = df[df['ARTISTA'] != 'NOMBRE ARTISTA'].dropna(subset=['ARTISTA'])
        df['PANTALLA'] = df['PANTALLA'].str.replace(r'PANTALLA (\d+).*', lambda x: 'P' + x.group(1).zfill(3), regex=True)
        df['FICHERO'] = df['NOMBRE FICHERO']
        df = df.drop(columns=['ID'])
        
        for column in ['RESOLUCION_X', 'RESOLUCION_Y', 'ORIENTACION', 'ANCHO', 'ALTO']:
            df[column] = ''

        for i, row in df.iterrows():
            file_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Obras', row['NOMBRE FICHERO'])
            if os.path.exists(file_path):
                info = ImageInfo.get_image_info(file_path)
                if info:
                    for key, value in info.items():
                        df.at[i, key] = value
            else:
                print(f"No se encontró el archivo: {file_path}")

        numeric_columns = ['ANCHO', 'ALTO', 'RESOLUCION_X', 'RESOLUCION_Y']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        output_excel_path = os.path.join(os.getcwd(), 'expos', self.output_folder, 'Resumen obras.xlsx')
        df.to_excel(output_excel_path, index=False)

        print("Procesamiento de Excel completado.")
        print(df)

class ImageProcessor:
    def __init__(self, expo_dir, font_path, status_callback, expo_id):
        self.expo_dir = expo_dir
        self.font_path = font_path
        self.font_size = 35
        self.status_callback = status_callback
        self.output_dir = os.path.join(self.expo_dir, 'ficheros_salida')
        self.expo_id = expo_id
        FileManager.ensure_directory(self.output_dir)
        print(f"Carpeta de salida creada: {self.output_dir}")
    
    def rename_file(self, pantalla, nombre_fichero):
        '''
        Renombra el archivo con el formato de la exposición
        '''
        # Extraer el número de la pantalla (asumiendo que está en formato 'P012')
        pantalla_num = pantalla[1:] if pantalla.startswith('P') else pantalla
        
        # Dividir el nombre del archivo original
        file_name, file_extension = os.path.splitext(nombre_fichero)
        
        # Crear el nuevo nombre de archivo
        new_file_name = f"{self.expo_id}_P{pantalla_num}_{file_name}{file_extension}"
        
        return new_file_name



    def customize_image(self, nombre_fichero, nombre_artista, nombre_obra, orientacion, url):
        '''
        Personaliza la imagen con el nombre del artista, el título de la obra, la orientación y el enlace
        '''
        #print(f"Intentando cargar fuente desde: {self.font_path}")

        background_size = (2160, 3840) if orientacion == 'V' else (3840, 2160)
        background = Image.new('RGB', background_size, color='black')

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype(self.font_path, self.font_size)

        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_size = min(100, background.width // 20)
        qr_img = qr_img.resize((qr_size, qr_size))
        qr_position = (background.width - qr_size - 20, background.height - qr_size - 10)

        nombre_artista = nombre_artista.upper()
        text = f"{nombre_artista}   \"{nombre_obra}\"" if nombre_obra else nombre_artista
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top

        text_x = max(20, qr_position[0] - text_width - 20)
        text_y = qr_position[1] + (qr_size - text_height) // 2

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
        '''
        Procesa la imagen, la personaliza y la guarda
        '''
        nombre_fichero = row['FICHERO']
        nombre_artista = row['ARTISTA']
        nombre_obra = row['TÍTULO']
        orientacion = row['ORIENTACION']
        url = row['LINK']
        pantalla = row['PANTALLA']


        img_path = os.path.join(self.expo_dir, 'Obras', nombre_fichero)
        print(f"Intentando abrir imagen: {img_path}")
        
        try:
            img = Image.open(img_path)
            print(f"Imagen abierta correctamente: {img_path}")

            background = self.customize_image(nombre_fichero, nombre_artista, nombre_obra, orientacion, url)
            img_final = self.resize_and_center_image(img, background, orientacion)

            # Renombrar el archivo antes de guardarlo
            new_file_name = self.rename_file(pantalla, nombre_fichero)
            output_path = os.path.join(self.output_dir, new_file_name)
            
            img_final.save(output_path)
            print(f"Imagen procesada guardada como: {output_path}")
        except Exception as e:
            print(f"Error al procesar la imagen {img_path}: {str(e)}")

    def process_all_images(self):
        '''
        Procesa todas las imágenes
        '''
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

def main():
    drive_url_img_folder = 'https://drive.google.com/drive/folders/10oBtG589CN11SVtVfGqo7YHQwhU4K7m8'
    output_folder = 'E997'
    
    full_output_path = os.path.join(os.getcwd(), 'expos', output_folder)

    if not os.path.exists(full_output_path):
        FileManager.download_files(drive_url_img_folder, output_folder)
    else:
        print(f"La carpeta {full_output_path} ya existe. No se descargarán los archivos nuevamente.")
    
    excel_processor = ExcelProcessor(output_folder)
    excel_processor.process_excel()

    def status_callback(message):
        print(message)

    obras_folder = os.path.join(full_output_path, 'Obras')
    if not os.path.exists(obras_folder):
        print(f"Error: La carpeta 'Obras' no existe en {full_output_path}")
        print("Asegúrate de que las imágenes estén en una carpeta llamada 'Obras'")
    else:
        print(f"Carpeta 'Obras' encontrada en: {obras_folder}")
        print("Contenido de la carpeta 'Obras':")
        for file in os.listdir(obras_folder):
            print(f"  - {file}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "..", "static", "fonts", "helvetica.ttf")

    if not os.path.exists(font_path):
        print(f"Error: El archivo de fuente no existe en la ruta: {font_path}")
        sys.exit(1)

    expo_id = 'E997'  # Asegúrate de que este sea el ID correcto para la exposición
    image_processor = ImageProcessor(full_output_path, font_path, status_callback, expo_id)
    
    print(f"Iniciando procesamiento de imágenes en: {full_output_path}")
    image_processor.process_all_images()
    print("Procesamiento de imágenes finalizado")



if __name__ == "__main__":
    main()