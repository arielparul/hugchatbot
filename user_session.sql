CREATE TABLE user_session (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    session_data BYTEA NOT NULL
);