CREATE TABLE login (
    auth_token VARCHAR(255) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    active BOOLEAN NOT NULL
);
