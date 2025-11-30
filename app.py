from flask import Flask, request, redirect, render_template, session, url_for, flash
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# File upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# PostgreSQL connection using .env variables
# Connection
conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

cur = conn.cursor()


# -------------------------------
# HELPER FUNCTION
# -------------------------------
def get_session_user_id():
    """Return logged-in user's ID from session"""
    return session.get('user_id')


# -------------------------------
# SIGNUP
# -------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_pw = generate_password_hash(password)

        try:
            cur.execute(
                "INSERT INTO user_data (username, password, role) VALUES (%s, %s, %s) RETURNING id",
                (username, hashed_pw, role)
            )
            user_id = cur.fetchone()[0]
            conn.commit()

            # Store in session
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role

            # Redirect based on role
            if role == "Donor":
                return redirect('/donor')
            elif role == "Recipient":
                return redirect('/recipient')
            elif role == "NGO":
                return redirect('/ngo')
            elif role == "Volunteer":
                return redirect('/volunteer')
            else:
                return redirect('/landing')

        except Exception as e:
            conn.rollback()
            if "duplicate key" in str(e):
                error = "Username already exists!"
            else:
                error = str(e)

    return render_template('signup.html', error=error)


# -------------------------------
# LOGIN
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur.execute("SELECT id, password, role FROM user_data WHERE username=%s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[2]

            # Redirect based on role
            if user[2] == "Donor":
                return redirect('/donor')
            elif user[2] == "Recipient":
                return redirect('/recipient')
            elif user[2] == "NGO":
                return redirect('/ngo')
            elif user[2] == "Volunteer":
                return redirect('/volunteer')
            elif user[2] == "Admin":
                return redirect('/admin')
            else:
                return redirect('/landing')
        else:
            error = "Invalid username or password!"

    return render_template('login.html', error=error)


# -------------------------------
# LANDING PAGE
# -------------------------------
@app.route('/landing')
def landing():
    if 'username' not in session:
        return redirect('/login')

    role = session.get('role')
    if role == "Donor":
        return redirect('/donor')
    elif role == "Recipient":
        return redirect('/recipient')
    elif role == "NGO":
        return redirect('/ngo')
    elif role == "Volunteer":
        return redirect('/volunteer')
    elif role == "Admin":
        return redirect('/admin')

    return render_template('landing.html', username=session['username'], role=role)


# -------------------------------
# LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# -------------------------------
# DONOR ROUTES
# -------------------------------
@app.route('/donor')
def donor_dashboard():
    if 'role' not in session or session['role'] != 'Donor':
        return redirect('/login')
    return render_template('donor.html', username=session['username'])

@app.route('/donor/profile', methods=['GET', 'POST'])
def donor_profile():
    if 'role' not in session or session['role'] != 'Donor':
        return redirect('/login')
    user_id = get_session_user_id()

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        document_file = request.files.get('document_file')
        document_path = None
        if document_file and document_file.filename != '':
            filename = secure_filename(document_file.filename)
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            document_file.save(document_path)

        cur.execute("SELECT id FROM donor_profiles WHERE donor_id=%s", (user_id,))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE donor_profiles
                SET full_name=%s, address=%s, document_path=%s, updated_at=%s
                WHERE donor_id=%s
            """, (full_name, address, document_path, datetime.now(), user_id))
        else:
            cur.execute("""
                INSERT INTO donor_profiles (donor_id, full_name, address, document_path)
                VALUES (%s,%s,%s,%s)
            """, (user_id, full_name, address, document_path))
        conn.commit()
        flash("Profile updated successfully!")
        return redirect('/donor/profile')

    cur.execute("SELECT * FROM donor_profiles WHERE donor_id=%s", (user_id,))
    profile = cur.fetchone()
    return render_template('donor_profile.html', profile=profile)


# -------------------------------
# RECIPIENT ROUTES
# -------------------------------
@app.route('/recipient')
def recipient_dashboard():
    if 'role' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    return render_template('recipient.html', username=session['username'])

@app.route('/recipient/profile', methods=['GET', 'POST'])
def recipient_profile():
    if 'role' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    user_id = get_session_user_id()

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        phone = request.form['phone']

        cur.execute("SELECT id FROM recipient_profiles WHERE recipient_id=%s", (user_id,))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE recipient_profiles
                SET full_name=%s, address=%s, phone=%s, updated_at=NOW()
                WHERE recipient_id=%s
            """, (full_name, address, phone, user_id))
        else:
            cur.execute("""
                INSERT INTO recipient_profiles (recipient_id, full_name, address, phone)
                VALUES (%s,%s,%s,%s)
            """, (user_id, full_name, address, phone))
        conn.commit()
        flash("Profile updated successfully!")
        return redirect('/recipient/profile')

    cur.execute("SELECT * FROM recipient_profiles WHERE recipient_id=%s", (user_id,))
    profile = cur.fetchone()
    return render_template('recipient_profile.html', profile=profile)


# -------------------------------
# NGO ROUTES
# -------------------------------
@app.route('/ngo')
def ngo_dashboard():
    if 'role' not in session or session['role'] != 'NGO':
        return redirect('/login')
    return render_template('ngo.html', username=session['username'])

@app.route('/ngo/profile', methods=['GET', 'POST'])
def ngo_profile():
    if 'role' not in session or session['role'] != 'NGO':
        return redirect('/login')
    user_id = get_session_user_id()

    if request.method == 'POST':
        ngo_name = request.form['ngo_name']
        address = request.form['address']
        contact_email = request.form['contact_email']
        phone = request.form['phone']
        registration_document = request.form['registration_document']

        cur.execute("SELECT id FROM ngo_profiles WHERE ngo_id=%s", (user_id,))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE ngo_profiles
                SET ngo_name=%s, address=%s, contact_email=%s, phone=%s, registration_document=%s, updated_at=NOW()
                WHERE ngo_id=%s
            """, (ngo_name, address, contact_email, phone, registration_document, user_id))
        else:
            cur.execute("""
                INSERT INTO ngo_profiles (ngo_id, ngo_name, address, contact_email, phone, registration_document)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (user_id, ngo_name, address, contact_email, phone, registration_document))
        conn.commit()
        flash("Profile updated successfully!")
        return redirect('/ngo/profile')

    cur.execute("SELECT * FROM ngo_profiles WHERE ngo_id=%s", (user_id,))
    profile = cur.fetchone()
    return render_template('ngo_profile.html', profile=profile)


# -------------------------------
# VOLUNTEER ROUTES
# -------------------------------
@app.route('/volunteer')
def volunteer_dashboard():
    if 'role' not in session or session['role'] != 'Volunteer':
        return redirect('/login')
    return render_template('volunteer.html', username=session['username'])


# -------------------------------
# DEFAULT ROUTE
# -------------------------------
@app.route('/')
def home():
    if 'username' not in session:
        return redirect('/login')
    return redirect('/landing')


# -------------------------------
# RUN APP
# -------------------------------
if __name__ == '__main__':
    app.run(debug=False)
