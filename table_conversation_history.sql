CREATE TABLE public.conversation_history (
    message_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES public.users(user_id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sender VARCHAR(50),  -- 'user' or 'bot' to denote the sender
    message_text TEXT
);