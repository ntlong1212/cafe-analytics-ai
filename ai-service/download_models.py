import numpy as np
from deepface import DeepFace

print("==================================================")
print("Downloading DeepFace models...")
print("This may take a few minutes depending on your network.")
print("Please wait until it finishes.")
print("==================================================\n")

dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)

try:
    print("Downloading Age & Gender models...")
    DeepFace.analyze(dummy_img, actions=['age', 'gender'], enforce_detection=False)
    print("--> Age & Gender models downloaded successfully.\n")
    
    print("Downloading VGG-Face model...")
    DeepFace.represent(dummy_img, model_name="VGG-Face", enforce_detection=False)
    print("--> VGG-Face model downloaded successfully.\n")
    
    print("==================================================")
    print("ALL MODELS DOWNLOADED SUCCESSFULLY!")
    print("You can now run main.py as normal.")
    print("==================================================")
except Exception as e:
    print(f"\n[ERROR] An error occurred: {e}")
