from flask import render_template, url_for, flash, redirect, request, abort, current_app as app
from app import app, db, bcrypt, socketio
from flask_socketio import send, join_room, leave_room
from forms import RegistrationForm, LoginForm, TripForm, ItineraryForm
from models import User, Trip, Itinerary
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image
from opencage.geocoder import OpenCageGeocode
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/trip_pics', picture_fn)

    output_size = (500, 500)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


# For retreiving latitude & longitude coordinates from location
def get_coordinates(destination):
    api_key = os.getenv('OPENCAGE_API_KEY')  # Get the API key from environment variable
    if not api_key:
        raise ValueError("No API key found. Please set the OPENCAGE_API_KEY environment variable.")
    url = f'https://api.opencagedata.com/geocode/v1/json?q={destination}&key={api_key}'
    response = requests.get(url)
    data = response.json()

    if data['results']:
        lat = data['results'][0]['geometry']['lat']
        lng = data['results'][0]['geometry']['lng']
        return lat, lng
    else:
        return None, None



@app.route('/')
@app.route('/home')
def home():
    if current_user.is_authenticated:
        trips = Trip.query.filter_by(user_id=current_user.id).all()
        serialized_trips = [trip.serialize() for trip in trips]
        deserialized_trips = [Trip.deserialize_trip(trip) for trip in serialized_trips]
    else:
        deserialized_trips = []
    return render_template('home.html', trips=deserialized_trips)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/account')
@login_required
def account():
    user_trips = Trip.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', title='Account', trips=user_trips)

@app.route('/trip/new', methods=['GET', 'POST'])
@login_required
def new_trip():
    form = TripForm()
    if form.validate_on_submit():
        if form.photo.data:
            photo_file = save_picture(form.photo.data)
        else:
            photo_file = 'default.jpg'
        
        lat, lng = get_coordinates(form.destination.data)
        if lat is None or lng is None:
            flash('Could not find coordinates for the provided destination.', 'danger')
            return redirect(url_for('new_trip'))

        trip = Trip(name=form.name.data, destination=form.destination.data, start_date=form.start_date.data, photo_file=photo_file, latitude=lat, longitude=lng, organizer=current_user)
        db.session.add(trip)
        db.session.commit()
        flash('Your trip has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_trip.html', title='New Trip', form=form)

@app.route('/trip/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    form = ItineraryForm()
    if form.validate_on_submit():
        itinerary = Itinerary(activity=form.activity.data, date=form.date.data, trip=trip)
        db.session.add(itinerary)
        db.session.commit()
        flash('Itinerary item has been added!', 'success')
        return redirect(url_for('trip', trip_id=trip.id))
    itineraries = Itinerary.query.filter_by(trip_id=trip.id).all()
    return render_template('trip.html', title=trip.name, trip=trip, form=form, itineraries=itineraries)

@app.route('/plan_trip', methods=['GET', 'POST'])
@login_required
def plan_trip():
    if request.method == 'POST':
        # Process the form data
        form_data = request.form.to_dict()
        # Call the function to generate the itinerary using the form data
        itinerary = generate_itinerary(form_data)
        return render_template('itinerary.html', itinerary=itinerary)
    return render_template('plan_trip.html')


@app.route('/trip/<int:trip_id>/update', methods=['GET', 'POST'])
@login_required
def update_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.organizer != current_user:
        abort(403)
    form = TripForm()
    if form.validate_on_submit():
        if form.photo.data:
            photo_file = save_picture(form.photo.data)
            trip.photo_file = photo_file
        trip.name = form.name.data
        trip.destination = form.destination.data
        trip.start_date = form.start_date.data
        
        lat, lng = get_coordinates(form.destination.data)
        if lat is None or lng is None:
            flash('Could not find coordinates for the provided destination.', 'danger')
            return redirect(url_for('update_trip', trip_id=trip.id))
        
        trip.latitude = lat
        trip.longitude = lng
        db.session.commit()
        flash('Your trip has been updated!', 'success')
        return redirect(url_for('trip', trip_id=trip.id))
    elif request.method == 'GET':
        form.name.data = trip.name
        form.destination.data = trip.destination
        form.start_date.data = trip.start_date
    return render_template('edit_trip.html', title='Update Trip', form=form)

@app.route('/trip/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.organizer != current_user:
        abort(403)
    db.session.delete(trip)
    db.session.commit()
    flash('Your trip has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route('/trip/<int:trip_id>/itinerary/<int:item_id>/update', methods=['GET', 'POST'])
@login_required
def update_itinerary(trip_id, item_id):
    itinerary = Itinerary.query.get_or_404(item_id)
    if itinerary.trip.organizer != current_user:
        abort(403)
    form = ItineraryForm()
    if form.validate_on_submit():
        itinerary.activity = form.activity.data
        itinerary.date = form.date.data
        db.session.commit()
        flash('Your itinerary item has been updated!', 'success')
        return redirect(url_for('trip', trip_id=trip_id))
    elif request.method == 'GET':
        form.activity.data = itinerary.activity
        form.date.data = itinerary.date
    return render_template('edit_itinerary.html', title='Update Itinerary', form=form)

@app.route('/trip/<int:trip_id>/itinerary/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_itinerary(trip_id, item_id):
    itinerary = Itinerary.query.get_or_404(item_id)
    if itinerary.trip.organizer != current_user:
        abort(403)
    db.session.delete(itinerary)
    db.session.commit()
    flash('Your itinerary item has been deleted!', 'success')
    return redirect(url_for('trip', trip_id=trip_id))


# Chat-related routes and functions
@app.route('/trip/<int:trip_id>/chat')
@login_required
def chat(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    return render_template('chat.html', title='Chat', trip=trip)

@socketio.on('join')
def on_join(data):
    username = data['username']
    trip_id = data['trip_id']
    join_room(trip_id)
    send(f'{username} has joined the chat.', to=trip_id)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    trip_id = data['trip_id']
    leave_room(trip_id)
    send(f'{username} has left the chat.', to=trip_id)

@socketio.on('message')
def handle_message(data):
    msg = data['msg']
    trip_id = data['trip_id']
    username = data['username']
    send(f'{username}: {msg}', to=trip_id)