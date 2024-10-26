from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from PIL import Image
import io
import base64
import glob
from main import ExpoProcessor, ImageInfo, VideoInfo  # Añadir importación de ImageInfo y VideoInfo

app = Flask(__name__)

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
    if hasattr(obj, 'numerator') and hasattr(obj, 'denominator'):  # Para IFDRational
        return float(obj.numerator) / float(obj.denominator)
    return str(obj)

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
        
        if not os.path.exists(output_path):
            # Si no existe pero hay un zip, procesarlo
            processor = ExpoProcessor(expo_id)
            
            # Verificar si existe algún archivo zip
            zip_files = glob.glob(os.path.join(processor.full_output_path, "*.zip"))
            
            if zip_files:
                processor.setup_directories()
                processor.unzip_files()
                processor.process_and_move_files()
                return jsonify({'status': 'success', 'message': 'Expo processed successfully'})
            else:
                return jsonify({'status': 'error', 'message': 'No zip file found'}), 404
        
        return jsonify({'status': 'success', 'message': 'Output folder already exists'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
