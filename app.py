from flask import Flask,render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ['app_key']#sessionn management

#database connection function
def get_db_connection():
    db_config = {
        os.environ['db_config_dict']
    }
    return mysql.connector.connect(db_config)
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

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == "POST":
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

        #hash password for security
        hashed_password = generate_password_hash(password, method='sha256')
        #connect to database
        connection = get_db_connection()
        cursor = connection.cursor()
        #insert user data into students database
        query = """
        INSERT INTO students (first_name, last_name, email, password, phone, gender, date_of_birth, address, city, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (first_name, last_name, email, hashed_password, phone, gender, date_of_birth, address, city, country))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template("register.html")
        
@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        #connect to database
        connection = get_db_connection()
        cursor = connection.cursor(dictionary = True)
        #Fetch user byt email
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
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
  app.run(host= '0.0.0.0', debug=True)