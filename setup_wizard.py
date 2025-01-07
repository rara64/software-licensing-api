import sys
import subprocess
import os

try:
    process = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "-vvv", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            check=False
        )

    if process.stderr.strip() != "":
        print("\nSome requirements are not satisified. Please run: pip install -r requirements.txt")
        print("It is also recommended to run this app in a Python VENV. THIS HAS TO BE DONE BEFORE INSTALLING PACKAGES!")
        print("You can create a VENV using this command (provided you have virtualenv installed): python -m venv ./venv")
        print("...and then run it with one of the scripts in ./venv/Scripts\n")
        print("Detailed output of pip:")
        print(process.stderr)
        exit()
except FileNotFoundError:
        print("\n`pip` was not found, please ensure it is in your PATH.\n")
except subprocess.CalledProcessError as e:
        print(f"\nError occured when running pip: {e}\n")

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from pymongo import MongoClient
    import bcrypt
    import pyotp
    import qrcode
    import os.path
    import re
    import secrets
    import base64
    from modules.validator import is_valid_username
except ImportError:
    pass

print("\nWelcome to the software licensing API setup wizard!\n")

if os.path.isfile(".env"):
    print("[ERROR] .env file with configuration already exists, please remove it before using the setup wizard.\n")
    exit()

print("Please provide a MongoDB connection string (e.g. mongodb://localhost:27017/)")
MONGO_STRING = input()
while not MONGO_STRING.strip().startswith("mongodb://") or not MONGO_STRING.strip().endswith("/"):
    print("\n[ERROR] Please provide a MongoDB connection string that starts with 'mongodb://' and ends with '/':")
    MONGO_STRING = input()

print("Please provide a database name for MongoDB (e.g. api)")
MONGO_DBNAME = input()
while not re.match(r"^[A-Za-z]+$", MONGO_DBNAME):
    print("\n[ERROR] Please provide a valid name that consists only of upper or lower letters:")
    MONGO_DBNAME = input()

print("Please provide a name for the users collection (e.g. users)")
USERS_COLLECTION = input()
while not re.match(r"^[A-Za-z]+$", USERS_COLLECTION):
    print("\n[ERROR] Please provide a valid name that consists only of upper or lower letters:")
    USERS_COLLECTION = input()

print("Please provide a name for the licenses collection (e.g. licenses)")
LICENSES_COLLECTION = input()
while LICENSES_COLLECTION == USERS_COLLECTION or not re.match(r"^[A-Za-z]+$", LICENSES_COLLECTION):
    print("\n[ERROR] Please provide a valid name that consists only of upper or lower letters and is not the same as for the users collection:")
    LICENSES_COLLECTION = input()

print("\nLet's now verify the MongoDB connection and create an admin user - this user will be used for managing users and licenses.")

mongodb_connected = False
while not mongodb_connected:
    try:
        mongo_client = MongoClient(MONGO_STRING)[MONGO_DBNAME]
        mongodb_connected = True
    except Exception as e:
        print(f"\n[ERROR] An error occured while connecting to a MongoDB server. {e}\n")
        print("Please provide a valid MongoDB connection string:")
        MONGO_STRING = input()

print("\nConnection to a MongoDB server was successful.\n")
print("Please provide a username for admin user. (e.g. admin or something random so it isn't obvious it's an admin account)")
ADMIN_USERNAME = input()
while not is_valid_username(ADMIN_USERNAME):
    print("\n[ERROR] Admin username cannot be empty and can only consist of upper/lower letters or numbers. Please provide a new username:")
    ADMIN_USERNAME = input()

ADMIN_PASSWORD = f"{base64.urlsafe_b64encode(secrets.token_bytes(4)).decode('utf-8').rstrip('=')}-{base64.urlsafe_b64encode(secrets.token_bytes(4)).decode('utf-8').rstrip('=')}-{base64.urlsafe_b64encode(secrets.token_bytes(4)).decode('utf-8').rstrip('=')}"
print("\n!!!\nYour randomly generated password for admin account, keep it safe: " + ADMIN_PASSWORD + "\n!!!")

admin_created = False
ADMIN_ID=""

while not admin_created:
    try:
        user = mongo_client[USERS_COLLECTION].find_one({"username": ADMIN_USERNAME})
        if not user:
            hashed_password = bcrypt.hashpw(bytes(ADMIN_PASSWORD, 'utf-8'), bcrypt.gensalt())
            admin = mongo_client[USERS_COLLECTION].insert_one({"username": ADMIN_USERNAME, "password": hashed_password})
            ADMIN_ID = admin.inserted_id
            admin_created = True
        else:
            print("\n[ERROR] User with that name already exists. Please provide a new username:")
            ADMIN_USERNAME = input()
            while not is_valid_username(ADMIN_USERNAME):
                print("\n[ERROR] Admin username cannot be empty and can only consist of upper/lower letters or numbers. Please provide a new username:")
                ADMIN_USERNAME = input()
    except Exception as e:
        print(f"\n[ERROR] An errour occured while creating admin user. {e}\n")

