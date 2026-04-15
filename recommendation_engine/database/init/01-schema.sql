CREATE TABLE IF NOT EXISTS content (
    content_id    VARCHAR(20) PRIMARY KEY,
    title         VARCHAR(255) NOT NULL,
    description   TEXT,
    duration_mins INTEGER,
    release_year  INTEGER,
    language      VARCHAR(50),
    content_type  VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS content_genres (
    content_id  VARCHAR(20) REFERENCES content(content_id),
    genre       VARCHAR(50),
    PRIMARY KEY (content_id, genre)
);

CREATE TABLE IF NOT EXISTS users (
    user_id       VARCHAR(20) PRIMARY KEY,
    username      VARCHAR(100),
    email         VARCHAR(255),
    region        VARCHAR(100),
    age_group     VARCHAR(20),
    created_at    TIMESTAMP DEFAULT NOW()
);