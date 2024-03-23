import bcrypt
import re
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Function to send email notification
def send_email_notification(user_email, service_type, timing, date):
    sender_email = 'your_email@gmail.com'  # Your Gmail address
    sender_password = 'your_password'  # Your Gmail password

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = user_email
    message['Subject'] = 'Room Service Request Accepted'
    message.attach(MIMEText(f'Your room service request for {service_type} at {timing} on {date} has been accepted.', 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(message)

# Database initialization and connection
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            admin_id TEXT,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_service (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            hotel_name TEXT,
            room_number TEXT,
            student_id TEXT,
            email TEXT,
            service_type TEXT,
            timing TEXT,
            date TEXT,
            accepted INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Route for home page
@app.route('/')
def index():
    return redirect(url_for('welcome'))

# Route for welcome page
@app.route('/welcome')
def welcome():
    user = None
    if 'user_id' in session:
        user_id = session['user_id']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
    return render_template('welcome.html', user=user)

# Route for user sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = 'Invalid email address.'
        else:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                error = 'Email address is already in use.'
            else:
                hashed_password = generate_hashed_password(password)
                cursor.execute("INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)", (first_name, last_name, email, hashed_password))
                conn.commit()
                conn.close()
                flash('Signup successful. Please login.', 'success')
                return redirect(url_for('login'))

    return render_template('signup.html', error=error)

# Function to securely hash the password using bcrypt
def generate_hashed_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()  # Decode the bytes to string before storing

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    # Clear admin session if already logged in
    if 'admin_id' in session:
        session.pop('admin_id')
        flash('You have been logged out of your admin account.', 'info')

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user[4].encode()):
            session['user_id'] = user[0]
            session['user_email'] = user[3]
            return redirect(url_for('user_dashboard'))
        else:
            error = 'Invalid email or password. Please try again.'

    return render_template('login.html', error=error)

# User Dashboard Page
@app.route('/user_dashboard')
def user_dashboard():
    user_id = session.get('user_id')

    # Clear admin session if already logged in
    if 'admin_id' in session:
        session.pop('admin_id')
        flash('You have been logged out of your admin account.', 'info')

    if user_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
        user_info = cursor.fetchone()
        cursor.execute("SELECT * FROM room_service WHERE user_id = ?", (user_id,))
        user_requests = cursor.fetchall()
        conn.close()
        return render_template('user_dashboard.html', user_info=user_info, user_requests=user_requests)
    else:
        return redirect(url_for('login'))

# Room Service Page
@app.route('/room_service', methods=['GET', 'POST'])
def room_service():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
                user_id = session.get('user_id')
                if user_id:
                    hotel_name = request.form['hotel_name']
                    room_number = request.form['room_number']
                    student_id = request.form['student_id']
                    email = request.form['email']
                    service_type = request.form['service_type']
                    timing = request.form['timing']
                    date = request.form['date']
                    conn = sqlite3.connect('database.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO room_service (user_id, hotel_name, room_number, student_id, email, service_type, timing, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (user_id, hotel_name, room_number, student_id, email, service_type, timing, date))
                    conn.commit()
                    conn.close()
                    flash('Your room service request has been submitted successfully!', 'success')
                    return redirect(url_for('user_dashboard'))

    return render_template('room_service.html')

# Admin Login Page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    error = None

    # Clear user session if already logged in
    if 'user_id' in session:
        session.pop('user_id')
        flash('You have been logged out of your user account.', 'info')

    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE admin_id = ? AND password = ?", (admin_id, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin_id'] = admin[0]
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid admin ID or password. Please try again.'

    return render_template('admin_login.html', error=error)

# Admin Dashboard Page
@app.route('/admin_dashboard')
def admin_dashboard():
    admin_id = session.get('admin_id')
    if admin_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM room_service")
        requests = cursor.fetchall()
        conn.close()
        return render_template('admin_dashboard.html', requests=requests)
    else:
        return redirect(url_for('admin_login'))

# Accept Room Service Request
@app.route('/accept/<int:request_id>')
def accept_request(request_id):
    admin_id = session.get('admin_id')
    if admin_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE room_service SET accepted = 1 WHERE id = ?", (request_id,))
        cursor.execute("SELECT email, service_type, timing, date FROM room_service WHERE id = ?", (request_id,))
        result = cursor.fetchone()
        if result:
            user_email, service_type, timing, date = result
            send_email_notification(user_email, service_type, timing, date)
        conn.commit()
        conn.close()
        flash('Room service request accepted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('admin_login'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')

    # Create a response object
    response = make_response(redirect(url_for('login')))

    # Add headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response  # Return the response object

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
