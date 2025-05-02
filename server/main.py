from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
import time
import argparse
import torch
import torchvision.transforms as transforms
from torchvision import models
import os

app = Flask(__name__)

start_time = time.time()
processed = {"success": 0, "fail": 0}

API_VERSION = 1
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Load ImageNet labels once
LABELS_PATH = os.path.join(os.path.dirname(__file__), "imagenet_classes.txt")
with open(LABELS_PATH) as f:
    class_labels = [line.strip() for line in f.readlines()]

# Load pre-trained model once
from torchvision.models import resnet50, ResNet50_Weights
weights = ResNet50_Weights.DEFAULT
model = resnet50(weights=weights)
model.eval()


# Define transform pipeline
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 400, "message": "No image file provided"}}), 400

    file = request.files['image']

    if file.filename == '' or not allowed_file(file.filename):
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 400, "message": "Unsupported image format"}}), 400

    filename = secure_filename(file.filename)

    try:
        # Read and preprocess image
        image = Image.open(file.stream).convert("RGB")
        input_tensor = transform(image).unsqueeze(0)  # Add batch dimension

        # Inference
        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.nn.functional.softmax(output[0], dim=0)

        # Top 2 predictions
        topk = torch.topk(probs, 2)
        results = [
            {"name": class_labels[idx], "score": round(probs[idx].item(), 4)}
            for idx in topk.indices
        ]

        processed["success"] += 1
        return jsonify({"matches": results}), 200

    except UnidentifiedImageError:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 400, "message": "Malformed image file"}}), 400

    except Exception as e:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 500, "message": f"Internal server error: {str(e)}"}}), 500

@app.route('/status', methods=['GET'])
def status():
    uptime = time.time() - start_time
    health = "ok" if processed["fail"] == 0 else "error"

    status_response = {
        "status": {
            "uptime": round(uptime, 2),
            "processed": processed,
            "health": health,
            "api_version": API_VERSION
        }
    }

    return jsonify(status_response), 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app.run(host="0.0.0.0", port=args.port, debug=True)
