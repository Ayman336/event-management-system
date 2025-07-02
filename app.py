import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = os.path.join(os.path.dirname(__file__), 'db', 'event_mgmt.db')

# ---------- Database Utilities ----------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open(os.path.join('db', 'schema.sql'), 'r') as f:
            db.executescript(f.read())
        db.commit()

# ---------- Auth ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        name, email, password, role = request.form['name'], request.form['email'], request.form['password'], request.form['role']
        try:
            db.execute("INSERT INTO User (name, email, password, role) VALUES (?, ?, ?, ?)", (name, email, password, role))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'danger')
    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        email, password = request.form['email'], request.form['password']
        user = db.execute("SELECT * FROM User WHERE email=? AND password=?", (email, password)).fetchone()
        if user:
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# ---------- Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'])

# ---------- Admin: Manage Users & Venues ----------
@app.route('/users')
def users():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    db = get_db()
    users = db.execute("SELECT * FROM User").fetchall()
    return render_template('users.html', users=users)

@app.route('/venues')
def venues():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    db = get_db()
    venues = db.execute("SELECT * FROM Venue").fetchall()
    return render_template('venues.html', venues=venues)

@app.route('/add_venue', methods=['GET', 'POST'])
def add_venue():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name, address, capacity = request.form['name'], request.form['address'], request.form['capacity']
        db = get_db()
        db.execute("INSERT INTO Venue (name, address, capacity) VALUES (?, ?, ?)", (name, address, capacity))
        db.commit()
        flash('Venue added.', 'success')
        return redirect(url_for('venues'))
    return render_template('add_venue.html')

# ---------- Events ----------
@app.route('/events')
def events():
    db = get_db()
    role = session.get('role')
    user_id = session.get('user_id')
    if role == 'organizer':
        events = db.execute("SELECT * FROM Event WHERE organizer_id=?", (user_id,)).fetchall()
    else:
        events = db.execute("SELECT * FROM Event").fetchall()
    return render_template('events.html', events=events, role=role)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM Event WHERE event_id=?", (event_id,)).fetchone()
    organizer = db.execute("SELECT name FROM User WHERE user_id=?", (event['organizer_id'],)).fetchone()
    venue = db.execute("SELECT * FROM Venue WHERE venue_id=?", (event['venue_id'],)).fetchone()
    tickets = db.execute("SELECT * FROM Ticket WHERE event_id=?", (event_id,)).fetchall()
    attendees = db.execute(
        "SELECT u.name FROM Ticket t JOIN User u ON t.attendee_id = u.user_id WHERE t.event_id=? AND t.status='active'", 
        (event_id,)
    ).fetchall()
    announcements = db.execute("SELECT * FROM Announcement WHERE event_id=?", (event_id,)).fetchall()
    feedbacks = db.execute("SELECT * FROM Feedback WHERE event_id=?", (event_id,)).fetchall()
    return render_template('event_detail.html', event=event, organizer=organizer, venue=venue, tickets=tickets, attendees=attendees, announcements=announcements, feedbacks=feedbacks)

# ---------- Organizer: Add Event ----------
@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if session.get('role') not in ['organizer', 'admin']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    db = get_db()
    venues = db.execute("SELECT * FROM Venue").fetchall()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        venue_id = request.form['venue_id']
        organizer_id = session['user_id']
        db.execute(
            "INSERT INTO Event (title, description, date, location, organizer_id, venue_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, date, location, organizer_id, venue_id)
        )
        db.commit()
        flash('Event created!', 'success')
        return redirect(url_for('events'))
    return render_template('add_event.html', venues=venues)

# ---------- Buy Ticket (with trigger handling) ----------
@app.route('/buy_ticket/<int:event_id>', methods=['POST'])
def buy_ticket(event_id):
    if session.get('role') != 'attendee':
        flash('Only attendees can buy tickets.', 'danger')
        return redirect(url_for('events'))
    db = get_db()
    try:
        db.execute(
            "INSERT INTO Ticket (event_id, attendee_id, purchase_date, status) VALUES (?, ?, ?, 'active')",
            (event_id, session['user_id'], datetime.now().strftime('%Y-%m-%d'))
        )
        db.commit()
        flash('Ticket purchased!', 'success')
    except sqlite3.IntegrityError as e:
        if 'venue capacity reached' in str(e):
            flash('Cannot purchase ticket: venue capacity reached.', 'danger')
        else:
            flash('An error occurred: ' + str(e), 'danger')
    return redirect(url_for('events'))

# ---------- Cancel Ticket ----------
@app.route('/cancel_ticket/<int:ticket_id>', methods=['POST'])
def cancel_ticket(ticket_id):
    if session.get('role') != 'attendee':
        flash('Only attendees can cancel tickets.', 'danger')
        return redirect(url_for('events'))
    db = get_db()
    db.execute("UPDATE Ticket SET status='cancelled' WHERE ticket_id=? AND attendee_id=?", (ticket_id, session['user_id']))
    db.commit()
    flash('Ticket cancelled.', 'info')
    return redirect(url_for('events'))

# ---------- Feedback ----------
@app.route('/feedback/<int:event_id>', methods=['POST'])
def feedback(event_id):
    if session.get('role') != 'attendee':
        flash('Only attendees can submit feedback.', 'danger')
        return redirect(url_for('events'))
    rating = int(request.form['rating'])
    comment = request.form['comment']
    db = get_db()
    db.execute(
        "INSERT INTO Feedback (event_id, attendee_id, rating, comment, submitted_at) VALUES (?, ?, ?, ?, ?)",
        (event_id, session['user_id'], rating, comment, datetime.now().strftime('%Y-%m-%d'))
    )
    db.commit()
    flash('Feedback submitted.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

# ---------- Announcement ----------
@app.route('/announcement/<int:event_id>', methods=['POST'])
def announcement(event_id):
    if session.get('role') != 'organizer':
        flash('Only organizers can post announcements.', 'danger')
        return redirect(url_for('events'))
    content = request.form['content']
    db = get_db()
    db.execute(
        "INSERT INTO Announcement (event_id, content, posted_at, posted_by) VALUES (?, ?, ?, ?)",
        (event_id, content, datetime.now().strftime('%Y-%m-%d'), session['user_id'])
    )
    db.commit()
    flash('Announcement posted.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

# ---------- View: Event Participants ----------
@app.route('/participants/<int:event_id>')
def participants(event_id):
    db = get_db()
    participants = db.execute(
        "SELECT * FROM EventParticipants WHERE event_id=?", (event_id,)
    ).fetchall()
    return render_template('participants.html', participants=participants)

# ---------- Utility: init DB route (not for prod) ----------
@app.route('/initdb')
def initdb():
    init_db()
    flash('Database initialized.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        init_db()
    app.run(debug=True)