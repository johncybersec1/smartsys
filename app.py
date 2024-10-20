from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_sqlalchemy import SQLAlchemy
import datetime
import pandas as pd

app = Flask(__name__)

app.secret_key = os.urandom(24) 

#Use pyMysSQL ofr the MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['db_config']
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'students'  # This matches the table name in your MySQL database

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hash password will be stored
    phone = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())  # Auto timestamp for user creation
    def __repr__(self):
        return f'<User {self.first_name}>'
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        gender = request.form['gender']
        date_of_birth = request.form['date_of_birth']
        address = request.form['address']
        city = request.form['city']
        country = request.form['country']

        # Hash the password before storing it in the database
        hashed_password = generate_password_hash(password)

        # Create a new user object
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            phone=phone,
            gender=gender,
            date_of_birth=date_of_birth,
            address=address,
            city=city,
            country=country
        )
        # Add the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Retrieve the user from the database based on the email
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            #successful login
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('stddashboard'))
        else:
            flash('Login failed. Please check your credentials.', 'danger')
    return render_template('login.html')


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

#COMPUTER SCIENCE semester V academic year 2024/2025
@app.route('/stddashboard')
def stddashboard():
    # Load the timetable from the Excel file
    df = pd.read_excel('schedule.xlsx')

    # Filter out rows with 'DAY' and 'GROUP' in the 'Computer Science sem' column
    df_filtered = df[~df['COMPUTER SCIENCE semester V academic year 2024/2025'].isin(['DAY', 'GROUP', 'Exams: Data security management', 'HOUR'])]

    # Extract the required columns
    time_slots = df_filtered['COMPUTER SCIENCE semester V academic year 2024/2025']
    monday_schedule = df_filtered['Unnamed: 1']
    tuesday_schedule = df_filtered['Unnamed: 2']
    wednesday_schedule = df_filtered['Unnamed: 3']
    thursday_schedule = df_filtered['Unnamed: 4']
    friday_schedule = df_filtered['Unnamed: 5']

    # Create the timetable DataFrame
    timetable = pd.DataFrame({
        'Time': time_slots,
        'Monday': monday_schedule,
        'Tuesday': tuesday_schedule,
        'Wednesday': wednesday_schedule,
        'Thursday': thursday_schedule,
        'Friday': friday_schedule
    })

    # Replace NaN values with 'No class'
    timetable.fillna(' - ', inplace=True)

    # Replace \n characters with <br> for HTML line breaks
    timetable = timetable.applymap(lambda x: x.replace('\n', '<br>') if isinstance(x, str) else x)

    # Convert the timetable to HTML with Bootstrap classes for styling
    timetable_html = timetable.to_html(classes='table table-bordered table-striped text-center', index=False, escape=False)

    # Render the dashboard template, passing the timetable
    return render_template('stddashboard.html', timetable_html=timetable_html)



#logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.debug = True
    app.run()