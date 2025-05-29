from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from database import fs, db  # Ensure your 'database.py' connects to MongoDB with GridFS
import os
import io
from bson import ObjectId
from geopy.geocoders import Nominatim

app = Flask(__name__)
CORS(app)

# Local file upload folder setup
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Utility: Reverse Geocoding
# -------------------------------
def get_location_details(latitude, longitude):
    try:
        geolocator = Nominatim(user_agent="image_upload_app")
        location = geolocator.reverse(f"{latitude}, {longitude}")
        if location:
            address = location.raw.get('address', {})
            return {
                "district": address.get('county', 'Unknown'),
                "state": address.get('state', 'Unknown'),
                "country": address.get('country', 'Unknown'),
                "city": address.get('city', address.get('town', address.get('village', 'Unknown'))),
                "postcode": address.get('postcode', 'Unknown')
            }
        return None
    except Exception as e:
        print(f"Location lookup error: {e}")
        return None

# -------------------------------
# Routes
# -------------------------------

@app.route('/')
def home():
    return "Backend is running!"

@app.route('/index')
def serve_index():
    return send_from_directory(os.getcwd(), "index.html")

@app.route('/gallery')
def serve_gallery():
    return send_from_directory(os.getcwd(), "gallery.html")

# -------------------------------
# Basic Local Upload (new)
# -------------------------------
@app.route('/upload-basic', methods=['POST'])
def upload_basic_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['image']
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return jsonify({'success': True})

# -------------------------------
# GridFS Upload with Location
# -------------------------------
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file found"}), 400

        image_file = request.files['image']
        username = request.form.get('username')
        email = request.form.get('email')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if not username or not email:
            return jsonify({"error": "Username and email are required"}), 400

        location_data = None
        location_details = None
        if latitude and longitude:
            try:
                location_data = {
                    "type": "Point",
                    "coordinates": [float(longitude), float(latitude)]
                }
                location_details = get_location_details(latitude, longitude)
            except ValueError:
                return jsonify({"error": "Invalid geolocation coordinates"}), 400

        file_id = fs.put(
            image_file,
            filename=image_file.filename,
            username=username,
            email=email,
            likes=[],
            location=location_data,
            location_details=location_details
        )

        return jsonify({
            "message": "Image uploaded successfully",
            "file_id": str(file_id),
            "username": username,
            "email": email,
            "location": location_data,
            "location_details": location_details
        }), 201

    except Exception as e:
        print("Upload error:", e)
        return jsonify({"error": "Internal server error"}), 500

# -------------------------------
# Image Routes
# -------------------------------
@app.route('/images', methods=['GET'])
def get_all_images():
    files = db.fs.files.find({}, {"_id": 1, "username": 1, "email": 1, "likes": 1, "location": 1})
    image_list = [{
        "_id": str(file["_id"]),
        "username": file.get("username", ""),
        "email": file.get("email", ""),
        "likes": len(file.get("likes", [])),
        "location": file.get("location")
    } for file in files]
    return jsonify(image_list)

@app.route('/image/<file_id>', methods=['GET'])
def get_image(file_id):
    try:
        image_data = fs.get(ObjectId(file_id))
        return send_file(io.BytesIO(image_data.read()), mimetype=image_data.content_type or "image/jpeg")
    except Exception as e:
        print("Image retrieval error:", e)
        return jsonify({"error": "Image not found"}), 404

@app.route('/image/<file_id>/like', methods=['POST'])
def like_image(file_id):
    try:
        user_ip = request.remote_addr
        image_data = db.fs.files.find_one({"_id": ObjectId(file_id)})
        if not image_data:
            return jsonify({"error": "Image not found"}), 404
        if user_ip in image_data.get("likes", []):
            return jsonify({"message": "You have already liked this image"}), 400
        db.fs.files.update_one({"_id": ObjectId(file_id)}, {"$push": {"likes": user_ip}})
        return jsonify({"message": "Image liked successfully"}), 200
    except Exception as e:
        print("Like error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/with-location', methods=['GET'])
def get_images_with_location():
    try:
        files = db.fs.files.find({
            "location": {"$exists": True, "$ne": None}
        }, {
            "_id": 1,
            "username": 1,
            "email": 1,
            "likes": 1,
            "location": 1,
            "location_details": 1
        })
        image_list = [{
            "_id": str(file["_id"]),
            "username": file.get("username", ""),
            "email": file.get("email", ""),
            "likes": len(file.get("likes", [])),
            "location": file.get("location"),
            "location_details": file.get("location_details", {})
        } for file in files]
        return jsonify(image_list)
    except Exception as e:
        print("Geolocation retrieval error:", e)
        return jsonify({"error": "Could not retrieve geotagged images"}), 500

@app.route('/get-location-details', methods=['GET'])
def get_location_details_route():
    try:
        latitude = request.args.get('lat')
        longitude = request.args.get('lon')
        if not latitude or not longitude:
            return jsonify({"error": "Latitude and longitude are required"}), 400
        location_details = get_location_details(latitude, longitude)
        if location_details:
            return jsonify(location_details)
        else:
            return jsonify({"error": "Could not retrieve location details"}), 404
    except Exception as e:
        print(f"Location details route error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# -------------------------------
# Run Server
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
