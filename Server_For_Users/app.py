from flask import Flask, jsonify, request, session, redirect, send_file
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
from web3 import Web3
from web3.middleware import geth_poa_middleware
import uuid

# Configure upload settings
UPLOAD_FOLDER = 'uploads/properties'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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



app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

def allowed_file(filename):
    return '.' in filename and  filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/users/search', methods=['GET'])
def search_users():
    try:
        search_term = request.args.get('q')
        if not search_term:
            return jsonify({"status": "error", "message": "Search term is required"}), 400

        # Search by name or wallet address (case insensitive)
        query = {
            "$or": [
                {"firstName": {"$regex": search_term, "$options": "i"}},
                {"lastName": {"$regex": search_term, "$options": "i"}},
                {"walletAddress": {"$regex": search_term, "$options": "i"}}
            ],
            "status": "active"  # Only show active users
        }

        # Include only users that have either firstName, lastName, or walletAddress
        query["$and"] = [{
            "$or": [
                {"firstName": {"$exists": True, "$ne": ""}},
                {"lastName": {"$exists": True, "$ne": ""}},
                {"walletAddress": {"$exists": True, "$ne": ""}}
            ]
        }]

        users = list(db.users.find(query, {
            "firstName": 1,
            "lastName": 1,
            "walletAddress": 1,
            "_id": 0  # Exclude the _id field
        }))

        if not users:
            return jsonify({
                "status": "success",
                "message": "No users found",
                "users": []
            })

        # Filter out any None or empty values from the results
        cleaned_users = []
        for user in users:
            cleaned_user = {
                "firstName": user.get("firstName", ""),
                "lastName": user.get("lastName", ""),
                "walletAddress": user.get("walletAddress", "")
            }
            cleaned_users.append(cleaned_user)

        return jsonify({
            "status": "success",
            "users": cleaned_users
        })

    except Exception as e:
        print(f'Search error: {str(e)}')
        return jsonify({
            "status": "error",
            "message": "Error searching users"
        }), 500


