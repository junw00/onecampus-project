from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import os
import json
import urllib.request
import urllib.parse

# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# 모든 출처에 대해 CORS 허용
CORS(app, resources={r"/*": {"origins": "*"}})

# Socket.IO 초기화
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])

# ComfyUI 설정
COMFYUI_SERVER_ADDRESS = "http://127.0.0.1:8188"
server_address = "127.0.0.1:8188"
COMFYUI_CLIENT_ID = "123"
# OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 감시할 폴더 목록 설정 (여러 폴더 추가 가능)
INPUT_FOLDER = "/Users/junwoo/Desktop/university/project/onecampus/ComfyUI/input"
OUTPUT_FOLDER = "/Users/junwoo/Desktop/university/project/onecampus/ComfyUI/output"

# 저장 경로 설정
DESTINATION_INPUT_FOLDER = "/Users/junwoo/Desktop/university/project/onecam-front/public/img/input/"
DESTINATION_OUTPUT_FOLDER = "/Users/junwoo/Desktop/university/project/onecam-front/public/img/output/"

# WebSocket 연결 이벤트 처리
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Watchdog 핸들러 클래스 정의 (폴더 내 새로운 이미지 감지)
# Watchdog 이벤트 핸들러 클래스 정의 (폴더 내 새로운 이미지 감지)
class ImageFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        # 디렉토리가 아닌 파일만 처리
        if not event.is_directory:
            file_path = event.src_path

            # 이미지 파일인지 확인
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                print(f"New image detected: {file_path}")
                
                # 감지된 폴더가 input인지 output인지 확인
                if INPUT_FOLDER in file_path:
                    destination_folder = DESTINATION_INPUT_FOLDER
                    relative_path_prefix = "/img/input/"
                elif OUTPUT_FOLDER in file_path:
                    destination_folder = DESTINATION_OUTPUT_FOLDER
                    relative_path_prefix = "/img/output/"
                else:
                    print("File detected in an unknown folder.")
                    return

                # 출력 폴더 생성 (없으면 생성)
                if not os.path.exists(destination_folder):
                    os.makedirs(destination_folder)
                    print(f"Created destination folder: {destination_folder}")
                
                # 파일 이름 추출 및 복사 경로 설정
                file_name = os.path.basename(file_path)
                destination_path = os.path.join(destination_folder, file_name)

                try:
                    # 파일 복사
                    shutil.copy(file_path, destination_path)
                    print(f"Copied {file_path} to {destination_path}")

                    # WebSocket을 통해 클라이언트로 복사된 이미지 경로 전송
                    relative_path = f"{relative_path_prefix}{file_name}"  # 클라이언트가 접근 가능한 상대 경로
                    socketio.emit('new_image', {'image_path': relative_path})
                    print(f"Emitted new image path: {relative_path}")
                
                except Exception as e:
                    print(f"Error copying file: {e}")



# Observer 설정 및 시작 함수 정의
def start_folder_monitoring():
    event_handler = ImageFileHandler()
    observer = Observer()
    observer.schedule(event_handler, INPUT_FOLDER, recursive=False)  # input 폴더 감시
    observer.schedule(event_handler, OUTPUT_FOLDER, recursive=False)  # output 폴더 감시
    observer.start()
    print(f"Started monitoring folders: {INPUT_FOLDER} and {OUTPUT_FOLDER}")

    try:
        while True:
            pass  # 계속 실행 (Ctrl+C로 종료 가능)
    except KeyboardInterrupt:
        observer.stop()
        print("Stopped monitoring.")

    observer.join()

# ComfyUI와 통신하는 함수 정의
def queue_prompt(prompt, server_address):
    p = {
        "prompt": prompt,
        "client_id": COMFYUI_CLIENT_ID,
        "extra_data": {
            "extra_pnginfo": {
                "workflow": prompt
            }
        }
    }
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read())

def get_history(prompt_id, server_address):
    data = {'prompt_id': prompt_id}
    url_values = urllib.parse.urlencode(data)
    try:
        with urllib.request.urlopen(f'http://{server_address}/history?{url_values}') as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        return None

