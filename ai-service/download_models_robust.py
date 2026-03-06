import os
import requests

def download_file(url, dest_path):
    print(f"Downloading {url.split('/')[-1]}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        last_percent = -1
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192 * 16):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        if percent % 10 == 0 and percent != last_percent:
                            print(f"Progress: {percent}%")
                            last_percent = percent
                            
        print(f"Successfully downloaded: {dest_path}\n")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
            
if __name__ == '__main__':
    weights_dir = os.path.expanduser('~/.deepface/weights')
    os.makedirs(weights_dir, exist_ok=True)
    
    models = {
        "gender_model_weights.h5": "https://github.com/serengil/deepface_models/releases/download/v1.0/gender_model_weights.h5",
        "vgg_face_weights.h5": "https://github.com/serengil/deepface_models/releases/download/v1.0/vgg_face_weights.h5"
    }
    
    for filename, url in models.items():
        dest_path = os.path.join(weights_dir, filename)
        if not os.path.exists(dest_path):
            download_file(url, dest_path)
        else:
            print(f"Skipping {filename}, already exists.\n")
            
    print("ALL MODELS DOWNLOAD COMPLETE!")
