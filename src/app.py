# Imports
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
import os
from PIL import Image
import io
import base64
import glob
import shutil
from main import ExpoProcessor, ImageInfo, VideoInfo, Recodificador

# Inicialización de Flask
print("Iniciando configuración de Flask...")
app = Flask(__name__, template_folder='templates')
CORS(app)

print("Rutas registradas:")
print(app.url_map)

# Funciones auxiliares
def get_thumbnail(image_path, size=(200, 200)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format=img.format)
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            return f"data:image/{img.format.lower()};base64,{img_str}"
    except Exception as e:
        print(f"Error creando miniatura para {image_path}: {e}")
        return None

def convert_to_serializable(obj):
    """Convierte objetos no serializables a tipos básicos de Python."""
    if hasattr(obj, 'numerator') and hasattr(obj, 'denominator'):
        return float(obj.numerator) / float(obj.denominator)
    return str(obj)

# Rutas de la aplicación
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_images', methods=['POST'])
def load_images():
    try:
        expo_id = request.form.get('expo_id')
        if not expo_id:
            return jsonify({
                'error': 'No se proporcionó ID de exposición'
            }), 400

        expo_path = os.path.join(os.getcwd(), 'expos', expo_id)
        output_path = os.path.join(expo_path, 'ficheros_salida')
        
        if not os.path.exists(expo_path):
            return jsonify({
                'error': f'No existe la carpeta para la exposición {expo_id}'
            }), 404
        
        if os.path.exists(output_path):
            images = []
            for filename in os.listdir(output_path):
                try:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4')):
                        file_path = os.path.join(output_path, filename)
                        
                        # Obtener información del archivo según su tipo
                        if filename.lower().endswith('.mp4'):
                            file_info = VideoInfo.get_video_info(file_path)
                            image_data = {
                                'filename': filename,
                                'is_video': True,
                                'info': {k: convert_to_serializable(v) for k, v in file_info.items()}
                            }
                        else:
                            try:
                                with Image.open(file_path) as img:
                                    # Crear miniatura
                                    img.thumbnail((200, 200))
                                    # Convertir a base64
                                    buffered = io.BytesIO()
                                    img.save(buffered, format=img.format)
                                    img_str = base64.b64encode(buffered.getvalue()).decode()
                                    thumbnail = f"data:image/{img.format.lower()};base64,{img_str}"
                                    
                                    file_info = ImageInfo.get_image_info(file_path)
                                    # Convertir valores no serializables
                                    serializable_info = {k: convert_to_serializable(v) for k, v in file_info.items()}
                                    
                                    image_data = {
                                        'filename': filename,
                                        'thumbnail': thumbnail,
                                        'is_video': False,
                                        'info': serializable_info
                                    }
                            except Exception as e:
                                print(f"Error processing image {filename}: {str(e)}")
                                continue
                        
                        images.append(image_data)
                except Exception as e:
                    print(f"Error processing file {filename}: {str(e)}")
                    continue
            
            return jsonify({
                'status': 'show_images',
                'images': images
            })
        
        # Buscar archivos ZIP si no existe ficheros_salida
        zip_files = [f for f in os.listdir(expo_path) if f.lower().endswith('.zip')]
        if zip_files:
            return jsonify({
                'status': 'ask_unzip',
                'zip_files': zip_files
            })
        
        return jsonify({
            'error': 'La carpeta no contiene archivos ZIP para descomprimir'
        }), 404

    except Exception as e:
        print(f"Error in load_images: {str(e)}")
        return jsonify({
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@app.route('/expos/<expo_id>/ficheros_salida/<filename>')
def serve_file(expo_id, filename):
    directory = os.path.join(os.getcwd(), 'expos', expo_id, 'ficheros_salida')
    return send_from_directory(directory, filename)

@app.route('/process_expo', methods=['POST'])
def process_expo_endpoint():
    try:
        data = request.json
        expo_id = data.get('expo_id')
        
        if not expo_id:
            return jsonify({'status': 'error', 'message': 'No expo_id provided'}), 400
        
        # Verificar si existe la carpeta ficheros_salida
        output_path = os.path.join(os.getcwd(), 'expos', expo_id, 'ficheros_salida')
        originales_path = os.path.join(os.getcwd(), 'expos', expo_id, 'originales')
        
        if not os.path.exists(output_path):
            # Si no existe pero hay un zip, procesarlo
            processor = ExpoProcessor(expo_id)
            
            # Verificar si existe algún archivo zip
            zip_files = glob.glob(os.path.join(processor.full_output_path, "*.zip"))
            
            if zip_files:
                processor.setup_directories()
                processor.unzip_files()
                processor.process_and_move_files()
                
                # Copiar contenido a la carpeta 'originales'
                if not os.path.exists(originales_path):
                    os.makedirs(originales_path)
                
                # Copiar todos los archivos de ficheros_salida a originales
                for item in os.listdir(output_path):
                    s = os.path.join(output_path, item)
                    d = os.path.join(originales_path, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                    else:
                        shutil.copytree(s, d, dirs_exist_ok=True)
                
                # Borrar la carpeta 'varios' si existe
                varios_path = os.path.join(output_path, 'varios')
                if os.path.exists(varios_path):
                    shutil.rmtree(varios_path)
                
                return jsonify({'status': 'success', 'message': 'Expo processed successfully and backed up'})
            else:
                return jsonify({'status': 'error', 'message': 'No zip file found'}), 404
        
        return jsonify({'status': 'success', 'message': 'Output folder already exists'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_images/<expo_id>')
def get_images(expo_id):
    try:
        output_path = os.path.join(os.getcwd(), 'expos', expo_id, 'ficheros_salida')
        if not os.path.exists(output_path):
            return jsonify({'status': 'error', 'message': 'Output folder not found'}), 404
            
        files = []
        for file in os.listdir(output_path):
            if file.lower().endswith(('.mp4', '.jpg', '.jpeg', '.png')):
                files.append({
                    'filename': file,
                    'is_video': file.lower().endswith('.mp4')
                })
        
        return jsonify({
            'status': 'show_images',
            'images': files
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/recodificar', methods=['POST'])
def recodificar_endpoint():
    try:
        print("Recibida petición de recodificación")
        data = request.json
        print(f"Datos recibidos: {data}")
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No se recibieron datos'}), 400
            
        expo_id = data.get('expo_id')
        if not expo_id:
            return jsonify({'status': 'error', 'message': 'No expo_id provided'}), 400
        
        print(f"Procesando expo_id: {expo_id}")
        
        # Crear instancia del recodificador
        recodificador = Recodificador(expo_id)
        
        # Procesar archivos
        print("Creando carpeta procesados...")
        recodificador.crear_carpeta_procesados()
        
        print("Iniciando procesamiento de archivos...")
        recodificador.procesar_archivos()
        
        print("Procesamiento completado")
        
        # Verificar contenido de la carpeta procesados
        carpeta_procesados = os.path.join(os.getcwd(), 'expos', expo_id, 'procesados')
        if os.path.exists(carpeta_procesados):
            archivos_procesados = os.listdir(carpeta_procesados)
            print(f"Archivos en carpeta procesados: {archivos_procesados}")
        else:
            print("La carpeta procesados no existe!")
        
        return jsonify({
            'status': 'success', 
            'message': 'Archivos recodificados correctamente',
            'archivos_procesados': archivos_procesados if 'archivos_procesados' in locals() else []
        })
        
    except Exception as e:
        print(f"Error en recodificar_endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Iniciar la aplicación
if __name__ == '__main__':
    app.run(debug=True)