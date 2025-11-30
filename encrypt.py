from werkzeug.security import generate_password_hash
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="user_data",
    user="postgres",
    password="123"
)
cur = conn.cursor()

admin_username = "admin"
admin_password = "sharebyte@2025"  # default password
hashed_password = generate_password_hash(admin_password)

cur.execute(
    "INSERT INTO user_data (username, password, role) VALUES (%s, %s, %s)",
    (admin_username, hashed_password, "Admin")
)
conn.commit()
cur.close()
conn.close()

print("Admin created successfully!")
