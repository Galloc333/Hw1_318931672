import requests
import os
import pytest

SERVER_URL = "http://localhost:8080"  # adjust port if needed


def test_status_endpoint():
    response = requests.get(f"{SERVER_URL}/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime" in data["status"]
    assert "processed" in data["status"]
    assert "health" in data["status"]
    assert "api_version" in data["status"]

def test_upload_valid_image():
    image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    assert os.path.exists(image_path), "test_image.jpg not found"

    with open(image_path, "rb") as img:
        files = {"image": ("test_image.jpg", img, "image/jpeg")}
        response = requests.post(f"{SERVER_URL}/upload_image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)
    assert all("name" in match and "score" in match for match in data["matches"])

def test_upload_invalid_file():
    fake_path = os.path.join(os.path.dirname(__file__), "bad.txt")
    with open(fake_path, "w") as f:
        f.write("this is not an image")
    with open(fake_path, "rb") as f:
        files = {"image": ("bad.txt", f, "text/plain")}
        response = requests.post(f"{SERVER_URL}/upload_image", files=files)

    os.remove(fake_path)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["http_status"] == 400

def test_upload_wrong_method():
    response = requests.get("http://localhost:8080/upload_image")
    assert response.status_code == 405

def test_upload_missing_image_field():
    response = requests.post("http://localhost:8080/upload_image", files={})
    assert response.status_code == 400
    assert "error" in response.json()

def test_upload_fake_jpg_with_txt_content():
    fake_jpg_path = os.path.join(os.path.dirname(__file__), "fake.jpg")
    with open(fake_jpg_path, "w") as f:
        f.write("this is not an image but has .jpg extension")

    with open(fake_jpg_path, "rb") as f:
        files = {"image": ("fake.jpg", f, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    os.remove(fake_jpg_path)
    assert response.status_code == 400
    assert response.json()["error"]["http_status"] == 400

def test_upload_html_file_with_jpg_name():
    html_content = "<html><h1>I am not a rabbit</h1></html>"
    fake_path = os.path.join(os.path.dirname(__file__), "rabbit.html.jpg")
    with open(fake_path, "w") as f:
        f.write(html_content)

    with open(fake_path, "rb") as f:
        files = {"image": ("rabbit.html.jpg", f, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    os.remove(fake_path)
    assert response.status_code == 400



def test_upload_with_wrong_form_field_name():
    image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    with open(image_path, "rb") as img:
        files = {"not_image": ("test_image.jpg", img, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    assert response.status_code == 400

def test_upload_empty_file():
    empty_path = os.path.join(os.path.dirname(__file__), "empty.jpg")
    open(empty_path, "wb").close()  # create empty file

    with open(empty_path, "rb") as f:
        files = {"image": ("empty.jpg", f, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    os.remove(empty_path)
    assert response.status_code == 400 or response.status_code == 500

def test_response_json_fields_strictness():
    image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    with open(image_path, "rb") as img:
        files = {"image": ("test_image.jpg", img, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    data = response.json()
    for match in data["matches"]:
        assert isinstance(match["name"], str)
        assert isinstance(match["score"], float)
        assert 0.0 < match["score"] <= 1.0

def test_upload_with_long_filename():
    long_name = "a" * 300 + ".jpg"
    image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    with open(image_path, "rb") as img:
        files = {"image": (long_name, img, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    assert response.status_code in [200, 400]


def test_upload_with_double_extension():
    image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    with open(image_path, "rb") as img:
        files = {"image": ("photo.jpg.exe", img, "image/jpeg")}
        response = requests.post("http://localhost:8080/upload_image", files=files)

    assert response.status_code == 400


