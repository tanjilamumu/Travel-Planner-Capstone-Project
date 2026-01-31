from multiprocessing.util import debug
import boto3
from flask import Flask, logging, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, User, Trip, Itinerary, File

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# -------- CONFIG --------
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:Abc12345.@database-3.c7224ew0aex5.us-east-2.rds.amazonaws.com/data'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# boto3 S3 Configuration
BUCKET_NAME = os.environ.get("BUCKET_NAME", "smart-travel-s3")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def upload_file_to_s3(file_obj, file_name):
    try:
        s3.upload_fileobj(file_obj, BUCKET_NAME, file_name)
        logging.info(f"File {file_name} uploaded to S3 bucket {BUCKET_NAME}")
        return f"s3://{BUCKET_NAME}/{file_name}"
    except Exception as e:
        logging.error(f"Error uploading file to S3: {e}")
        return None

# -------- ROUTES --------

# with app.app_context():
#   db.create_all()

@app.route('/')
def home():
    return render_template('home.html')


# -------- AUTH --------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect(url_for('register'))

        user = User(first_name=first_name, last_name=last_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Logged in successfully", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out", "info")
    return redirect(url_for('home'))


# -------- DASHBOARD --------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if not user:
        session.clear()
        flash("Session Expired. Please login again.", "warning")
        return redirect(url_for('login'))
    
    trips = Trip.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', trips=trips, user=user)


# -------- TRIP CRUD --------
@app.route('/trip/add', methods=['POST'])
def add_trip():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    destination = request.form['destination']
    notes = request.form['notes']

    start_date_str = request.form['start_date']
    end_date_str = request.form['end_date']

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for('dashboard'))

    trip = Trip(
        user_id=session['user_id'],
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        notes=notes
    )
    db.session.add(trip)
    db.session.commit()
    flash("Trip added.", "success")
    return redirect(url_for('dashboard'))


@app.route('/trip/<int:trip_id>')
def view_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    itineraries = Itinerary.query.filter_by(trip_id=trip.id).all()
    files = File.query.filter_by(trip_id=trip.id).all()
    return render_template('trip_detail.html', trip=trip, itineraries=itineraries, files=files)


@app.route('/trip/<int:trip_id>/edit', methods=['GET', 'POST'])
def edit_trip(trip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    trip = Trip.query.get_or_404(trip_id)

    if trip.user_id != session['user_id']:
        flash("You are not authorized to edit this trip.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        trip.destination = request.form['destination']
        trip.notes = request.form['notes']

        try:
            trip.start_date = datetime.strptime(request.form['start_date'], "%Y-%m-%d").date()
            trip.end_date = datetime.strptime(request.form['end_date'], "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('edit_trip', trip_id=trip.id))

        db.session.commit()
        flash("Trip updated successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_trip.html', trip=trip)


@app.route('/trip/<int:trip_id>/delete', methods=['POST'])
def delete_trip(trip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        flash("You are not authorized to delete this trip.", "danger")
        return redirect(url_for('dashboard'))

    Itinerary.query.filter_by(trip_id=trip.id).delete()
    File.query.filter_by(trip_id=trip.id).delete()

    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted successfully.", "success")
    return redirect(url_for('dashboard'))


# -------- ITINERARY CRUD --------
@app.route('/trip/<int:trip_id>/itinerary/add', methods=['POST'])
def add_itinerary(trip_id):
    title = request.form['title']
    description = request.form['description']

    trip = Trip.query.get_or_404(trip_id)

    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')

    start_datetime = None
    end_datetime = None

    if start_time_str:
        start_time_obj = datetime.strptime(start_time_str, "%H:%M").time()
        start_datetime = datetime.combine(trip.start_date, start_time_obj)

    if end_time_str:
        end_time_obj = datetime.strptime(end_time_str, "%H:%M").time()
        end_datetime = datetime.combine(trip.start_date, end_time_obj)

    itinerary = Itinerary(
        trip_id=trip_id,
        title=title,
        description=description,
        start_time=start_datetime,
        end_time=end_datetime
    )

    db.session.add(itinerary)
    db.session.commit()
    flash("Itinerary added.", "success")
    return redirect(url_for('view_trip', trip_id=trip_id))


@app.route('/itinerary/<int:itinerary_id>/edit', methods=['GET', 'POST'])
def edit_itinerary(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    trip = Trip.query.get(itinerary.trip_id)

    if 'user_id' not in session or trip.user_id != session['user_id']:
        flash("Unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        itinerary.title = request.form['title']
        itinerary.description = request.form['description']

        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        if start_time_str:
            start_time_obj = datetime.strptime(start_time_str, "%H:%M").time()
            itinerary.start_time = datetime.combine(trip.start_date, start_time_obj)
        else:
            itinerary.start_time = None

        if end_time_str:
            end_time_obj = datetime.strptime(end_time_str, "%H:%M").time()
            itinerary.end_time = datetime.combine(trip.start_date, end_time_obj)
        else:
            itinerary.end_time = None

        db.session.commit()
        flash("Itinerary updated.", "success")
        return redirect(url_for('view_trip', trip_id=trip.id))

    return render_template('edit_itinerary.html', itinerary=itinerary, trip=trip)


@app.route('/itinerary/<int:itinerary_id>/delete', methods=['POST'])
def delete_itinerary(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    trip = Trip.query.get(itinerary.trip_id)

    if 'user_id' not in session or trip.user_id != session['user_id']:
        flash("Unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    db.session.delete(itinerary)
    db.session.commit()
    flash("Itinerary deleted.", "success")
    return redirect(url_for('view_trip', trip_id=trip.id))


# -------- FILE UPLOAD --------
@app.route('/trip/<int:trip_id>/upload', methods=['POST'])
def upload_file(trip_id):
    if 'file' not in request.files:
        flash("No file part", "danger")
        return redirect(url_for('view_trip', trip_id=trip_id))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file", "danger")
        return redirect(url_for('view_trip', trip_id=trip_id))

    filename = secure_filename(file.filename)
    s3_uri = upload_file_to_s3(file, filename)

    if s3_uri:
        new_file = File(trip_id=trip_id, file_name=filename, file_path=s3_uri)
        db.session.add(new_file)
        db.session.commit()
        flash("File uploaded to S3 successfully!", "success")
    else:
        flash("Failed to upload file to S3.", "danger")

    return redirect(url_for('view_trip', trip_id=trip_id))


@app.route('/file/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    trip = Trip.query.get(file.trip_id)

    if 'user_id' not in session or trip.user_id != session['user_id']:
        flash("Unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    try:
        s3_key = file.file_path.split(f"s3://{BUCKET_NAME}/")[-1]
        s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
    except Exception as e:
        logging.error(f"Error deleting file from S3: {e}")
        flash("Failed to delete file from S3.", "danger")

    db.session.delete(file)
    db.session.commit()
    flash("File deleted successfully.", "success")
    return redirect(url_for('view_trip', trip_id=trip.id))


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
