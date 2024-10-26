from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from PIL import Image
import io
import base64
import glob
from main import ExpoProcessor  # Importar la clase desde main.py

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_images', methods=['POST'])
def load_images():
    expo_id = request.form.get('expo_id')
    expo_path = os.path.join(os.getcwd(), 'expos', expo_id)
    output_path = os.path.join(expo_path, 'ficheros_salida')
    
    # Verificar si existe la carpeta de la exposición
    if not os.path.exists(expo_path):
        return jsonify({
            'error': f'No existe la carpeta para la exposición {expo_id}'
        })
    
    # Si existe ficheros_salida, mostrar miniaturas
    if os.path.exists(output_path):
        images = []
        for filename in os.listdir(output_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4')):
                file_path = os.path.join(output_path, filename)
                if filename.lower().endswith('.mp4'):
                    thumbnail = '/static/video-thumbnail.png'
                else:
                    thumbnail = get_thumbnail(file_path)
                
                images.append({
                    'filename': filename,
                    'thumbnail': thumbnail,
                    'is_video': filename.lower().endswith('.mp4')
                })
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
    
    # No hay ZIP ni ficheros_salida
    return jsonify({
        'error': 'La carpeta no contiene archivos ZIP para descomprimir'
    })

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