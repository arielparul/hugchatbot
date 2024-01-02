# ChatBot Application API

This repository contains a Flask application that serves as a simple chatbot. The application integrates with a PostgreSQL database to manage user authentication, conversation history, and the Hugging Face ChatGPT model for generating responses.

## Features

- **User Authentication (`/api/check_auth_status`):**
  - Validates user authentication against the PostgreSQL database.
  - Checks if the user's account is active.

- **User Conversation (`/api/user_conversation`):**
  - Saves user questions in the `conversation_history` table.
  - Utilizes the Hugging Face ChatGPT model for generating responses.
  - Stores bot responses in the `conversation_history` table.

- **Start New Conversation (`/api/start_new_conversation`):**
  - Initiates a new conversation by inserting an initial null message.
  - Saves user questions and bot responses in the `conversation_history` table.

- **Delete User History (`/api/delete_user_history`):**
  - Deletes the user's conversation history from the `conversation_history` table.

## Prerequisites

- Python 3.x
- PostgreSQL database
- Hugging Face ChatGPT API key

## Setup

1. Clone the repository:

   ```bash
     [git clone https://github.com/arielparul/hugchatbot.git]
     cd app_api.py


### Install dependencies:

2. pip install -r requirements.txt


