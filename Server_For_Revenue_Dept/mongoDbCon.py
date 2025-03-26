from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")  # Change this to your MongoDB connection string

# Connect to a specific database
db = client.LandRegistry  # Change 'LandRegistry' to your database name

# Get the list of collections (tables) in the database
collections = db.list_collection_names()

# Print the collections
print("Collections in the database:", collections)

