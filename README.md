# Event Management System

A simple Flask-based event management system, for database coursework.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Initialize the database (run once):
   ```
   python app.py
   # Visit http://127.0.0.1:5000/initdb in your browser
   ```

3. Run the app:
   ```
   python app.py
   ```

4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Features

- Roles: Admin, Organizer, Attendee
- CRUD for users, venues, events, tickets
- Foreign keys, views, triggers in DB
- Trigger handles venue capacity; error shown on the page
- Announcements, feedback, participant view

---