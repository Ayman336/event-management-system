-- User table (Admin, Organizer, Attendee)
CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'organizer', 'attendee')) NOT NULL
);

-- Venue table
CREATE TABLE IF NOT EXISTS Venue (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    capacity INTEGER NOT NULL
);

-- Event table
CREATE TABLE IF NOT EXISTS Event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    location TEXT NOT NULL,
    organizer_id INTEGER NOT NULL,
    venue_id INTEGER NOT NULL,
    FOREIGN KEY (organizer_id) REFERENCES User(user_id),
    FOREIGN KEY (venue_id) REFERENCES Venue(venue_id)
);

-- Ticket table
CREATE TABLE IF NOT EXISTS Ticket (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    attendee_id INTEGER NOT NULL,
    purchase_date DATE NOT NULL,
    status TEXT CHECK(status IN ('active', 'cancelled')) DEFAULT 'active',
    FOREIGN KEY (event_id) REFERENCES Event(event_id),
    FOREIGN KEY (attendee_id) REFERENCES User(user_id)
);

-- Feedback table
CREATE TABLE IF NOT EXISTS Feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    attendee_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    submitted_at DATE,
    FOREIGN KEY (event_id) REFERENCES Event(event_id),
    FOREIGN KEY (attendee_id) REFERENCES User(user_id)
);

-- Announcement table
CREATE TABLE IF NOT EXISTS Announcement (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    posted_at DATE NOT NULL,
    posted_by INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES Event(event_id),
    FOREIGN KEY (posted_by) REFERENCES User(user_id)
);

-- View: EventParticipants
CREATE VIEW IF NOT EXISTS EventParticipants AS
SELECT e.event_id, e.title, u.name AS attendee_name, t.ticket_id
FROM Ticket t
JOIN Event e ON t.event_id = e.event_id
JOIN User u ON t.attendee_id = u.user_id
WHERE t.status = 'active';

-- Trigger: Enforce venue capacity when buying a ticket
CREATE TRIGGER IF NOT EXISTS check_ticket_capacity
BEFORE INSERT ON Ticket
BEGIN
    SELECT
        CASE
            WHEN (
                SELECT COUNT(*) FROM Ticket WHERE event_id = NEW.event_id AND status = 'active'
            ) >= (
                SELECT capacity FROM Venue WHERE venue_id = (SELECT venue_id FROM Event WHERE event_id = NEW.event_id)
            )
            THEN
                RAISE(ABORT, 'Cannot purchase ticket: venue capacity reached.')
        END;
END;