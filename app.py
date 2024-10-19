from flask import Flask, render_template, request, redirect, url_for, flash, session
import stddb
from werkzeug.security import generate_password_hash, check_password_hash
import os
app = Flask(__name__)
app.secret_key = os.urandom(24) 

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        # Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        date_of_birth = request.form.get('date_of_birth')
        address = request.form.get('address')
        city = request.form.get('city')
        country = request.form.get('country')

        # Hash password for security
        hashed_password = generate_password_hash(password, method='sha256')

        # Connect to database within the application context
        with app.app_context():
            # Call your db function
            cursor = stddb.connection.cursor()

            # Insert user data into students database
            query = """
            INSERT INTO students (first_name, last_name, email, password, phone, gender, date_of_birth, address, city, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            try:
                cursor.execute(query, (first_name, last_name, email, hashed_password, phone, gender, date_of_birth, address, city, country))
                stddb.connection.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                stddb.connection.rollback()  # Rollback on error
                flash('Registration failed. Please try again.', 'danger')
                print(e)  # Log the error (you might want to implement a proper logging mechanism)
            finally:
                cursor.close()
                stddb.connection.close()

    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Connect to database within the application context
        with app.app_context():
            cursor = stddb.connection.cursor(dictionary=True)

            # Fetch user by email
            cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
            user = cursor.fetchone()

            cursor.close()
            stddb.connection.close()

        if user and check_password_hash(user['password'], password):
            session["user_id"] = user['id']
            session["first_name"] = user['first_name']
            flash("Login successful!", "success")
            return redirect(url_for('stddashboard'))
        else:
            flash("Login failed. Please check your email and password.", "danger")

    return render_template("login.html")

@app.route('/stddashboard')
def stddashboard():
    return render_template("stddashboard.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
