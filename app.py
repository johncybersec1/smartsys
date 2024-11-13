from flask import Flask, render_template, request, redirect, url_for, flash, session,send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime
from flask import jsonify
import pandas as pd
from flask_socketio import SocketIO, emit, join_room
from sqlalchemy import Enum as SQLAEnum
from enum import Enum as PyEnum
from werkzeug.utils import secure_filename
from flask import send_file
from functools import wraps


app = Flask(__name__)

app.secret_key = os.urandom(24) 
socketio = SocketIO(app)

# JWT Configuration
app.config["JWT_SECRET_KEY"] = os.urandom(24)
jwt = JWTManager(app)

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Use pyMysSQL for the MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['db_config']
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'C:/Users/mwang/Desktop/SchoolSmart_Project/smartsys/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class UserRole(PyEnum):
    student = 'student'
    teacher = 'teacher'

# Define a decorator to check if the user is a teacher
def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            if current_user.role != role:
                flash("You need to log in as a teacher to view submissions.", "danger")
                return redirect(url_for('login'))  # Redirect to login if role is not teacher
            return func(*args, **kwargs)
        return wrapped_function
    return role_required

class Message(db.Model):  # Corrected to db.Model
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    content = db.Column(db.String(600), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

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
    sender_id = data['sender_id']
    room = f"room_{sender_id}_{data['receiver_id']}"
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
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M')
        })

    users = User.query.filter(User.id != user_id).all()  # Get list of other users for the conversation list

    return render_template('inbox_list.html', messages=formatted_messages, receiver = receiver, users=users, receiver_id=receiver_id)

@app.route('/inbox', methods=['GET'])
@jwt_required
def inbox_list():
    user_id = get_jwt_identity()

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



class User(db.Model, UserMixin):
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
    role = db.Column(SQLAEnum(UserRole), default=UserRole.student, nullable=False)


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
        profile_photo = 'p1.jpg'

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

        # Check if the user is a student
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
                login_user(user) #flask-login login
                access_token = create_access_token(identity=user.id)  # JWT creation

                flash('Login successful!', 'success')

                return jsonify({
                'access_token': access_token,
                'redirect_url': url_for('stddashboard')
                })
    

        teacher = Teacher.query.filter_by(email=email).first()
        if teacher and check_password_hash(teacher.password, password):
                login_user(teacher)  # Flask-Login login
                access_token = create_access_token(identity=teacher.id) #JWT creation
               
                flash('Login successful!', 'success')

                return jsonify({
                'access_token': access_token,
                'redirect_url': url_for('teacher_dashboard')
                })

        # If login fails for both student and teacher
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
@jwt_required()  # Ensures the JWT token is valid
def stddashboard():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('login'))

    # Retrieve the current user from the database
    user = User.query.get(user_id)

    # Fetch all messages received by the user
    received_messages = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()

    # Fetch all assignments and announcements for display in the student dashboard
    assignments = Assignment.query.order_by(Assignment.due_date.asc()).all()  # Sorted by due date
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()  # Sorted by creation date

    users = User.query.filter(User.id != user_id).all()
    submissions = Submission.query.filter_by(student_id=user_id).all()
    return render_template('stddashboard.html', user=user, received_messages=received_messages, assignments = assignments, announcements=announcements, users=users, submissions = submissions)

# New route for the timetable with pagination
@app.route('/timetable')
@jwt_required()
def timetable():
    user_id = get_jwt_identity()
    if not user_id:
        flash("You need to login first!", "danger")
        return redirect(url_for('login'))

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

    # Convert the full timetable to HTML
    timetable_html = timetable.to_html(classes='table table-bordered table-striped text-center', index=False, escape=False)

    return render_template('timetable.html', timetable_html=timetable_html)

