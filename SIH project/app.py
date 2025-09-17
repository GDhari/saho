from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
import qrcode

app = Flask(__name__)

# ----------------- Secret Key (from environment) -----------------
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret")

# ----------------- Database setup -----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(200))
    adhaar = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    username = db.Column(db.String(50))
    password = db.Column(db.String(200))
    gmail = db.Column(db.String(200))
    tourist_id = db.Column(db.String(50), unique=True)
    qr_code = db.Column(db.String(200))
    latitude = db.Column(db.Float, default=0.0)
    longitude = db.Column(db.Float, default=0.0)
    safety_score = db.Column(db.Integer, default=100)

with app.app_context():
    db.create_all()

# ----------------- QR Code Generator -----------------
def generate_qr(tourist_id):
    folder = "static/qrcodes"
    os.makedirs(folder, exist_ok=True)
    filename = f"{folder}/{tourist_id}.png"
    img = qrcode.make(tourist_id)
    img.save(filename)
    return filename

# ----------------- Google OAuth -----------------
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ----------------- Routes -----------------
@app.route('/')
def home():
    return render_template("login.html")

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def callback():
    token = google.authorize_access_token()  
    user_info = google.userinfo()  # fetch user info safely
    session['user'] = user_info

    google_id = user_info.get('sub')
    existing_user = User.query.filter_by(google_id=google_id).first()
    if existing_user:
        return redirect(url_for('dashboard'))

    return redirect(url_for('form'))

@app.route('/form', methods=['GET', 'POST'])
def form():
    if 'user' not in session:
        return redirect(url_for('home'))

    gmail = session['user']['email']
    google_id = session['user'].get('sub')

    if request.method == 'POST':
        tourist_id = "TID-" + str(uuid.uuid4())[:8]
        qr_path = generate_qr(tourist_id)

        user = User(
            google_id=google_id,
            name=request.form['name'],
            adhaar=request.form['adhaar'],
            dob=request.form['dob'],
            gender=request.form['gender'],
            mobile=request.form['mobile'],
            username=request.form['username'],
            password=request.form['password'],
            gmail=gmail,
            tourist_id=tourist_id,
            qr_code=qr_path
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template("form.html", gmail=gmail)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))

    google_id = session['user'].get('sub')
    user = User.query.filter_by(google_id=google_id).first()
    return render_template("dashboard.html", name=user.name, user=user)

# ----------------- Update Location -----------------
@app.route('/update_location', methods=['POST'])
def update_location():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    data = request.get_json(force=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "Latitude or longitude missing"}), 400

    google_id = session['user'].get('sub')
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    user.latitude = lat
    user.longitude = lng

    # Example safety score adjustment
    HIGH_RISK_ZONE = [(26.2, 91.7)]  # example coordinates
    for zone_lat, zone_lng in HIGH_RISK_ZONE:
        if abs(lat - zone_lat) < 0.01 and abs(lng - zone_lng) < 0.01:
            user.safety_score = max(0, user.safety_score - 20)

    db.session.commit()
    return jsonify({"status": "success", "safety_score": user.safety_score})

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
