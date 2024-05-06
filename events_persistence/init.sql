CREATE TYPE participation AS ENUM ('Dont Participate', 'Participate', 'Maybe Participate');

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_date TIMESTAMP NOT NULL,
    organizer_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE event_invitations (
    event_id INT NOT NULL REFERENCES events(id),
    user_id INT NOT NULL,
    PRIMARY KEY (event_id, user_id)
);

CREATE TABLE event_participation (
    event_id INT NOT NULL REFERENCES events(id),
    user_id INT NOT NULL,
    response participation NOT NULL,
    PRIMARY KEY (event_id, user_id)
);