def save_images_from_history(history):
    if isinstance(history, dict):
        for key, value in history.items():
            if isinstance(value, dict) and 'outputs' in value:
                for node_id, node_output in value['outputs'].items():
                    if 'images' in node_output:
                        for image in node_output['images']:
                            image_path = os.path.join(OUTPUT_FOLDER, image['filename'])
                            print(f"Image saved by ComfyUI: {image_path}")
                        return True
    return False

# POST 요청 처리 엔드포인트 정의 (ComfyUI와 통신)
@app.route('/send', methods=['POST'])
def handle_send():
    try:
        data = request.json  # JSON 데이터 파싱
        user_prompt = data.get('prompt')
        image_path = data.get('image_path')
        image = image_path[image_path.rfind('/') + 1: ]

        print("Dsd: " + image)
        if not user_prompt:
            return jsonify({"error": "Prompt is required"}), 400

        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            print(f"Created directory: {OUTPUT_FOLDER}")

        # 워크플로우 JSON 설정 (간단히 유지)
        workflow = {
          "3": {
            "inputs": {
              "seed": 331335407035282,
              "steps": 20,
              "cfg": 8,
              "sampler_name": "euler",
              "scheduler": "normal",
              "denoise": 1,
              "model": [
                "4",
                0
              ],
              "positive": [
                "6",
                0
              ],
              "negative": [
                "7",
                0
              ],
              "latent_image": [
                "14",
                0
              ]
            },
            "class_type": "KSampler",
            "_meta": {
              "title": "KSampler"
            }
          },
          "4": {
            "inputs": {
              "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
              "title": "Load Checkpoint"
            }
          },
          "5": {
            "inputs": {
              "width": 512,
              "height": 512,
              "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
              "title": "Empty Latent Image"
            }
          },
          "6": {
            "inputs": {
              "text": user_prompt,
              "clip": [
                "4",
                1
              ]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
              "title": "CLIP Text Encode (Prompt)"
            }
          },
          "7": {
            "inputs": {
              "text": "text, watermark",
              "clip": [
                "4",
                1
              ]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
              "title": "CLIP Text Encode (Prompt)"
            }
          },
          "8": {
            "inputs": {
              "samples": [
                "3",
                0
              ],
              "vae": [
                "4",
                2
              ]
            },
            "class_type": "VAEDecode",
            "_meta": {
              "title": "VAE Decode"
            }
          },
          "9": {
            "inputs": {
              "filename_prefix": "ComfyUI",
              "images": [
                "8",
                0
              ]
            },
            "class_type": "SaveImage",
            "_meta": {
              "title": "Save Image"
            }
          },
          "13": {
            "inputs": {
              "image": image,
              "upload": "image"
            },
            "class_type": "LoadImage",
            "_meta": {
              "title": "Load Image"
            }
          },
          "14": {
            "inputs": {
              "pixels": [
                "13",
                0
              ],
              "vae": [
                "4",
                2
              ]
            },
            "class_type": "VAEEncode",
            "_meta": {
              "title": "VAE Encode"
            }
          }
        }

        # ComfyUI에 워크플로우 전송 및 처리 시작
        prompt_id_response = queue_prompt(workflow, server_address)
        prompt_id = prompt_id_response.get('prompt_id')

        # 작업 완료 후 히스토리 가져오기
        history = get_history(prompt_id, server_address)

        if history is None or not save_images_from_history(history):
            return jsonify({"message": "No images found in the output"}), 500

        return jsonify({"message": f"Process completed successfully. Images saved at {OUTPUT_FOLDER}"})
    
    except Exception as e:
        print(f"Error during processing: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # 폴더 모니터링을 별도의 스레드에서 실행 (메인 스레드와 분리)
    monitor_thread = threading.Thread(target=start_folder_monitoring)
    monitor_thread.daemon = True  # 메인 스레드 종료 시 함께 종료되도록 설정
    monitor_thread.start()

    # Flask-SocketIO 서버 실행
    socketio.run(app, debug=True)