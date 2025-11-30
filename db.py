import psycopg2

# ------------------ Connect to Render PostgreSQL ------------------
conn = psycopg2.connect(
    host="dpg-d4lt50ruibrs73883ae0-a.oregon-postgres.render.com",
    database="myflaskdb_fu1b",
    user="myflaskdb_fu1b_user",
    password="M1oUb7p4ZjnQYvEQXyEGcsLjYh5gtdBn",
    port=5432
)
cur = conn.cursor()
print("Connected successfully!")

# ------------------ Create Tables ------------------
tables_sql = [

"""
CREATE TABLE IF NOT EXISTS user_data (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL
)
""",

"""
CREATE TABLE IF NOT EXISTS donor_profiles (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    address TEXT,
    document_path VARCHAR(200),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS recipient_profiles (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    address TEXT,
    phone VARCHAR(20),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
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
""",

"""
CREATE TABLE IF NOT EXISTS volunteer_profiles (
    id SERIAL PRIMARY KEY,
    volunteer_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    full_name VARCHAR(200),
    contact_email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS donor_listings (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    title VARCHAR(200),
    description TEXT,
    quantity INT,
    type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Available',
    pickup_location TEXT,
    pickup_time TIMESTAMP,
    food_type VARCHAR(100),
    cooked BOOLEAN,
    expiry_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
)
""",

"""
CREATE TABLE IF NOT EXISTS donor_claims (
    id SERIAL PRIMARY KEY,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    requester_name VARCHAR(100) NOT NULL,
    requester_contact VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS recipient_claims (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS ngo_claims (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    quantity_claimed INT,
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS volunteer_tasks (
    id SERIAL PRIMARY KEY,
    volunteer_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    listing_id INT REFERENCES donor_listings(id) ON DELETE CASCADE,
    task_description TEXT,
    status VARCHAR(20) DEFAULT 'Assigned',
    pickup_location TEXT,
    delivery_location TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    sender_id INT REFERENCES user_data(id),
    receiver_id INT REFERENCES user_data(id),
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""",

"""
CREATE TABLE IF NOT EXISTS admin_notifications (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
)
""",

"""
CREATE TABLE IF NOT EXISTS donor_notifications (
    id SERIAL PRIMARY KEY,
    donor_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS recipient_notifications (
    id SERIAL PRIMARY KEY,
    recipient_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS ngo_notifications (
    id SERIAL PRIMARY KEY,
    ngo_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS volunteer_notifications (
    id SERIAL PRIMARY KEY,
    volunteer_id INT REFERENCES user_data(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS user_approvals (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP
)
"""
]

# Execute all table creations
for sql in tables_sql:
    cur.execute(sql)

# Insert default admin
cur.execute("""
INSERT INTO user_data (username, password, role)
VALUES ('admin', 'sharebyteadmin@2025', 'Admin')
ON CONFLICT (username) DO NOTHING
""")

conn.commit()
print("All tables created successfully!")

cur.close()
conn.close()
