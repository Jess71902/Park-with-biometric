from flask import Flask, render_template, redirect, url_for, request, jsonify, session
import os
import cv2
import numpy as np
import face_recognition
import base64
import hashlib
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USER_FILE = 'user.txt'
FACE_DIR = 'face'

if not os.path.exists(FACE_DIR):
    os.makedirs(FACE_DIR)


# ---------- Utility functions ----------
def load_users_from_file():
    users = {}
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                data = eval(line.strip())
                if isinstance(data, dict):
                    users.update(data)
    return users

def save_users_to_file(users):
    with open(USER_FILE, "w") as f:
        for username, user_data in users.items():
            f.write(str({username: user_data}) + "\n")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_face_encoding(username, encoding):
    file_path = os.path.join(FACE_DIR, f"{username}.npy")
    np.save(file_path, encoding)

def load_face_encoding(username):
    file_path = os.path.join(FACE_DIR, f"{username}.npy")
    if os.path.exists(file_path):
        return np.load(file_path)
    return None

# ---------- Auth logic ----------
def register_user(username, email, password):
    current_users = load_users_from_file()
    if username in current_users:
        return False

    current_users[username] = {
        "email": email,
        "password": hash_password(password),
        "balance": 0,
        "vehicles": [],
        "selected_vehicle": "",
        "receipts": []
    }
    save_users_to_file(current_users)
    return True

def login_user(username, password):
    current_users = load_users_from_file()
    user = current_users.get(username)
    return user and user["password"] == hash_password(password)

def reset_user_password(username, new_password):
    current_users = load_users_from_file()
    user = current_users.get(username)
    if user:
        user["password"] = hash_password(new_password)
        save_users_to_file(current_users)
        return True
    return False

