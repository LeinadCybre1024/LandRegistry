from flask import Flask, jsonify, request, session, redirect
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from werkzeug.utils import secure_filename
import os
import bcrypt
from flask_cors import CORS
from datetime import datetime
import json
import base64
from datetime import timedelta  # Add this with your other imports

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["http://localhost:5500", "http://127.0.0.1:5500"]  # Your frontend URL
    }
})



# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client.LandRegistry
fs = gridfs.GridFS(db)

# Add this near the top of your Flask app
USER_ROLES = {
    'ADMIN': '12',
    'CLIENT': '34',
    'STAFF': '56'  # Added staff role
}

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)


@app.route('/check-session', methods=['GET'])
def check_session():
    
    user = db.users.find_one({"walletAddress": session['wallet_address']})
    if user:
        return jsonify({
            "authenticated": True,
            "user": {
                "name": user['name'],
                "walletAddress": user['walletAddress'],
                "role": user.get('userRole', USER_ROLES['CLIENT'])
                }
        })
    
    return jsonify({"authenticated": False}), 401

def normalize_wallet_address(address):
    """Normalize wallet address by converting to lowercase and stripping whitespace"""
    if not address:
        return None
    return address.strip().lower()
    
@app.route('/properties', methods=['GET', 'POST'])
def properties():
    if request.method == 'GET':
        # Get properties for the current user
        wallet_address = request.args.get('owner')
       ## print(wallet_address)
        if not wallet_address:
            return jsonify({"status": "error", "message": "Owner wallet address is required"}), 400
        
        properties = list(db.properties.find({"owner": wallet_address}))
        ##print(properties)
        
        if not properties:
            return jsonify({
                "status": "success",
                "message": "No properties found for this owner",
                "properties": []
            })
        
        # Convert MongoDB objects to JSON-serializable format
        serialized_properties = []
        for prop in properties:
            serialized_prop = {
                '_id': str(prop['_id']),
                'title': prop.get('title'),
                'streetAddress': prop.get('streetAddress'),
                'postalCode': prop.get('postalCode'),
                'county': prop.get('county'),
                'plotNumber': prop.get('plotNumber'),
                'owner': prop.get('owner'),
                'status': prop.get('status'),
                'createdAt': prop['createdAt'].isoformat() if 'createdAt' in prop else None,
                'updatedAt': prop['updatedAt'].isoformat() if 'updatedAt' in prop else None,
            }
        
            # Add document URLs if they exist
            if 'deedDocument' in prop:
                serialized_prop['deedDocumentUrl'] = f"/properties/{str(prop['_id'])}/deed"
            if 'idDocument' in prop:
                serialized_prop['idDocumentUrl'] = f"/properties/{str(prop['_id'])}/id"
            if 'surveyPlan' in prop:
                serialized_prop['surveyPlanUrl'] = f"/properties/{str(prop['_id'])}/survey"
            if 'passportPhoto' in prop:
                serialized_prop['passportPhotoUrl'] = f"/properties/{str(prop['_id'])}/photo"
        
            serialized_properties.append(serialized_prop)
    
        return jsonify({
            "status": "success",
            "properties": serialized_properties
        })
        
