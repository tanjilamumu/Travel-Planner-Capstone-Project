from flask import Flask, render_template, request, redirect, url_for, session, flash
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
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# -------- ROUTES --------

#with app.app_context():
 #  db.create_all()

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
        flash("Session Expired. please login again.", "Warning")
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

    # Convert strings to date objects
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

# -------- UPDATE TRIP --------
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


# -------- DELETE TRIP --------
@app.route('/trip/<int:trip_id>/delete', methods=['POST'])
def delete_trip(trip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        flash("You are not authorized to delete this trip.", "danger")
        return redirect(url_for('dashboard'))

    # Optional: Delete related itineraries and files
    Itinerary.query.filter_by(trip_id=trip.id).delete()
    File.query.filter_by(trip_id=trip.id).delete()

    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted successfully.", "success")
    return redirect(url_for('dashboard'))


# -------- ITINERARY CRUD --------
from datetime import datetime

@app.route('/trip/<int:trip_id>/itinerary/add', methods=['POST'])
def add_itinerary(trip_id):
    title = request.form['title']
    description = request.form['description']

    # Get the trip to know the date
    trip = Trip.query.get_or_404(trip_id)

    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')

    # Combine trip start date with time input to create full datetime
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

# -------- UPDATE ITINERARY --------
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


# -------- DELETE ITINERARY --------
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
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    new_file = File(trip_id=trip_id, file_name=filename, file_path=file_path)
    db.session.add(new_file)
    db.session.commit()
    flash("File uploaded.", "success")
    return redirect(url_for('view_trip', trip_id=trip_id))

# -------- DELETE FILE --------
@app.route('/file/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    trip = Trip.query.get(file.trip_id)

    if 'user_id' not in session or trip.user_id != session['user_id']:
        flash("Unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    # Delete file from filesystem
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    db.session.delete(file)
    db.session.commit()
    flash("File deleted.", "success")
    return redirect(url_for('view_trip', trip_id=trip.id))


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
