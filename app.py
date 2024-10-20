from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_sqlalchemy import SQLAlchemy
import datetime
import pandas as pd
from flask_socketio import SocketIO, emit, join_room, leave_room
app = Flask(__name__)

app.secret_key = os.urandom(24) 
socketio = SocketIO(app)

# Use pyMysSQL for the MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['db_config']
db = SQLAlchemy(app)

class Message(db.Model):  # Corrected to db.Model
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    content = db.Column(db.String(600), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Message from {self.sender_id} to {self.receiver_id}>"

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']

    # Save the message to the database
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    room = f"room_{sender_id}_{receiver_id}"
    emit('receive_message', {'sender_id': sender_id, 'content': content, 'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, room=room)
    # Also emit the message to the opposite room (if both users are in the chat)
    room_reverse = f"room_{receiver_id}_{sender_id}"
    emit('receive_message', {
        'sender_id': sender_id,
        'content': content,
        'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }, room=room_reverse)


@socketio.on('join_room')
def join_room(data):
    room = f"room_{data['sender_id']}_{data['receiver_id']}"
    join_room(room)
    emit('room_joined', {'room': room}, room=room)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

    sender_id = session['user_id']
    receiver_id = request.form['receiver_id']  # Get the receiver_id from the form
    content = request.form['content']  # Get the message content from the form

    # Create the message object and save to the database
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    flash('Message sent!', 'success')
    return redirect(url_for('inbox', receiver_id=receiver_id))

@app.route('/inbox/<int:receiver_id>', methods=['GET', 'POST'])
def inbox(receiver_id):
    if 'user_id' not in session:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    receiver = User.query.filter_by(id=receiver_id).first()

    # Fetch messages between the current user and the selected receiver
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == user_id))
    ).order_by(Message.timestamp.asc()).all()

    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            'id': message.id,
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })

    return render_template('inbox.html', messages=formatted_messages, receiver = receiver, receiver_id=receiver_id)

@app.route('/inbox', methods=['GET'])
def inbox_list():
    if 'user_id' not in session:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch all unique users the current user has chatted with
    unique_receivers = db.session.query(Message.receiver_id).filter(Message.sender_id == user_id).distinct()
    unique_senders = db.session.query(Message.sender_id).filter(Message.receiver_id == user_id).distinct()

    all_user_ids = unique_receivers.union(unique_senders).all()

    # Fetch User objects for the unique IDs
    unique_users = User.query.filter(User.id.in_([uid[0] for uid in all_user_ids])).all()

    return render_template('inbox_list.html', users=unique_users)


@app.route('/contact')
def contact():
    if 'user_id' not in session:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Fetch all users except the current one
    users = User.query.filter(User.id != user_id).all()

    return render_template('contact.html', users=users)



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
    profile_photo = db.Column(db.String(200))

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
        profile_photo = request.form['profile_photo']

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
            country=country,
            profile_photo=profile_photo
        )

        # Add the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
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
            # Successful login
            session['user_id'] = user.id
            session['first_name'] = user.first_name
            session['last_name'] = user.last_name
            session['email'] = user.email
            session['phone'] = user.phone
            session['profile_photo'] = user.profile_photo
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

# COMPUTER SCIENCE semester V academic year 2024/2025
@app.route('/stddashboard', methods=['GET', 'POST'])
def stddashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Retrieve the current user from the database
    user = User.query.get(user_id)

    # Fetch all messages received by the user
    received_messages = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()

    users = User.query.filter(User.id != user_id).all()
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
    return render_template('stddashboard.html', user = user, timetable_html=timetable_html, received_messages=received_messages, users=users)

@app.route('/reply_message/<int:message_id>', methods=['POST'])
def reply_message(message_id):
    if 'user_id' not in session:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

    sender_id = session['user_id']
    message = Message.query.get(message_id)

    if message:
        # Create a reply message
        reply_content = request.form['reply_content']
        reply_message = Message(sender_id=sender_id, receiver_id=message.sender_id, content=reply_content)

        db.session.add(reply_message)
        db.session.commit()
        flash('Reply sent!', 'success')
    else:
        flash('Message not found.', 'danger')

    return redirect(url_for('inbox', receiver_id=message.sender_id'))
#logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.debug = True
    app.run()
