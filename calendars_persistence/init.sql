CREATE TABLE calendars
(
    id      SERIAL PRIMARY KEY,
    user_id INT NOT NULL
);

CREATE TABLE calendar_events
(
    calendar_id INT NOT NULL REFERENCES calendars (id),
    event_id    INT NOT NULL,
    PRIMARY KEY (calendar_id, event_id)
);

CREATE TABLE calendar_sharing
(
    calendar_id INT NOT NULL REFERENCES calendars (id),
    viewer_id   INT NOT NULL,
    PRIMARY KEY (calendar_id, viewer_id)
);