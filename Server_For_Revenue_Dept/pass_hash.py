from werkzeug.security import generate_password_hash

# Generate a properly formatted hash
print(generate_password_hash("12345678", method='pbkdf2:sha256'))
