from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from database import fs, db
import io
from bson import ObjectId
import os
import requests
from geopy.geocoders import Nominatim

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

def get_location_details(latitude, longitude):
    """
    Retrieve detailed location information using reverse geocoding
    """
    try:
        # Initialize Nominatim geocoder
        geolocator = Nominatim(user_agent="image_upload_app")
        
        # Perform reverse geocoding
        location = geolocator.reverse(f"{latitude}, {longitude}")
        
        if location:
            address = location.raw.get('address', {})
            
            # Extract location details
            location_info = {
                "district": address.get('county', 'Unknown'),
                "state": address.get('state', 'Unknown'),
                "country": address.get('country', 'Unknown'),
                "city": address.get('city', address.get('town', address.get('village', 'Unknown'))),
                "postcode": address.get('postcode', 'Unknown')
            }
            
            return location_info
        
        return None
    
    except Exception as e:
        print(f"Location lookup error: {e}")
        return None

# Serve the gallery.html file from the same folder
@app.route('/')
def serve_gallery():
    return send_from_directory(os.getcwd(), "gallery.html")

# Serve the index.html file
@app.route('/index')
def serve_index():
    return send_from_directory(os.getcwd(), "index.html")

# API to get all image IDs
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

# Route to upload an image with user details and geolocation
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Check for required fields
        if 'image' not in request.files:
            return jsonify({"error": "No image file found"}), 400

        image_file = request.files['image']
        username = request.form.get('username')
        email = request.form.get('email')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if not username or not email:
            return jsonify({"error": "Username and email are required"}), 400

        # Prepare geolocation data
        location_data = None
        location_details = None
        if latitude and longitude:
            try:
                # Geospatial coordinates
                location_data = {
                    "type": "Point",
                    "coordinates": [float(longitude), float(latitude)]
                }
                
                # Get detailed location information
                location_details = get_location_details(latitude, longitude)
            except ValueError:
                return jsonify({"error": "Invalid geolocation coordinates"}), 400

        # Store image and user info in GridFS
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

# Route to retrieve an image by ID
@app.route('/image/<file_id>', methods=['GET'])
def get_image(file_id):
    try:
        image_data = fs.get(ObjectId(file_id))
        return send_file(io.BytesIO(image_data.read()), mimetype="image/jpeg")
    except Exception as e:
        print("Image retrieval error:", e)
        return jsonify({"error": "Image not found"}), 404

# Route to like an image
@app.route('/image/<file_id>/like', methods=['POST'])
def like_image(file_id):
    try:
        user_ip = request.remote_addr  # Capture user IP

        image_data = db.fs.files.find_one({"_id": ObjectId(file_id)})

        if not image_data:
            return jsonify({"error": "Image not found"}), 404

        # Check if user already liked the image
        if user_ip in image_data.get("likes", []):
            return jsonify({"message": "You have already liked this image"}), 400

        # Add user IP to the likes
        db.fs.files.update_one({"_id": ObjectId(file_id)}, {"$push": {"likes": user_ip}})

        return jsonify({"message": "Image liked successfully"}), 200

    except Exception as e:
        print("Like error:", e)
        return jsonify({"error": "Internal server error"}), 500

# Route to get images with geolocation
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

# Route to get location details
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

if __name__ == '__main__':
    app.run(debug=True)