@app.route('/reply_message/<int:message_id>', methods=['POST'])
@jwt_required()
def reply_message(message_id):
    user_id = get_jwt_identity()
    message = Message.query.get(message_id)

    if message:
        # Create a reply message
        reply_content = request.form.get('reply_content')
        if not reply_content:
            flash('Reply content cannot be empty.', 'danger')
            return redirect(url_for('inbox', receiver_id=message.sender_id))
        
        from markupsafe import escape
        reply_content = escape(reply_content)
    
        reply_message = Message(sender_id=user_id, receiver_id=message.sender_id, content=reply_content)

        db.session.add(reply_message)
        db.session.commit()
        flash('Reply sent!', 'success')
    else:
        flash('Message not found.', 'danger')

    return redirect(url_for('inbox', receiver_id=message.sender_id))
#Teacher section

class Teacher(db.Model, UserMixin):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(100), unique = True, nullable = False)
    password = db.Column(db.String(200), nullable = False)
    school = db.Column(db.String(200), nullable = False)
    created_at = db.Column(db.DateTime, default = datetime.datetime.utcnow)
    role = db.Column(SQLAEnum(UserRole), default=UserRole.teacher, nullable=False)

    def __repr__(self):
        return f'<Teacher {self.name}>'

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    teacher = db.relationship('Teacher', backref='assignments')

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    teacher = db.relationship('Teacher', backref='announcements')