# ---------- Routes ----------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if login_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return '''
                <script>
                    alert("Incorrect username or password.");
                    window.location.href = "/";
                </script>
            '''
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        face_image_data = request.form['face_image']

        if not face_image_data:
            message = "Please capture your face before registering!"
            return render_template('register.html', message=message)

        header, encoded = face_image_data.split(',', 1)
        img_data = base64.b64decode(encoded)
        image_path = f"temp_{username}.png"
        with open(image_path, "wb") as f:
            f.write(img_data)

        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            os.remove(image_path)
            message = "No face detected!"
            return render_template('register.html', message=message)

        encoding = face_recognition.face_encodings(image, face_locations)[0]
        save_face_encoding(username, encoding)
        os.remove(image_path)

        if not register_user(username, email, password):
            message = "User already exists!"
        else:
            message = "Registration successful! Please return to login."

    return render_template('register.html', message=message)

@app.route('/face_login', methods=['GET', 'POST'])
def face_login():
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"status": "error", "message": "No image data provided"})

        header, encoded = data['image'].split(",", 1)
        img_bytes = base64.b64decode(encoded)

        temp_image_path = "temp_face.png"
        with open(temp_image_path, "wb") as f:
            f.write(img_bytes)

        image = face_recognition.load_image_file(temp_image_path)
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            os.remove(temp_image_path)
            return jsonify({"status": "error", "message": "No face detected!"})

        captured_encoding = face_recognition.face_encodings(image, face_locations)[0]
        os.remove(temp_image_path)

        users = load_users_from_file()
        for username in users:
            stored_encoding = load_face_encoding(username)
            if stored_encoding is not None and face_recognition.compare_faces([stored_encoding], captured_encoding)[0]:
                session['username'] = username
                return jsonify({"status": "success"})

        return jsonify({"status": "error", "message": "No matching user found"})

    return render_template('face_login.html')

@app.route('/face_verify', methods=['POST'])
def face_verify():
    username = session.get("username")
    if not username:
        return jsonify({"status": "fail", "message": "User not logged in"})

    data = request.get_json()
    image_data = data.get("image")
    if not image_data:
        return jsonify({"status": "error", "message": "No image data"})

    img_bytes = base64.b64decode(image_data.split(",")[1])
    np_img = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    if not face_encodings:
        return jsonify({"status": "fail", "message": "No face detected"})

    stored_encoding = load_face_encoding(username)
    if stored_encoding is not None and face_recognition.compare_faces([stored_encoding], face_encodings[0])[0]:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "message": "Face does not match"})

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    username = session.get("username")
    if not username:
        return redirect(url_for('index'))

    users = load_users_from_file()
    user = users.get(username)

    balance = user.get("balance", 0)
    selected_vehicle = user.get("selected_vehicle", "")
    payment_summary = ""
    parking_seconds = 0

    if request.method == "POST":
        location = request.form.get("location")
        duration = request.form.get("duration")

        if not selected_vehicle:
            payment_summary = "Please select a vehicle first."
        elif not location or not duration:
            payment_summary = "Please provide location and duration."
        else:
            try:
                duration = int(duration)
                fee_per_hour = 5
                total_payment = duration * fee_per_hour

                if total_payment > balance:
                    return '''
                        <script>
                            alert("Insufficient balance! Please reload your wallet.");
                            window.location.href = "/wallet";
                        </script>
                    '''
                else:
                    user["balance"] -= total_payment
                    balance = user["balance"]

                    receipt_data = {
                    "type": "payment",
                    "amount": total_payment,
                    "location": location,
                    "vehicle": selected_vehicle,  # ✅ Capture vehicle at time of payment
                    "duration": duration,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "reference": f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "status": "Successful"
                    }
                    user.setdefault("receipts", []).append(receipt_data)


                    save_users_to_file(users)

                    payment_summary = f"Payment successful: RM {total_payment} for {duration} hours at {location}."
                    parking_seconds = duration * 3600

            except ValueError:
                payment_summary = "Invalid duration value."

    return render_template('dashboard.html',
                           balance=balance,
                           selected_vehicle=selected_vehicle,
                           payment_summary=payment_summary,
                           parking_seconds=parking_seconds)

@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    username = session.get("username")
    if not username:
        return redirect(url_for('index'))

    users = load_users_from_file()
    user = users.get(username)

    if request.method == 'POST':
        amount = int(request.form.get("amount", 0))
        user["balance"] += amount

        receipt = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Reloaded RM{amount}"
        user.setdefault("receipts", []).append(receipt)

        save_users_to_file(users)
        return render_template("wallet.html", balance=user["balance"], message=f"Reload successful! Current balance: RM {user['balance']}")

    return render_template("wallet.html", balance=user["balance"], message="")

@app.route('/vehicle_list', methods=['GET', 'POST'])
def vehicle_list():
    username = session.get("username")
    if not username:
        return redirect(url_for("index"))

    users = load_users_from_file()
    user = users.get(username)

    if request.method == 'POST':
        action = request.form.get("action")
        if action == "add":
            new_vehicle = request.form.get("vehicle")
            if new_vehicle and new_vehicle not in user["vehicles"]:
                user["vehicles"].append(new_vehicle)
                user["selected_vehicle"] = new_vehicle
        elif action == "select":
            vehicle_to_select = request.form.get("vehicle_to_select")
            if vehicle_to_select in user["vehicles"]:
                user["selected_vehicle"] = vehicle_to_select

        save_users_to_file(users)
        return redirect(url_for("vehicle_list"))

    vehicles = user["vehicles"]
    selected_vehicle = user.get("selected_vehicle", "")
    return render_template("vehicle_list.html", vehicles=vehicles, selected_vehicle=selected_vehicle)

@app.route('/account', methods=['GET', 'POST'])
def account():
    username = session.get("username")
    if not username:
        return redirect(url_for('index'))

    users = load_users_from_file()
    user = users.get(username)

    if not user:
        return redirect(url_for('index'))

    if request.method == "POST":
        new_email = request.form.get("email")
        new_password = request.form.get("password")

        if new_email:
            user["email"] = new_email
        if new_password:
            user["password"] = hash_password(new_password)

        save_users_to_file(users)
        return redirect(url_for('account'))

    user_data = {
        "username": username,
        "email": user.get("email", ""),
        "password": "",
        "balance": user.get("balance", 0),
        "vehicles": user.get("vehicles", [])
    }

    return render_template("account.html", user_data=user_data)

@app.route('/history')
def history():
    username = session.get("username")
    if not username:
        return redirect(url_for('index'))

    users = load_users_from_file()
    user = users.get(username)

    # Initialize empty lists for history
    reload_history = []
    payment_history = []

    # Parse receipts into reload_history and payment_history
    for index, receipt in enumerate(user.get("receipts", [])):
        # Handle dictionary-based receipts (new format)
        if isinstance(receipt, dict):
            if receipt.get("type") == "reload":
                reload_history.append({
                    "amount": receipt["amount"],
                    "date": receipt["date"],
                    "reference": receipt["reference"],
                    "status": receipt["status"]
                })
            elif receipt.get("type") == "payment":
                payment_history.append({
                    "amount": receipt["amount"],
                    "location": receipt["location"],
                    "vehicle": receipt["vehicle"],
                    "duration": receipt["duration"],
                    "date": receipt["date"],
                    "reference": receipt["reference"],
                    "status": receipt["status"]
                })
        # Handle string-based receipts (old format)
        elif isinstance(receipt, str):
            # Extract date (first 19 characters: YYYY-MM-DD HH:MM:SS)
            date = receipt[:19]
            # Generate a unique reference using index
            reference = f"LEGACY-{index:04d}"

            # Check if it's a reload receipt
            reload_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - Reloaded RM(\d+)", receipt)
            if reload_match:
                reload_history.append({
                    "amount": int(reload_match.group(2)),
                    "date": date,
                    "reference": reference,
                    "status": "Successful"
                })
            # Check if it's a payment receipt
            payment_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - Paid RM(\d+) for (\d+) hours at (.+)", receipt)
            if payment_match:
                payment_history.append({
                    "amount": int(payment_match.group(2)),
                    "location": payment_match.group(4),
                    "vehicle": user.get("selected_vehicle", "Unknown"),  # Use current selected_vehicle
                    "duration": int(payment_match.group(3)),
                    "date": date,
                    "reference": reference,
                    "status": "Successful"
                })

    return render_template("history.html", reload_history=reload_history, payment_history=payment_history)

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        if reset_user_password(username, new_password):
            message = "Reset successful! Please return to login."
        else:
            message = "User not found!"
    return render_template('reset.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')