@app.route('/properties/<property_id>/transfer', methods=['POST'])
def transfer_property(property_id):
    try:
        
        data = request.get_json()
        current_owner = data.get('currentOwner')
        new_owner = data.get('newOwner')
        tx_hash = data.get('txHash')

        # Validate input
        if not all([current_owner, new_owner, tx_hash]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Get the property
        property_obj = db.properties.find_one({"_id": property_id})
        if not property_obj:
            return jsonify({"status": "error", "message": "Property not found"}), 404

        # Verify current owner matches
        if property_obj['owner'].lower() != current_owner.lower():
            return jsonify({"status": "error", "message": "Current owner doesn't match"}), 400

        # Verify new owner exists in system
        new_owner_user = db.users.find_one({"walletAddress": new_owner})
        if not new_owner_user:
            return jsonify({"status": "error", "message": "New owner not registered in system"}), 400

        # Update property ownership
        update_result = db.properties.update_one(
            {"_id": property_id},
            {
                "$set": {
                    "owner": new_owner,
                    "previousOwners": property_obj.get('previousOwners', []) + [{
                        "walletAddress": current_owner,
                        "transferDate": datetime.utcnow(),
                        "txHash": tx_hash
                    }],
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        if update_result.modified_count == 0:
            return jsonify({"status": "error", "message": "Failed to update property"}), 500

        # Add transaction to history
        db.transactions.insert_one({
            "propertyId": property_id,
            "fromAddress": current_owner,
            "toAddress": new_owner,
            "txHash": tx_hash,
            "timestamp": datetime.utcnow(),
            "type": "ownership_transfer"
        })

        return jsonify({
            "status": "success",
            "message": "Property ownership updated successfully"
        })

    except Exception as e:
        print(f"Error transferring property: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/properties/search', methods=['GET'])
def search_property():
    plot_number = request.args.get('plotNumber')
    if not plot_number:
        return jsonify({"status": "error", "message": "Plot number is required"}), 400
    
    property = db.properties.find_one({"plotNumber": plot_number})
    if not property:
        return jsonify({"status": "success", "property": None})
    
    # Get owner details
    owner = db.users.find_one({"walletAddress": property['owner']}, 
                            {"firstName": 1, "lastName": 1, "walletAddress": 1})
    
    serialized_prop = {
        '_id': str(property['_id']),
        'title': property.get('title'),
        'streetAddress': property.get('streetAddress'),
        'postalCode': property.get('postalCode'),
        'county': property.get('county'),
        'plotNumber': property.get('plotNumber'),
        'owner': property.get('owner'),
        'status': property.get('status'),
        'createdAt': property['createdAt'].isoformat() if 'createdAt' in property else None,
        'ownerDetails': {
            "firstName": owner['firstName'],
            "lastName": owner['lastName'],
            "walletAddress": owner['walletAddress']
        } if owner else None
    }
    
    return jsonify({
        "status": "success",
        "property": serialized_prop
    })

@app.route('/admin/users/<user_id>/approve', methods=['POST'])
def approve_user(user_id):
    try:
        """ Verify admin
        if 'wallet_address' not in session or session.get('user_role') != USER_ROLES['ADMIN']:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        """
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status": "active",
                "kycVerified": True,
                "approvedAt": datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            return jsonify({"status": "error", "message": "User not found or already approved"}), 404
        
        return jsonify({
            "status": "success",
            "message": "User approved successfully"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/check-session', methods=['GET'])
def check_session():
    if 'wallet_address' not in session:
        return jsonify({"authenticated": False}), 401
    
    user = db.users.find_one({"walletAddress": session['wallet_address']})
    if user:
        return jsonify({
            "authenticated": True,
            "user": {
                "firstName": user['firstName'],
                "lastName": user['lastName'],
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
    

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/properties', methods=['GET', 'POST'])
def properties():
    if request.method == 'GET':
        # Get properties for the current user
        wallet_address = request.args.get('owner')
        if not wallet_address:
            return jsonify({"status": "error", "message": "Owner wallet address is required"}), 400
        
        properties = list(db.properties.find({"owner": wallet_address}))
        
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
                'blockchainPropertyId': prop.get('blockchainPropertyId'),
                'status': prop.get('status', 'pending'),  # Default to 'pending' if not set
                'createdAt': prop['createdAt'].isoformat() if 'createdAt' in prop else None,
                'updatedAt': prop['updatedAt'].isoformat() if 'updatedAt' in prop else None,
            }
        
            # Add document URLs if they exist
            if 'deedDocument' in prop:
                serialized_prop['deedDocumentUrl'] = f"/properties/{str(prop['_id'])}/deed"
            if 'surveyPlan' in prop:
                serialized_prop['surveyPlanUrl'] = f"/properties/{str(prop['_id'])}/survey"
        
            serialized_properties.append(serialized_prop)
            
            print(serialized_properties)
    
        return jsonify({
            "status": "success",
            "properties": serialized_properties
        })

    elif request.method == 'POST':
        # Handle property creation
        try:
            # Parse property data
            property_data = request.form.get('property')
            if not property_data:
                return jsonify({"status": "error", "message": "Property data is required"}), 400
            
            property_json = json.loads(property_data)
            
            # Validate required fields
            required_fields = ['title', 'streetAddress', 'postalCode', 'county', 'plotNumber', 'owner']
            for field in required_fields:
                if not property_json.get(field):
                    return jsonify({"status": "error", "message": f"{field} is required"}), 400

            # Handle file uploads
            deed_document = request.files.get('deedDocument')
            survey_plan = request.files.get('surveyPlan')

            if not deed_document:
                return jsonify({"status": "error", "message": "Title deed document is required"}), 400

            # Generate unique filenames
            property_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Save deed document
            if deed_document and allowed_file(deed_document.filename):
                deed_filename = f"{property_id}_deed_{secure_filename(deed_document.filename)}"
                deed_path = os.path.join(UPLOAD_FOLDER, deed_filename)
                deed_document.save(deed_path)
            else:
                return jsonify({"status": "error", "message": "Invalid title deed document"}), 400

            # Save survey plan if provided
            survey_path = None
            if survey_plan and allowed_file(survey_plan.filename):
                survey_filename = f"{property_id}_survey_{secure_filename(survey_plan.filename)}"
                survey_path = os.path.join(UPLOAD_FOLDER, survey_filename)
                survey_plan.save(survey_path)
            
            print(property_json)

            # Create property document
            property_doc = {
                '_id': property_id,
                'title': property_json['title'],
                'streetAddress': property_json['streetAddress'],
                'postalCode': property_json['postalCode'],
                'county': property_json['county'],
                'plotNumber': property_json['plotNumber'],
                'owner': property_json['owner'],
                'status': 'pending',  # Default status
                'deedDocument': deed_path,
               'blockchainPropertyId': property_json['blockchainPropertyId'],
                'createdAt': now,
                'updatedAt': now
            }

            # Add survey plan if provided
            if survey_path:
                property_doc['surveyPlan'] = survey_path

            # Insert into database
            db.properties.insert_one(property_doc)

            return jsonify({
                "status": "success",
                "message": "Property created successfully",
                "propertyId": property_id
            })

        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "Invalid property data format"}), 400
        except Exception as e:
            print(f"Error creating property: {str(e)}")
            return jsonify({"status": "error", "message": "Failed to create property"}), 500

# Add endpoint to serve property documents
@app.route('/properties/<property_id>/<document_type>', methods=['GET'])
def get_property_document(property_id, document_type):
    if document_type not in ['deed', 'survey']:
        return jsonify({"status": "error", "message": "Invalid document type"}), 400
    
    property = db.properties.find_one({"_id": property_id})
    if not property:
        return jsonify({"status": "error", "message": "Property not found"}), 404
    
    file_path = property.get(f"{document_type}Document")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Document not found"}), 404
    
    return send_file(file_path, as_attachment=True)
        
@app.route('/properties/<property_id>', methods=['GET', 'PUT', 'DELETE'])
def property(property_id):
    try:
        property_obj = db.properties.find_one({"_id": property_id})
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
            
            db.properties.delete_one({"_id": property_id})
            
            return jsonify({"status": "success", "message": "Property deleted"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/properties/<property_id>/<document_type>', methods=['GET'])
def property_document(property_id, document_type):
    try:
        property_obj = db.properties.find_one({"_id": property_id})
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
    
    





@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    password = data.get('password')

    # Validate required fields
    if not wallet_address or not password:
        return jsonify({"status": "error", "message": "Wallet address and password are required"}), 400

    user = db.users.find_one({"walletAddress": wallet_address})
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Check if user has required fields
    if 'firstName' not in user or not user['firstName'] or 'lastName' not in user or not user['lastName']:
        return jsonify({
            "status": "error",
            "message": "User profile incomplete. Please contact support to update your profile details."
        }), 200

    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"status": "error", "message": "Invalid password"}), 401

    session['user_id'] = str(user['_id'])
    session['wallet_address'] = wallet_address
    session['user_role'] = user.get('userRole', USER_ROLES['CLIENT'])

    return jsonify({
        "status": "success",
        "user": {
            "firstName": user['firstName'],
            "lastName": user['lastName'],
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
        if not all([first_name, last_name, wallet_address, password, id_number]):
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
        serialized_prop = {
            '_id': str(prop['_id']),
            'title': prop.get('title'),
            'streetAddress': prop.get('streetAddress'),
            'postalCode': prop.get('postalCode'),
            'county': prop.get('county'),
            'plotNumber': prop.get('plotNumber'),
            'blockchainPropertyId': prop.get('blockchainPropertyId'),
            'owner': prop.get('owner'),
            'status': prop.get('status'),
            'createdAt': prop['createdAt'].isoformat() if 'createdAt' in prop else None,
            'updatedAt': prop['updatedAt'].isoformat() if 'updatedAt' in prop else None,
        }
        
        # Add owner details with firstName and lastName
        owner = db.users.find_one({"walletAddress": prop['owner']}, 
                                {"firstName": 1, "lastName": 1, "walletAddress": 1})
        if owner:
            serialized_prop['ownerDetails'] = {
                "firstName": owner['firstName'],
                "lastName": owner['lastName'],
                "walletAddress": owner['walletAddress']
            }
        
        result.append(serialized_prop)
    
    return jsonify({
        "status": "success",
        "properties": result
    })

@app.route('/admin/properties/<property_id>/verify/<user_wallet>', methods=['POST'])
def verify_property(property_id, user_wallet):
    property_obj = db.properties.find_one({"_id": property_id})
    if not property_obj:
        return jsonify({"status": "error", "message": "Property not found"}), 404
    
    user = db.users.find_one({"walletAddress": user_wallet})
    """
    if not user or user.get('userRole') != USER_ROLES['ADMIN']:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    """
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
        {"_id": property_id},
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
        
        # Convert MongoDB documents to JSON-serializable format
        serialized_users = []
        for user in users:
            serialized_user = {
                '_id': str(user['_id']),
                'firstName': user.get('firstName'),
                'lastName': user.get('lastName'),
                'walletAddress': user.get('walletAddress'),
                'userRole': user.get('userRole'),
                'status': user.get('status'),
                'createdAt': user['createdAt'].isoformat() if 'createdAt' in user else None,
                'idNumber': user.get('idNumber'),
                'kycVerified': user.get('kycVerified', False)
            }
            serialized_users.append(serialized_user)
        
        return jsonify({
            "status": "success",
            "users": serialized_users
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['firstName', 'lastName', 'walletAddress', 'password', 'userRole']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"status": "error", "message": f"{field} is required"}), 400
        
        if db.users.find_one({"walletAddress": data['walletAddress']}):
            return jsonify({"status": "error", "message": "User already exists"}), 400
        
        if data['userRole'] not in USER_ROLES.values():
            return jsonify({"status": "error", "message": "Invalid user role"}), 400
        
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            "firstName": data['firstName'],
            "lastName": data['lastName'],
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
            "userId": str(user_id)  # Convert ObjectId to string
        })

@app.route('/admin/users/<user_id>', methods=['GET'])
def admin_user_details(user_id):
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Convert to JSON-serializable format
        user_data = {
            "_id": str(user["_id"]),
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
            "walletAddress": user.get("walletAddress"),
            "userRole": user.get("userRole"),
            "status": user.get("status"),
            "idNumber": user.get("idNumber"),
            "kycVerified": user.get("kycVerified", False),
            "createdAt": user["createdAt"].isoformat() if "createdAt" in user else None
        }

        # Add document URLs if they exist
        if "passportPhoto" in user:
            user_data["passportPhotoUrl"] = f"/admin/users/{str(user['_id'])}/passport"
        if "idDocument" in user:
            user_data["idDocumentUrl"] = f"/admin/users/{str(user['_id'])}/idDocument"

        return jsonify({
            "status": "success",
            "user": user_data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/users/<user_id>/<document_type>', methods=['GET'])
def user_document(user_id, document_type):
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        if document_type not in ['passportPhoto', 'idDocument']:
            return jsonify({"status": "error", "message": "Invalid document type"}), 400

        doc_field = document_type
        if doc_field not in user:
            return jsonify({"status": "error", "message": "Document not found"}), 404

        file_obj = fs.get(user[doc_field])
        return file_obj.read(), 200, {
            'Content-Type': 'image/jpeg',
            'Content-Disposition': f'inline; filename="{file_obj.filename}"'
        }

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
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