print("\nDo you want to enable 2FA for admin user? (RECOMMENDED) y/n")
TFA_CHOICE = input().strip().lower()
ADMIN_OTP_SECRET = ""

if TFA_CHOICE == "y" or TFA_CHOICE == "yes":  
    ADMIN_OTP_SECRET = pyotp.random_base32()

    totp = pyotp.TOTP(ADMIN_OTP_SECRET)
    print("Provide issuer name for OTP QR-CODE for Authenticator app:")
    ISSUER = input()
    print("Provide account name for OTP QR-CODE for Authenticator app:")
    ACCOUNT = input()

    URI = totp.provisioning_uri(name=ACCOUNT, issuer_name=ISSUER)

    qr = qrcode.QRCode()
    qr.add_data(URI)
    qr.make(fit=True)
    print("\nScan this QR-CODE with any Authenticator app. DO NOT SHARE THIS QR CODE WITH ANYONE ELSE!")
    qr.print_ascii()
else:
    print("WARNING! 2FA for admin user was disabled.")

print("\nNow, let's setup JWT tokens.")
JWT_SECRET = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode('utf-8').rstrip('=')

print("Please provide a time in minutes for how long tokens should be valid. Lower is better, but may be annoying for users.")
JWT_KEEPALIVE_MINUTES = input()
while not re.match(r"^[0-9]+$", JWT_KEEPALIVE_MINUTES) or int(JWT_KEEPALIVE_MINUTES) <= 0:
    print("\n[ERROR] Please provide a value in number of minutes:")
    JWT_KEEPALIVE_MINUTES = input()

print("\nNow, let's setup the rate limiter for /auth API endpoint to prevent bruteforcing (per IP address). Limiter will store logs in `limits` database.")

print("Please provide ammount of allowed requests per day (for one IP address):")
AUTH_LIMITER_PER_DAY = input()
while not re.match(r"^[0-9]+$", AUTH_LIMITER_PER_DAY) or int(AUTH_LIMITER_PER_DAY) <= 0:
    print("\n[ERROR] Please provide a valid non-zero ammount of allowed requests per day (for one IP address):")
    AUTH_LIMITER_PER_DAY = input()

print("Please provide ammount of allowed requests per hour (for one IP address):")
AUTH_LIMITER_PER_HOUR = input()
while not re.match(r"^[0-9]+$", AUTH_LIMITER_PER_HOUR) or int(AUTH_LIMITER_PER_HOUR) <= 0:
    print("\n[ERROR] Please provide a valid non-zero ammount of allowed requests per hour (for one IP address):")
    AUTH_LIMITER_PER_HOUR = input()

print("\nNow let's generate a PRIVATE/PUBLIC KEY pair for signing licenses. Please copy the PUBLIC key to your app to verify licenses.")

PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

PRIVATE_KEY_PEM = PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)

PUBLIC_KEY = PRIVATE_KEY.public_key()
PUBLIC_KEY_PEM = PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

print()
print(PUBLIC_KEY_PEM.decode("utf-8"))

print("Saving to .env file...")

with open(".env", "w") as ENV:
    ENV.write(f'MONGO_STRING="{MONGO_STRING}"\n')
    ENV.write(f'MONGO_DBNAME="{MONGO_DBNAME}"\n')
    ENV.write(f'USERS_COLLECTION="{USERS_COLLECTION}"\n')
    ENV.write(f'LICENSES_COLLECTION="{LICENSES_COLLECTION}"\n')
    ENV.write(f'JWT_SECRET="{JWT_SECRET}"\n')
    ENV.write(f'TOKEN_KEEPALIVE_MINUTES="{JWT_KEEPALIVE_MINUTES}"\n')
    ENV.write(f'AUTH_LIMITER_PER_DAY="{AUTH_LIMITER_PER_DAY}"\n')
    ENV.write(F'AUTH_LIMITER_PER_HOUR="{AUTH_LIMITER_PER_HOUR}"\n')
    ENV.write(f'ADMIN_ID="{ADMIN_ID}"\n')
    ENV.write(f'ADMIN_OTP_SECRET="{ADMIN_OTP_SECRET}"\n')
    ENV.write(f'LICENSE_PRIVATE_KEY="{PRIVATE_KEY_PEM.decode("utf-8")}"\n')
    ENV.write(f'LICENSE_PUBLIC_KEY="{PUBLIC_KEY_PEM.decode("utf-8")}"\n')

print("Successfully saved the information to .env file. You can edit this file anytime you want to change settings, just keep the file secure. DO NOT EXPOSE IT TO THE WEB!")
print("\nYou can now run the app with: py app.py (or python app.py)\n")