@app.route('/properties/<property_id>', methods=['GET', 'PUT', 'DELETE'])
def property(property_id):
    try:
        property_obj = db.properties.find_one({"_id": ObjectId(property_id)})
        if not property_obj:
            return jsonify({"status": "error", "message": "Property not found"}), 404

        # Verify ownership for write operations
        
        if request.method == 'GET':
            property_obj['_id'] = str(property_obj['_id'])
            return jsonify({"status": "success", "property": property_obj})

        elif request.method == 'PUT':
            # Update property
            update_data = request.get_json()
            update_data['updatedAt'] = datetime.utcnow()
            
            db.properties.update_one(
                {"_id": ObjectId(property_id)},
                {"$set": update_data}
            )
            
            return jsonify({"status": "success", "message": "Property updated"})

        elif request.method == 'DELETE':
            # Delete property and associated files
            file_fields = ['deedDocument', 'idDocument', 'surveyPlan', 'passportPhoto']
            for field in file_fields:
                if field in property_obj:
                    fs.delete(property_obj[field])
            
            db.properties.delete_one({"_id": ObjectId(property_id)})
            
            return jsonify({"status": "success", "message": "Property deleted"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/properties/<property_id>/<document_type>', methods=['GET'])
def property_document(property_id, document_type):
    try:
        property_obj = db.properties.find_one({"_id": ObjectId(property_id)})
        if not property_obj:
            return jsonify({"status": "error", "message": "Property not found"}), 404

        if document_type not in ['deed', 'id', 'survey', 'photo']:
            return jsonify({"status": "error", "message": "Invalid document type"}), 400

        # Map URL types to document fields
        doc_map = {
            'deed': 'deedDocument',
            'id': 'idDocument',
            'survey': 'surveyPlan',
            'photo': 'passportPhoto'
        }

        doc_field = doc_map[document_type]
        if doc_field not in property_obj:
            return jsonify({"status": "error", "message": "Document not found"}), 404

        file_obj = fs.get(property_obj[doc_field])
        return file_obj.read(), 200, {
            'Content-Type': 'application/pdf' if document_type != 'photo' else 'image/jpeg',
            'Content-Disposition': f'inline; filename="{file_obj.filename}"'
        }

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
    




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    password = data.get('password')

    user = db.users.find_one({"walletAddress": wallet_address})
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"status": "error", "message": "Invalid password"}), 401

    session['user_id'] = str(user['_id'])
    session['wallet_address'] = wallet_address
    session['user_role'] = user.get('userRole', USER_ROLES['CLIENT'])

    return jsonify({
        "status": "success",
        "user": {
            "name": user['name'],
            "walletAddress": user['walletAddress'],
            "role": user.get('userRole', USER_ROLES['CLIENT'])
        },
        "token": str(user['_id'])
    })

@app.route('/logout', methods=['POST'])
def logout_user():
    session.clear()
    return jsonify({"status": "success"})

