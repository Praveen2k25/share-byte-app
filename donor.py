import psycopg2
from datetime import datetime

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="user_data",
    user="postgres",
    password="123"
)
cur = conn.cursor()


# -------------------------------------------------
# Create a food listing
# -------------------------------------------------
def create_listing(donor_id, title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path=None):
    cur.execute("""
        INSERT INTO donor_listings 
        (donor_id, title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        donor_id, title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path, datetime.now()
    ))
    conn.commit()
    listing_id = cur.fetchone()[0]
    return listing_id


# -------------------------------------------------
# Fetch all listings of a donor
# -------------------------------------------------
def get_my_listings(donor_id):
    cur.execute("""
        SELECT id, title, description, quantity, food_type, cooked_status, pickup_location, pickup_time, image_path, created_at
        FROM donor_listings
        WHERE donor_id=%s
        ORDER BY created_at DESC
    """, (donor_id,))
    return cur.fetchall()


# -------------------------------------------------
# Fetch claims for donor's listings
# -------------------------------------------------
def get_claims_for_donor(donor_id):
    cur.execute("""
        SELECT c.id, c.listing_id, c.requester_name, c.requester_contact, c.status, c.created_at, l.title
        FROM donor_claims c
        JOIN donor_listings l ON c.listing_id = l.id
        WHERE l.donor_id = %s
        ORDER BY c.created_at DESC
    """, (donor_id,))
    return cur.fetchall()


# -------------------------------------------------
# Update claim status (Accept / Reject)
# -------------------------------------------------
def update_claim_status(claim_id, status):
    cur.execute("UPDATE donor_claims SET status=%s WHERE id=%s", (status, claim_id))
    conn.commit()


# -------------------------------------------------
# Fetch notifications for donor
# -------------------------------------------------
def get_notifications(donor_id):
    cur.execute("""
        SELECT id, message, is_read, created_at
        FROM donor_notifications
        WHERE donor_id=%s
        ORDER BY created_at DESC
    """, (donor_id,))
    return cur.fetchall()


# -------------------------------------------------
# Mark notification as read
# -------------------------------------------------
def mark_notification_read(notification_id):
    cur.execute("UPDATE donor_notifications SET is_read=TRUE WHERE id=%s", (notification_id,))
    conn.commit()


# -------------------------------------------------
# Update donor profile
# -------------------------------------------------
def update_profile(donor_id, full_name=None, address=None, document_path=None):
    # Check if profile exists
    cur.execute("SELECT id FROM donor_profiles WHERE donor_id=%s", (donor_id,))
    profile = cur.fetchone()
    if profile:
        cur.execute("""
            UPDATE donor_profiles
            SET full_name=%s, address=%s, document_path=%s, updated_at=%s
            WHERE donor_id=%s
        """, (full_name, address, document_path, datetime.now(), donor_id))
    else:
        cur.execute("""
            INSERT INTO donor_profiles (donor_id, full_name, address, document_path, updated_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (donor_id, full_name, address, document_path, datetime.now()))
    conn.commit()
def get_user_id(username):
    cur.execute("SELECT id FROM user_data WHERE username=%s", (username,))
    result = cur.fetchone()
    if result:
        return result[0]
    return None