@app.route('/teacher/register', methods = ['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        school = request.form['school']

        new_teacher = Teacher(name = name, email = email, password = password, school = school)
        db.session.add(new_teacher)
        db.session.commit()
        flash('Teacher registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('teacher_register.html')

@app.route('/teacher/dashboard')
@login_required  # Ensures the user is logged in
def teacher_dashboard():
    teacher_id = current_user.id
    
    teacher = Teacher.query.get(teacher_id)

    if teacher is None:
        flash('Teacher not found.', 'danger')
        return redirect(url_for('teacher_login'))
    
    assignments = Assignment.query.filter_by(teacher_id=teacher_id).all()
    assignments_ids = [assignment.id for assignment in assignments]

    # Using a single query to fetch all submissions for the assignments the teacher has
    submissions = Submission.query.filter(Submission.assignment_id.in_(assignments_ids)).all()
    announcements = Announcement.query.filter_by(teacher_id=teacher_id).all()

    return render_template(
        'teacher_dashboard.html',
        teacher=teacher,
        assignments=assignments,
        announcements=announcements,
        submissions=submissions
    )
@app.route('/teacher/assignments/create', methods=['GET', 'POST'])
@login_required   # Ensures the JWT token is valid
def create_assignment():
    teacher_id = current_user.id

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = datetime.datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        
        assignment = Assignment(
            title=title, 
            description=description, 
            due_date=due_date, 
            teacher_id=teacher_id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))

    return render_template('create_assignment.html')


@app.route('/teacher/announcements/create', methods=['GET', 'POST'])
@login_required
def create_announcement():
    teacher_id = current_user.id
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        announcement = Announcement(
            title=title, 
            content=content, 
            teacher_id=teacher_id
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_announcement.html')

@app.route('/assignment/<int:assignment_id>')
@login_required
def assignment_details(assignment_id):
    # Fetch the assignment based on its ID
    assignment = Assignment.query.get(assignment_id)
    if assignment:
        return render_template('assignment_details.html', assignment=assignment)
    else:
        return "Assignment not found", 404

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()  # Flask-Login logout
    session.pop('access_token', None)  # Remove JWT token from session if stored
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))
@app.route('/all_assignments')
@login_required
def all_assignments():
    try:
        # Fetch all assignments from the database
        assignments = Assignment.query.order_by(Assignment.due_date.asc()).all()
        print(f"Assignments fetched: {[assignment.title for assignment in assignments]}")  # Debug print
        return render_template('all_assignments.html', assignments=assignments)
    except Exception as e:
        print(f"Error fetching assignments: {e}")  # Print the error to console
        return "Internal Server Error", 500

@app.route('/get-started')
def get_started():
    return render_template('get_started.html')

class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    file_url = db.Column(db.String(200), nullable=False)  # URL to the submitted file
    status = db.Column(db.String(50), default="Submitted")  # Status of the submission (e.g., Submitted, Graded)

    student = db.relationship('User', backref='submissions')
    assignment = db.relationship('Assignment', backref='submissions')

    def __repr__(self):
        return f'<Submission {self.id}, Student ID: {self.student_id}, Assignment ID: {self.assignment_id}>'

@app.route('/submit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    print("Session data at submit_assignment:", session) 
    
    # Check if the user is logged in as a student
    if 'user_id' not in session or session.get('role') != 'UserRole.student':
        flash("You need to log in as a student to submit assignments.", "danger")
        return redirect(url_for('login'))

    # Retrieve the assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        flash("Assignment not found.", "danger")
        return redirect(url_for('stddashboard'))

    if request.method == 'POST':
        file = request.files['file']

        # Validate file upload
        if file and allowed_file(file.filename):
            # Ensure the uploads folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            # Generate a unique filename based on the current timestamp to avoid conflicts
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            filename = secure_filename(file.filename)
            unique_filename = f"{timestamp}_{filename}"  # Add timestamp to filename for uniqueness

            # Define the path to save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Save the file
            file.save(file_path)

            # Save submission in the database
            submission = Submission(
                student_id=session['user_id'],
                assignment_id=assignment_id,
                file_url=unique_filename  # Store just the filename
            )
            db.session.add(submission)
            db.session.commit()

            flash("Assignment submitted successfully!", "success")
            return redirect(url_for('stddashboard'))
        else:
            flash("Invalid file type or no file uploaded. Please try again.", "danger")

    return render_template('submit_assignment.html', assignment=assignment)

def allowed_file(filename):
    allowed_extensions = {'pdf', 'docx', 'pptx', 'txt'}  # Example extensions
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

class Grade(db.Model):
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    grade = db.Column(db.String(10))  # Grade (e.g., A, B, 85%)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    submission = db.relationship('Submission', backref='grade')
    teacher = db.relationship('Teacher', backref='grades')

    def __repr__(self):
        return f'<Grade {self.id}, Submission ID: {self.submission_id}, Teacher ID: {self.teacher_id}>'

@app.route('/grade_submission/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def grade_submission(submission_id):
    if 'teacher_id' not in session:
        flash("You need to login as a teacher to grade assignments.", "danger")
        return redirect(url_for('login'))

    submission = Submission.query.get(submission_id)
    if request.method == 'POST':
        grade_value = request.form['grade']
        feedback = request.form.get('feedback')

        grade = Grade(
            submission_id=submission_id,
            teacher_id=session['teacher_id'],
            grade=grade_value,
            feedback=feedback
        )
        submission.status = "Graded"
        db.session.add(grade)
        db.session.commit()
        flash("Grade submitted successfully!", "success")
        return redirect(url_for('teacher_dashboard'))

    return render_template('grade_submission.html', submission=submission)
@app.route('/submissions')
@login_required
@role_required('teacher')
def submissions():

    # Query all submissions for the teacher
    submissions = Submission.query.all()

    return render_template('submissions.html', submissions=submissions)
#view submission
@app.route('/download_submission_file/<int:submission_id>')
def download_submission_file(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    # Make sure the submission has a file path
    if not submission.file_path:
        flash("No file found for this submission.", "danger")
        return redirect(url_for('submissions'))

    return send_file(submission.file_path, as_attachment=True)
# Define the route to serve files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/view_grades')
@login_required
def view_grades():
    # Check if the user is logged in and is a student
    if 'user_id' not in session or session.get('role') != 'UserRole.student':
        flash("You need to log in as a student to view your grades.", "danger")
        return redirect(url_for('login'))

    # Get the student ID from the session
    student_id = session['user_id']

    # Query grades for the logged-in student
    grades = Grade.query.join(Submission).join(Assignment).filter(Submission.student_id == student_id).all()

    # Check if grades exist
    if not grades:
        flash("You don't have any grades yet.", "info")

    return render_template('view_grades.html', grades=grades)

@app.route('/mygrades')
@login_required
def mygrades():
    return render_template('mygrades.html')
if __name__ == '__main__':
    app.debug = True
    socketio.run(app)
