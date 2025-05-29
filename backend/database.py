from pymongo import MongoClient
from gridfs import GridFS

# Connect to MongoDB
client = MongoClient("mongodb+srv://chennaicorprm:biuIvx7I7akjQx1B@cluster0.5y2ndpd.mongodb.net/VirtualTour?retryWrites=true&w=majority")
db = client.userUploads
fs = GridFS(db)

# Create a geospatial index for efficient location-based queries
db.fs.files.create_index([("location", "2dsphere")])