CREATE TABLE public.users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    status BOOLEAN NOT NULL
);