@app.route('/register', methods=['POST'])
def register_user():
    try:
        # Get form data
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        wallet_address = request.form.get('walletAddress')
        password = request.form.get('password')
        id_number = request.form.get('idNumber')
        
        # Get files
        passport_photo = request.files.get('passportPhoto')
        id_document = request.files.get('idDocument')

        # Validate required fields
        if not all([first_name, last_name, wallet_address, password, date_of_birth, id_number]):
            return jsonify({"status": "error", "message": "All fields are required"}), 400

        # Check if user already exists
        if db.users.find_one({"walletAddress": wallet_address}):
            return jsonify({"status": "error", "message": "User already exists"}), 400

        # Check if ID number is already registered
        if db.users.find_one({"idNumber": id_number}):
            return jsonify({"status": "error", "message": "ID number already registered"}), 400

        # Validate files
        if not passport_photo or not id_document:
            return jsonify({"status": "error", "message": "Both passport photo and ID document are required"}), 400

        if not allowed_file(passport_photo.filename) or not allowed_file(id_document.filename):
            return jsonify({"status": "error", "message": "Invalid file type"}), 400

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Store files in GridFS
        passport_id = fs.put(
            passport_photo.read(),
            filename=f"{wallet_address}_passport.{passport_photo.filename.split('.')[-1]}",
            contentType=passport_photo.content_type
        )
        
        id_doc_id = fs.put(
            id_document.read(),
            filename=f"{wallet_address}_id.{id_document.filename.split('.')[-1]}",
            contentType=id_document.content_type
        )

        # Create user document
        user_data = {
            "firstName": first_name,
            "lastName": last_name,
            "walletAddress": wallet_address,
            "password": hashed_password,
            "idNumber": id_number,
            "passportPhoto": passport_id,
            "idDocument": id_doc_id,
            "userRole": USER_ROLES['CLIENT'],
            "createdAt": datetime.utcnow(),
            "status": "pending",  # New users need admin approval
            "kycVerified": False
        }

        # Insert user into database
        user_id = db.users.insert_one(user_data).inserted_id

        # Set session data
        session['user_id'] = str(user_id)
        session['wallet_address'] = wallet_address
        session['user_role'] = USER_ROLES['CLIENT']

        return jsonify({
            "status": "success",
            "message": "Registration successful. Awaiting admin approval.",
            "user": {
                "firstName": first_name,
                "lastName": last_name,
                "walletAddress": wallet_address,
                "role": USER_ROLES['CLIENT']
            }
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/admin/properties', methods=['GET'])
def admin_properties():
    status = request.args.get('status', 'pending')
    properties = list(db.properties.find({"status": status}))
    
    result = []
    for prop in properties:
        # Convert MongoDB document to a serializable format
        serialized_prop = {
            '_id': str(prop['_id']),
            'title': prop.get('title'),
            'streetAddress': prop.get('streetAddress'),
            'postalCode': prop.get('postalCode'),
            'county': prop.get('county'),
            'plotNumber': prop.get('plotNumber'),
            'owner': prop.get('owner'),
            'status': prop.get('status'),
            'createdAt': prop['createdAt'].isoformat() if 'createdAt' in prop else None,
            'updatedAt': prop['updatedAt'].isoformat() if 'updatedAt' in prop else None,
            'deedDocument': str(prop['deedDocument']) if 'deedDocument' in prop else None,
            'idDocument': str(prop['idDocument']) if 'idDocument' in prop else None,
            'passportPhoto': str(prop['passportPhoto']) if 'passportPhoto' in prop else None,
            'surveyPlan': str(prop['surveyPlan']) if 'surveyPlan' in prop else None
        }
        
        # Add owner details
        owner = db.users.find_one({"walletAddress": prop['owner']}, {"name": 1, "walletAddress": 1})
        if owner:
            serialized_prop['ownerDetails'] = {
                "name": owner['name'],
                "walletAddress": owner['walletAddress']
            }
        
        result.append(serialized_prop)
    
    return jsonify({
        "status": "success",
        "properties": result
    })

@app.route('/admin/properties/<property_id>/verify/<user_wallet>', methods=['POST'])
def verify_property(property_id, user_wallet):
    property_obj = db.properties.find_one({"_id": ObjectId(property_id)})
    if not property_obj:
        return jsonify({"status": "error", "message": "Property not found"}), 404
    
    user = db.users.find_one({"walletAddress": user_wallet})
    if not user or user.get('userRole') != USER_ROLES['ADMIN']:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    data = request.get_json()
    action = data.get('action')
    reason = data.get('reason', '') if action == 'reject' else ''
    
    if action not in ['approve', 'reject']:
        return jsonify({"status": "error", "message": "Invalid action"}), 400
    
    
    new_status = "verified" if action == "approve" else "rejected"
    
    update_data = {
        "status": new_status,
        "updatedAt": datetime.utcnow(),
        "verifiedBy": user_wallet,
        "verificationDate": datetime.utcnow()
    }
    
    if action == 'reject':
        update_data['rejectionReason'] = reason
    
    db.properties.update_one(
        {"_id": ObjectId(property_id)},
        {"$set": update_data}
    )
    
    return jsonify({
        "status": "success",
        "message": f"Property {action}d successfully"
    })


@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    
    if request.method == 'GET':
        role_filter = request.args.get('role')
        query = {}
        if role_filter in USER_ROLES.values():
            query['userRole'] = role_filter
        
        users = list(db.users.find(query, {"password": 0}))
        
        for user in users:
            user['_id'] = str(user['_id'])
            if 'createdAt' in user:
                user['createdAt'] = user['createdAt'].isoformat()
        
        return jsonify({
            "status": "success",
            "users": users
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['name', 'walletAddress', 'password', 'userRole']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"status": "error", "message": f"{field} is required"}), 400
        
        if db.users.find_one({"walletAddress": data['walletAddress']}):
            return jsonify({"status": "error", "message": "User already exists"}), 400
        
        if data['userRole'] not in USER_ROLES.values():
            return jsonify({"status": "error", "message": "Invalid user role"}), 400
        
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            "name": data['name'],
            "walletAddress": data['walletAddress'],
            "password": hashed_password,
            "userRole": data['userRole'],
            "createdAt": datetime.utcnow(),
            "status": "active",
            "createdBy": session['wallet_address']
        }
        
        user_id = db.users.insert_one(user_data).inserted_id
        
        return jsonify({
            "status": "success",
            "message": "User created successfully",
            "userId": str(user_id)
        })

@app.route('/profile/change-password', methods=['POST'])
def change_password():
    data = request.get_json()
    user_address = data.get('currentWalletAddress')
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    if not current_password or not new_password:
        return jsonify({"status": "error", "message": "Both current and new password are required"}), 400
    
    user = db.users.find_one({"walletAddress": user_address})
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    if not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
        return jsonify({"status": "error", "message": "Current password is incorrect"}), 401
    
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    db.users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$set": {"password": hashed_password}}
    )
    
    return jsonify({
        "status": "success",
        "message": "Password changed successfully"
    })



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')