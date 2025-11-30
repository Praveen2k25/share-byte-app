from flask import Flask, request, redirect, render_template, session, url_for, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'b>\x8b\x1e\xe9O*\x8b\xbf\r\x0f\xd0\x8e\xe9\x8f\x17h\x9b\xc2\x885\xba\x86\xccJ'

# File upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="user_data",
    user="postgres",
    password="123"
)
cur = conn.cursor()

# -------------------------------
# CREATE NECESSARY TABLES
# -------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS user_data (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS donor_listings (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    quantity VARCHAR(100) NOT NULL,
    food_type VARCHAR(50) NOT NULL,
    cooked_status VARCHAR(20) NOT NULL,
    pickup_location VARCHAR(200) NOT NULL,
    pickup_time TIMESTAMP NOT NULL,
    image_path VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS donor_claims (
    id SERIAL PRIMARY KEY,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    requester_name VARCHAR(100) NOT NULL,
    requester_contact VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS donor_notifications (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS donor_profiles (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    address TEXT,
    document_path VARCHAR(200),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

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
                "INSERT INTO user_data (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_pw, role)
            )
            conn.commit()

            # Get the inserted user's ID
            cur.execute("SELECT id FROM user_data WHERE username=%s", (username,))
            user_id = cur.fetchone()[0]

            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role

            # Redirect based on role
            if role == "Donor":
                return redirect('/donor')
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
            else:
                return redirect('/landing')
        else:
            error = "Invalid username or password!"

    return render_template('login.html', error=error)


# -------------------------------
# LANDING PAGE (other roles)
# -------------------------------
@app.route('/landing')
def landing():
    if 'username' not in session:
        return redirect('/login')
    if session['role'] == "Donor":
        return redirect('/donor')
    elif session['role'] == "Recipient":
        return redirect('/recipient')
    elif session['role'] == "NGO":
        return redirect('/ngo')
    elif session['role'] == "Volunteer":
        return redirect('/volunteer')
    elif session['role'] == "Admin":
        return redirect('/admin')
    return render_template('landing.html', username=session['username'], role=session['role'])
#admin


# ------------------- Admin Routes -------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = conn.cursor()
        cur.execute("SELECT password FROM user_data WHERE username=%s AND role='Admin'", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user[0], password):
            session['username'] = username
            session['role'] = 'Admin'
            return redirect('/admin')
        else:
            error = "Invalid admin credentials!"

    return render_template('admin_login.html', error=error)


@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    return render_template('admin_dashboard.html', username=session['username'])


# ------------------- User Approvals -------------------

@app.route('/admin/users')
def admin_users():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, approved FROM user_approvals")
    users = cur.fetchall()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/approve/<int:user_id>')
def approve_user(user_id):
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("UPDATE user_approvals SET approved = TRUE, approved_at = NOW() WHERE id=%s", (user_id,))
    conn.commit()
    return redirect('/admin/users')


# ------------------- Listings Monitoring -------------------

@app.route('/admin/listings')
def admin_listings():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, u.username AS donor_name, l.food_type, l.quantity, l.expiry_date
        FROM donor_listings l
        JOIN user_data u ON l.donor_id = u.id
    """)
    listings = cur.fetchall()
    return render_template('admin_listings.html', listings=listings)


@app.route('/admin/listings/remove/<int:listing_id>')
def remove_listing(listing_id):
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("DELETE FROM donor_listings WHERE id=%s", (listing_id,))
    conn.commit()
    return redirect('/admin/listings')


# ------------------- Claims Monitoring -------------------

@app.route('/admin/claims')
def admin_claims():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, u.username AS user_name, l.food_type AS listing_name, c.status
        FROM claims c
        JOIN user_data u ON c.user_id = u.id
        JOIN donor_listings l ON c.listing_id = l.id
    """)
    claims = cur.fetchall()
    return render_template('admin_claims.html', claims=claims)


@app.route('/admin/claims/approve/<int:claim_id>')
def approve_claim(claim_id):
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("UPDATE claims SET status='Approved' WHERE id=%s", (claim_id,))
    conn.commit()
    return redirect('/admin/claims')


# ------------------- Chat Moderation -------------------

@app.route('/admin/chat')
def admin_chat():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("SELECT id, sender_id, receiver_id, message FROM chats")
    chats_raw = cur.fetchall()
    chats = []
    for c in chats_raw:
        # fetch sender and receiver names
        cur.execute("SELECT username FROM user_data WHERE id=%s", (c[1],))
        sender = cur.fetchone()[0]
        cur.execute("SELECT username FROM user_data WHERE id=%s", (c[2],))
        receiver = cur.fetchone()[0]
        chats.append({'id': c[0], 'sender': sender, 'receiver': receiver, 'message': c[3]})
    
    return render_template('admin_chat.html', chats=chats)


@app.route('/admin/chat/report/<int:chat_id>')
def report_chat(chat_id):
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    # For simplicity, we just delete the chat. You can extend to store reports.
    cur = conn.cursor()
    cur.execute("DELETE FROM chats WHERE id=%s", (chat_id,))
    conn.commit()
    return redirect('/admin/chat')


# ------------------- Notifications -------------------

@app.route('/admin/notifications', methods=['GET', 'POST'])
def admin_notifications():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    if request.method == 'POST':
        message = request.form['message']
        cur = conn.cursor()
        cur.execute("INSERT INTO admin_notifications (message) VALUES (%s)", (message,))
        conn.commit()
        return redirect('/admin/notifications')
    
    return render_template('admin_notifications.html')


# ------------------- Analytics -------------------

@app.route('/admin/analytics')
def admin_analytics():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect('/admin/login')
    
    cur = conn.cursor()
    cur.execute("SELECT SUM(quantity) FROM donor_listings")
    total_food = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM claims WHERE status='Approved'")
    meals_saved = cur.fetchone()[0] or 0

    analytics = {
        'total_food_donated': total_food,
        'meals_saved': meals_saved
    }

    return render_template('admin_analytics.html', analytics=analytics)


# ------------------- Admin Logout -------------------

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')



#Volunteer 


# ------------------- Volunteer Routes & Functions -------------------

# Volunteer Dashboard
@app.route('/volunteer')
def volunteer_dashboard():
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')
    return render_template('volunteer.html', username=session['username'], role=session['role'])


# Volunteer Tasks List
@app.route('/volunteer/tasks')
def volunteer_tasks():
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')

    cur = conn.cursor()
    cur.execute("""
        SELECT vt.id, u.username as donor_name, u2.username as ngo_name, vt.task_description, vt.status
        FROM volunteer_tasks vt
        JOIN user_data u ON vt.donor_id = u.id
        JOIN user_data u2 ON vt.ngo_id = u2.id
        WHERE vt.volunteer_id = %s
    """, (session_user_id(),))
    tasks = cur.fetchall()

    tasks_list = []
    for t in tasks:
        tasks_list.append({
            'id': t[0],
            'donor_name': t[1],
            'ngo_name': t[2],
            'task_description': t[3],
            'status': t[4]
        })

    return render_template('volunteer_tasks.html', tasks=tasks_list)


# Volunteer Accept Task
@app.route('/volunteer/task/<int:task_id>/accept')
def volunteer_accept_task(task_id):
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')
    cur = conn.cursor()
    cur.execute("UPDATE volunteer_tasks SET status='Accepted', updated_at=NOW() WHERE id=%s AND volunteer_id=%s",
                (task_id, session_user_id()))
    conn.commit()
    return redirect('/volunteer/tasks')


# Volunteer Reject Task
@app.route('/volunteer/task/<int:task_id>/reject')
def volunteer_reject_task(task_id):
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')
    cur = conn.cursor()
    cur.execute("UPDATE volunteer_tasks SET status='Rejected', updated_at=NOW() WHERE id=%s AND volunteer_id=%s",
                (task_id, session_user_id()))
    conn.commit()
    return redirect('/volunteer/tasks')


# Volunteer Update Task Status
@app.route('/volunteer/task/<int:task_id>/update', methods=['GET', 'POST'])
def volunteer_update_task(task_id):
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')

    if request.method == 'POST':
        status = request.form['status']
        cur = conn.cursor()
        cur.execute("UPDATE volunteer_tasks SET status=%s, updated_at=NOW() WHERE id=%s AND volunteer_id=%s",
                    (status, task_id, session_user_id()))
        conn.commit()
        return redirect('/volunteer/tasks')

    return render_template('volunteer_update_task.html', task_id=task_id)


# Volunteer Profile
@app.route('/volunteer/profile', methods=['GET', 'POST'])
def volunteer_profile():
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')
    
    cur = conn.cursor()
    user_id = session_user_id()
    if request.method == 'POST':
        full_name = request.form['full_name']
        contact_email = request.form['contact_email']
        phone = request.form['phone']
        address = request.form['address']

        # Check if profile exists
        cur.execute("SELECT id FROM volunteer_profiles WHERE volunteer_id=%s", (user_id,))
        exists = cur.fetchone()
        if exists:
            cur.execute("""
                UPDATE volunteer_profiles SET full_name=%s, contact_email=%s, phone=%s, address=%s, updated_at=NOW()
                WHERE volunteer_id=%s
            """, (full_name, contact_email, phone, address, user_id))
        else:
            cur.execute("""
                INSERT INTO volunteer_profiles (volunteer_id, full_name, contact_email, phone, address)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, full_name, contact_email, phone, address))
        conn.commit()

    cur.execute("SELECT * FROM volunteer_profiles WHERE volunteer_id=%s", (user_id,))
    profile = cur.fetchone()
    profile_dict = None
    if profile:
        profile_dict = {
            'full_name': profile[2],
            'contact_email': profile[3],
            'phone': profile[4],
            'address': profile[5]
        }
    return render_template('volunteer_profile.html', profile=profile_dict)


# Volunteer Notifications
@app.route('/volunteer/notifications')
def volunteer_notifications():
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')

    cur = conn.cursor()
    cur.execute("SELECT message, is_read, created_at FROM volunteer_notifications WHERE volunteer_id=%s ORDER BY created_at DESC",
                (session_user_id(),))
    notifications = [{'message': n[0], 'is_read': n[1], 'created_at': n[2]} for n in cur.fetchall()]

    return render_template('volunteer_notifications.html', notifications=notifications)


# Volunteer Chat
@app.route('/volunteer/chat', methods=['GET', 'POST'])
def volunteer_chat():
    if 'username' not in session or session['role'] != 'Volunteer':
        return redirect('/login')

    messages = []
    if request.method == 'POST':
        msg_text = request.form['message']
        # Here you can implement message storing logic
        messages.append({'sender': session['username'], 'text': msg_text})

    return render_template('volunteer_chat.html', messages=messages)


# ------------------- Utility Function -------------------
def session_user_id():
    """Helper to get the logged-in user's ID from user_data table"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM user_data WHERE username=%s", (session['username'],))
    user_id = cur.fetchone()
    return user_id[0] if user_id else None

# -------------------------------
# DONOR DASHBOARD
# -------------------------------
@app.route('/donor')
def donor_dashboard():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    return render_template('donor.html', username=session['username'])


# -------------------------------
# CREATE FOOD LISTING
# -------------------------------
@app.route('/donor/create-listing', methods=['GET', 'POST'])
def donor_create_listing():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        quantity = request.form['quantity']
        food_type = request.form['food_type']
        cooked_status = request.form['cooked_status']
        pickup_location = request.form['pickup_location']
        pickup_time = request.form['pickup_time']
        image_file = request.files.get('image_file')
        image_path = None
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        cur.execute("""
            INSERT INTO donor_listings
            (donor_id, title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (session['user_id'], title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path))
        conn.commit()
        flash("Listing created successfully!")
        return redirect('/donor/my-listings')
    return render_template('donor_create_listing.html')


# -------------------------------
# VIEW MY LISTINGS
# -------------------------------
@app.route('/donor/my-listings')
def donor_my_listings():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    cur.execute("SELECT * FROM donor_listings WHERE donor_id=%s ORDER BY created_at DESC", (session['user_id'],))
    listings = cur.fetchall()
    return render_template('donor_my_listings.html', listings=listings)


# -------------------------------
# CLAIM REQUESTS
# -------------------------------
@app.route('/donor/claims')
def donor_claims():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    cur.execute("""
        SELECT c.id, l.title, c.requester_name, c.requester_contact, c.status 
        FROM donor_claims c 
        JOIN donor_listings l ON c.listing_id = l.id
        WHERE l.donor_id=%s ORDER BY c.created_at DESC
    """, (session['user_id'],))
    claims = cur.fetchall()
    return render_template('donor_claims.html', claims=claims)


# -------------------------------
# NOTIFICATIONS
# -------------------------------
@app.route('/donor/notifications')
def donor_notifications():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    cur.execute("SELECT * FROM donor_notifications WHERE donor_id=%s ORDER BY created_at DESC", (session['user_id'],))
    notifications = cur.fetchall()
    return render_template('donor_notifications.html', notifications=notifications)


# -------------------------------
# PROFILE
# -------------------------------
@app.route('/donor/profile', methods=['GET', 'POST'])
def donor_profile():
    if 'username' not in session or session['role'] != 'Donor':
        return redirect('/login')
    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        document_file = request.files.get('document_file')
        document_path = None
        if document_file and document_file.filename != '':
            filename = secure_filename(document_file.filename)
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            document_file.save(document_path)
        cur.execute("SELECT id FROM donor_profiles WHERE donor_id=%s", (session['user_id'],))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE donor_profiles
                SET full_name=%s, address=%s, document_path=%s, updated_at=%s
                WHERE donor_id=%s
            """, (full_name, address, document_path, datetime.now(), session['user_id']))
        else:
            cur.execute("""
                INSERT INTO donor_profiles (donor_id, full_name, address, document_path)
                VALUES (%s,%s,%s,%s)
            """, (session['user_id'], full_name, address, document_path))
        conn.commit()
        flash("Profile updated successfully!")
        return redirect('/donor/profile')
    cur.execute("SELECT * FROM donor_profiles WHERE donor_id=%s", (session['user_id'],))
    profile = cur.fetchone()
    return render_template('donor_profile.html', profile=profile)




#recipient 

# -------------------------------
# CREATE NECESSARY TABLES FOR RECIPIENT
# -------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS recipient_profiles (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    address TEXT,
    phone VARCHAR(20),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS recipient_claims (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'Pending', -- Pending, Approved, Rejected, Cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS recipient_notifications (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# -------------------------------
# RECIPIENT DASHBOARD
# -------------------------------
@app.route('/recipient')
def recipient_dashboard():
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    return render_template('recipient.html', username=session['username'])

# -------------------------------
# RECIPIENT PROFILE
# -------------------------------
@app.route('/recipient/profile', methods=['GET', 'POST'])
def recipient_profile():
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        phone = request.form['phone']

        cur.execute("SELECT id FROM recipient_profiles WHERE recipient_id=%s", (session['user_id'],))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE recipient_profiles
                SET full_name=%s, address=%s, phone=%s, updated_at=NOW()
                WHERE recipient_id=%s
            """, (full_name, address, phone, session['user_id']))
        else:
            cur.execute("""
                INSERT INTO recipient_profiles (recipient_id, full_name, address, phone)
                VALUES (%s,%s,%s,%s)
            """, (session['user_id'], full_name, address, phone))
        conn.commit()
        flash("Profile updated successfully!")
        return redirect('/recipient/profile')

    cur.execute("SELECT * FROM recipient_profiles WHERE recipient_id=%s", (session['user_id'],))
    profile = cur.fetchone()
    return render_template('recipient_profile.html', profile=profile)

# -------------------------------
# VIEW NEARBY LISTINGS
# -------------------------------
@app.route('/recipient/listings')
def recipient_listings():
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    cur.execute("SELECT * FROM donor_listings ORDER BY created_at DESC")
    listings = cur.fetchall()
    return render_template('recipient_listings.html', listings=listings)

# -------------------------------
# LISTING DETAILS AND CLAIM
# -------------------------------
@app.route('/recipient/listings/<int:listing_id>', methods=['GET', 'POST'])
def recipient_listing_detail(listing_id):
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')

    cur.execute("SELECT * FROM donor_listings WHERE id=%s", (listing_id,))
    listing = cur.fetchone()

    if request.method == 'POST':
        # Claim the listing
        cur.execute("""
            INSERT INTO recipient_claims (recipient_id, listing_id)
            VALUES (%s, %s)
        """, (session['user_id'], listing_id))
        conn.commit()
        flash("Claim submitted successfully!")
        return redirect('/recipient/claims')

    return render_template('recipient_listing_detail.html', listing=listing)

# -------------------------------
# TRACK / CANCEL CLAIMS
# -------------------------------
@app.route('/recipient/claims')
def recipient_claims():
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')

    cur.execute("""
        SELECT c.id, l.title, c.status, l.pickup_time, l.pickup_location
        FROM recipient_claims c
        JOIN donor_listings l ON c.listing_id = l.id
        WHERE c.recipient_id=%s
        ORDER BY c.created_at DESC
    """, (session['user_id'],))
    claims = cur.fetchall()
    return render_template('recipient_claims.html', claims=claims)

@app.route('/recipient/claims/cancel/<int:claim_id>')
def recipient_cancel_claim(claim_id):
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    cur.execute("UPDATE recipient_claims SET status='Cancelled' WHERE id=%s AND recipient_id=%s",
                (claim_id, session['user_id']))
    conn.commit()
    flash("Claim cancelled successfully!")
    return redirect('/recipient/claims')

# -------------------------------
# RECIPIENT NOTIFICATIONS
# -------------------------------
@app.route('/recipient/notifications')
def recipient_notifications():
    if 'username' not in session or session['role'] != 'Recipient':
        return redirect('/login')
    cur.execute("SELECT * FROM recipient_notifications WHERE recipient_id=%s ORDER BY created_at DESC", (session['user_id'],))
    notifications = cur.fetchall()
    return render_template('recipient_notifications.html', notifications=notifications)

#NGO


# NGO Profile
cur.execute("""
CREATE TABLE IF NOT EXISTS ngo_profiles (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    ngo_name VARCHAR(200),
    address TEXT,
    contact_email VARCHAR(100),
    phone VARCHAR(20),
    registration_document TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# NGO Claims (bulk)
cur.execute("""
CREATE TABLE IF NOT EXISTS ngo_claims (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    quantity_claimed INT,
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# NGO Volunteers
cur.execute("""
CREATE TABLE IF NOT EXISTS ngo_volunteers (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    volunteer_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    task_description TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'Assigned'
)
""")

# NGO Notifications
cur.execute("""
CREATE TABLE IF NOT EXISTS ngo_notifications (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
# -------------------------------
# NGO DASHBOARD
# -------------------------------
@app.route('/ngo')
def ngo_dashboard():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    return render_template('ngo.html', username=session['username'])

# -------------------------------
# NGO PROFILE
# -------------------------------
@app.route('/ngo/profile', methods=['GET', 'POST'])
def ngo_profile():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    
    if request.method == 'POST':
        ngo_name = request.form['ngo_name']
        address = request.form['address']
        contact_email = request.form['contact_email']
        phone = request.form['phone']
        registration_document = request.form['registration_document']

        cur.execute("SELECT id FROM ngo_profiles WHERE ngo_id=%s", (session['user_id'],))
        profile = cur.fetchone()
        if profile:
            cur.execute("""
                UPDATE ngo_profiles
                SET ngo_name=%s, address=%s, contact_email=%s, phone=%s, registration_document=%s, updated_at=NOW()
                WHERE ngo_id=%s
            """, (ngo_name, address, contact_email, phone, registration_document, session['user_id']))
        else:
            cur.execute("""
                INSERT INTO ngo_profiles (ngo_id, ngo_name, address, contact_email, phone, registration_document)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (session['user_id'], ngo_name, address, contact_email, phone, registration_document))
        conn.commit()
        return redirect('/ngo/profile')

    cur.execute("SELECT * FROM ngo_profiles WHERE ngo_id=%s", (session['user_id'],))
    profile = cur.fetchone()
    return render_template('ngo_profile.html', profile=profile)

# -------------------------------
# VIEW ALL DONOR LISTINGS
# -------------------------------
@app.route('/ngo/listings')
def ngo_listings():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    cur.execute("SELECT * FROM donor_listings ORDER BY created_at DESC")
    listings = cur.fetchall()
    return render_template('ngo_listings.html', listings=listings)

# -------------------------------
# CLAIM DONOR LISTING IN BULK
# -------------------------------
@app.route('/ngo/claims/<int:listing_id>', methods=['GET', 'POST'])
def ngo_claim_listing(listing_id):
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    
    cur.execute("SELECT * FROM donor_listings WHERE id=%s", (listing_id,))
    listing = cur.fetchone()

    if request.method == 'POST':
        quantity_claimed = int(request.form['quantity_claimed'])
        cur.execute("""
            INSERT INTO ngo_claims (ngo_id, listing_id, quantity_claimed)
            VALUES (%s, %s, %s)
        """, (session['user_id'], listing_id, quantity_claimed))
        conn.commit()
        return redirect('/ngo/claims')

    return render_template('ngo_claim_listing.html', listing=listing)

# -------------------------------
# TRACK NGO CLAIMS
# -------------------------------
@app.route('/ngo/claims')
def ngo_claims():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    
    cur.execute("""
        SELECT c.id, l.title, c.quantity_claimed, c.status
        FROM ngo_claims c
        JOIN donor_listings l ON c.listing_id = l.id
        WHERE c.ngo_id=%s
        ORDER BY c.created_at DESC
    """, (session['user_id'],))
    claims = cur.fetchall()
    return render_template('ngo_claims.html', claims=claims)

# -------------------------------
# VOLUNTEER ASSIGNMENT
# -------------------------------
@app.route('/ngo/volunteers', methods=['GET', 'POST'])
def ngo_volunteers():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    
    if request.method == 'POST':
        volunteer_id = int(request.form['volunteer_id'])
        task_description = request.form['task_description']
        cur.execute("""
            INSERT INTO ngo_volunteers (ngo_id, volunteer_id, task_description)
            VALUES (%s, %s, %s)
        """, (session['user_id'], volunteer_id, task_description))
        conn.commit()
        return redirect('/ngo/volunteers')

    cur.execute("SELECT * FROM ngo_volunteers WHERE ngo_id=%s ORDER BY assigned_at DESC", (session['user_id'],))
    volunteers = cur.fetchall()
    return render_template('ngo_volunteers.html', volunteers=volunteers)

# -------------------------------
# NGO NOTIFICATIONS
# -------------------------------
@app.route('/ngo/notifications')
def ngo_notifications():
    if 'username' not in session or session['role'] != 'NGO':
        return redirect('/login')
    cur.execute("SELECT * FROM ngo_notifications WHERE ngo_id=%s ORDER BY created_at DESC", (session['user_id'],))
    notifications = cur.fetchall()
    return render_template('ngo_notifications.html', notifications=notifications)

# -------------------------------
# LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# -------------------------------
# DEFAULT ROUTE
# -------------------------------
@app.route('/')
def home():
    if 'username' not in session:
        return redirect('/login')
    return redirect('/landing')


if __name__ == '__main__':
    app.run(debug=True)
