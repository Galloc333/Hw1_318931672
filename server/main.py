from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError
import time
import argparse
import torch
import torchvision.transforms as transforms
import os
import requests

app = Flask(__name__)

start_time = time.time()
processed = {"success": 0, "fail": 0}

API_VERSION = 1

# Load ImageNet labels once
LABELS_PATH = os.path.join(os.path.dirname(__file__), "assets\imagenet_classes.txt")
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

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 400, "message": "No image file provided"}}), 400

    file = request.files['image']

    try:
        # Read and preprocess image
        # Pillow supports a wide variety of image and file types (even pdf) and recognizes them based on their file headers
        image = Image.open(file.stream).convert("RGB")
        input_tensor = transform(image).unsqueeze(0)  # Add batch dimension

        # Inference
        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.nn.functional.softmax(output[0], dim=0)

        # Top 2 predictions
        top2 = torch.topk(probs, 2)
        results = [
            {"name": class_labels[idx], "score": round(probs[idx].item(), 4)}
            for idx in top2.indices
        ]

        processed["success"] += 1
        return jsonify({"matches": results}), 200

    except UnidentifiedImageError:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 400, "message": "Unsupported image format"}}), 400

    except Exception as e:
        processed["fail"] += 1
        return jsonify({"error": {"http_status": 500, "message": f"Internal server error: {str(e)}"}}), 500


@app.route('/status', methods=['GET'])
def status():
    health = "error"
    success = processed["success"]
    fail = processed["fail"]
    try:
        with open("assets/valid_image.jpg", "rb") as f:
            files = {"image": ("valid_image.jpg", f, "image/jpeg")}
            headers = {"X-Healthcheck": "true"}
            response = requests.post(
                f"http://localhost:{app.config['PORT']}/upload_image",
                files=files)
            if response.status_code == 200:
                health = "ok"
    except Exception as e:
        app.logger.warning(f"Health check failed: {e}")
    finally:
        processed["success"] = success
        processed["fail"] = fail

    uptime = time.time() - start_time
    status_response = {
        "status": {
            "uptime": round(uptime, 2),
            "processed": processed,
            "health": health,
            "api_version": API_VERSION
        }
    }
    return jsonify(status_response), 200

@app.errorhandler(405)
def method_not_allowed(_):
    error_response = {
        "error": {
            "http_status": 405,
            "message": "Method Not Allowed",
        }
    }
    return jsonify(error_response), 405

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    app.config["PORT"] = args.port
    app.run(host="0.0.0.0", port=args.port, debug=False)
