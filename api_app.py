from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
from hugchat import hugchat
from hugchat.exceptions import ChatError
import logging
import config
from datetime import datetime
from psycopg2 import sql, connect, Error

app = Flask(__name__)
auth_token = config.CHATGPT_AUTH_TOKEN


# Database configuration
db_config = {
    'host': 'localhost',
    'port': 5000,
    'database': 'chatbot',
    'user': 'postgres',
    'sslmode': 'prefer',
    'connect_timeout': 10,
    'password': 'Admin@123'  
}

#CHAT START
def create_chatbot():
    try:
        return hugchat.ChatBot(cookies={'Authorization': f'Bearer {auth_token}'})
    except ChatError as e:
        logging.error(f"Authentication error: {e}")
        exit()

# Initial creation of ChatBot
chatbot = create_chatbot()


@app.route('/api/check_auth_status', methods=['GET'])
def check_auth_status():
    try:
        # Get auth token (key) from the request headers
        auth_token = request.headers.get('key')

        if not auth_token:
            return jsonify({"error": "Authorization token (key) is required"}), 401

        with psycopg2.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
                    sql.Literal(auth_token)
                )
                cursor.execute(query)

                user = cursor.fetchone()

                if user:
                    # Check if the account is active
                    if user[5]:  #  'status' is at index 5
                        logging.info("Authentication successful. Proceeding to next step.")
                        
                        # Extract user data
                        user_data = {
                            'user_id': user[0],
                            'email': user[1],
                            'first_name': user[2],
                            'last_name': user[3],
                            'key': user[4],
                            'status': user[5]
                        }

                        return jsonify({"message": "You can proceed now.", "user_data": user_data}), 200
                    else:
                        return jsonify({"error": "Account not active"}), 401
                else:
                    return jsonify({"error": "Invalid key or account not found"}), 401

    except psycopg2.Error as e:
        # Handle database connection errors
        logging.error(f"Error connecting to PostgreSQL: {e}")
        return jsonify({"error": "Error connecting to the database"}), 500


#function to save user ques
def save_user_question(user_id, user_message, cursor):
    try:
        # Use parameterized query to prevent SQL injection
        insert_query_user = sql.SQL("""
            INSERT INTO conversation_history (user_id, sender, message_text, created_at)
            VALUES ({}, {}, {}, {})
        """).format(
            sql.Literal(user_id),
            sql.Literal('user'),
            sql.Literal(user_message),
            sql.Literal(datetime.utcnow())
        )
        cursor.execute(insert_query_user)

        return jsonify({"message": "User question saved successfully"}), 200

    except Error as e:
        # Handle database errors
        logging.error(f"Error saving user question: {e}")
        return jsonify({"error": "Error saving user question"}), 500


#START CONVERSATION AND SHOW ALL USERS CONVERSATION IN DB
@app.route('/api/user_conversation', methods=['POST'])
def all_users_conversation():
    try:
        # Get auth token (key) from the request parameters
        auth_token = request.args.get('key')
        if not auth_token:
            return jsonify({"error": "Authorization token (key) is required"}), 400

        with connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
                    sql.Literal(auth_token)
                )
                cursor.execute(query)

                user = cursor.fetchone()

                if user:
                    # Check if the user's status is active
                    if user[5]:  #  'status' is at index 5
                        # Get user_message from JSON in the request body
                        data = request.get_json()
                        user_message = data.get('user_message')

                        if not user_message:
                            return jsonify({"error": "User message is missing in the request body"}), 400

                        # Save the user's question in conversation_history
                        save_user_question(user[0], user_message, cursor)

                        # Use Hugging Face ChatGPT to get a response
                        response_message = chatbot.chat(user_message)

                        # Convert the Message object to a string
                        response_text = str(response_message)

                        # Save the bot's response in conversation_history
                        insert_query_bot = sql.SQL("""
                            INSERT INTO conversation_history (user_id, sender, message_text, created_at)
                            VALUES ({}, {}, {}, {})
                        """).format(
                            sql.Literal(user[0]),  #  'user_id' is at index 0
                            sql.Literal('bot'),  # Sender is the bot
                            sql.Literal(response_text),  #  'text' is the attribute holding the message text
                            sql.Literal(datetime.utcnow())  # Use the current time as the creation time for the bot's response
                        )
                        cursor.execute(insert_query_bot)

                        return jsonify({"message": response_text}), 200
                    else:
                        # If user status is not active, send a response to get approval from admin
                        return jsonify({"error": "Your account is inactive. Please contact the admin for approval"}), 401
                else:
                    return jsonify({"error": "Invalid key or account not active"}), 401

    except Error as e:
        # Handle database connection errors
        logging.error(f"Error connecting to PostgreSQL: {e}")
        return jsonify({"error": "Error connecting to the database"}), 500
    

#CREATE NEW CONVERSATION
@app.route('/api/start_new_conversation', methods=['POST'])
def start_new_conversation():
    try:
        # Get auth token (key) from the request parameters
        auth_token = request.args.get('key')

        if not auth_token:
            return jsonify({"error": "Authorization token (key) is required"}), 400

        with connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
                    sql.Literal(auth_token)
                )
                cursor.execute(query)

                user = cursor.fetchone()

                if user:
                    # Check if the user's status is active
                    if user[5]:  #'status' is at index 5
                        # Start a new conversation with an initial null message
                        insert_query = sql.SQL("""
                            INSERT INTO conversation_history (user_id, sender, message_text, created_at)
                            VALUES ({}, {}, {}, {})
                            RETURNING message_id
                        """).format(
                            sql.Literal(user[0]),  #'user_id' is at index 0
                            sql.Literal('user'),  # Sender is the user
                            sql.SQL('NULL'),  # Initial null message
                            sql.Literal(datetime.utcnow())
                        )

                        cursor.execute(insert_query)

                        # Get the message_id of the null message
                        null_message_id = cursor.fetchone()[0]

                        # Now, ask a new question and update the conversation history
                        data = request.get_json()
                        user_question = data.get('user_question')

                        if not user_question:
                            return jsonify({"error": "User question is missing in the request body"}), 400
                        
                        # Save the user's question in conversation_history
                        save_user_question(user[0], user_question, cursor)

                        # Use Hugging Face ChatGPT to get a response
                        response_message = chatbot.chat(user_question)

                        # Convert the Message object to a string
                        response_text = str(response_message)

                        # Update the conversation history with the user question and bot's response
                        update_query = sql.SQL("""
                            UPDATE conversation_history
                            SET sender = {}, message_text = {}
                            WHERE message_id = {}
                        """).format(
                            sql.Literal('user'),  # Sender is now the user
                            sql.Literal(response_text),  # User's question becomes the message text
                            sql.Literal(null_message_id)
                        )

                        cursor.execute(update_query)

                        return jsonify({"message": response_text, "message_id": null_message_id}), 200
                    else:
                        # If user status is not active, send a response to get approval from admin
                        return jsonify({"error": "Your account is inactive. Please contact the admin for approval"}), 401
                else:
                    return jsonify({"error": "Invalid key or account not active"}), 401

    except Error as e:
        # Handle database connection errors
        logging.error(f"Error connecting to PostgreSQL: {e}")
        return jsonify({"error": "Error connecting to the database"}), 500


# #CREATE USER CONTINUE CHAT(CHAT STARTS FROM LAST WHERE U END)
# @app.route('/api/continue_chat', methods=['POST'])
# def continue_chat():
#     try:
#         # Get auth token (key) from the request parameters
#         auth_token = request.args.get('key')

#         if not auth_token:
#             return jsonify({"error": "Authorization token (key) is required"}), 400

#         with psycopg2.connect(**db_config) as connection:
#             with connection.cursor() as cursor:
#                 # Use parameterized query to prevent SQL injection
#                 query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
#                     sql.Literal(auth_token)
#                 )
#                 cursor.execute(query)

#                 user = cursor.fetchone()

#                 if user:
#                     # Get the last user's message from the chat history
#                     last_user_message_query = sql.SQL("""
#                         SELECT message_text
#                         FROM conversation_history
#                         WHERE user_id = {}
#                         AND sender = 'user'
#                         ORDER BY created_at DESC
#                         LIMIT 1
#                     """).format(sql.Literal(user[0]))  #  'user_id' is at index 0

#                     cursor.execute(last_user_message_query)
#                     last_user_message = cursor.fetchone()

#                     if last_user_message:
#                         # Use Hugging Face ChatGPT to continue the chat
#                         response_message = chatbot.chat(last_user_message[0])

#                         # Save the bot's response in conversation_history
#                         insert_query_bot = sql.SQL("""
#                             INSERT INTO conversation_history (user_id, sender, message_text, created_at)
#                             VALUES ({}, {}, {}, {})
#                         """).format(
#                             sql.Literal(user[0]),  #  'user_id' is at index 0
#                             sql.Literal('bot'),  # Sender is the bot
#                             sql.Literal(str(response_message)),  # Convert the Message object to a string
#                             sql.Literal(datetime.utcnow())
#                         )
#                         cursor.execute(insert_query_bot)

#                         return jsonify({"message": str(response_message)}), 200
#                     else:
#                         return jsonify({"error": "No previous user message found"}), 404

#                 else:
#                     return jsonify({"error": "Invalid key or account not active"}), 401

#     except psycopg2.Error as e:
#         # Handle database connection errors
#         logging.error(f"Error connecting to PostgreSQL: {e}")
#         return jsonify({"error": "Error connecting to the database"}), 500


#SHOW HISTORY FOR ONE USER
# @app.route('/api/user_history', methods=['GET'])
# def get_user_history():
#     try:
#         # Get auth token (key) from the request parameters
#         auth_token = request.args.get('key')

#         if not auth_token:
#             return jsonify({"error": "Authorization token (key) is required"}), 400

#         with psycopg2.connect(**db_config) as connection:
#             with connection.cursor() as cursor:
#                 # Use parameterized query to prevent SQL injection
#                 query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
#                     sql.Literal(auth_token)
#                 )
#                 cursor.execute(query)

#                 user = cursor.fetchone()

#                 if user:
#                     # Retrieve user's conversation history from conversation_history table
#                     history_query = sql.SQL("""
#                         SELECT sender, message_text, created_at
#                         FROM conversation_history
#                         WHERE user_id = {}
#                         ORDER BY created_at DESC
#                     """).format(
#                         sql.Literal(user[0])  #  'user_id' is at index 0
#                     )
#                     cursor.execute(history_query)

#                     history_entries = cursor.fetchall()

#                     # Format the history entries
#                     formatted_history = [
#                         {
#                             "sender": entry[0],
#                             "message_text": entry[1],
#                             "created_at": entry[2]  #  'created_at' is at index 2
#                         }
#                         for entry in history_entries
#                     ]

#                     return jsonify({"user_history": formatted_history}), 200

#                 else:
#                     return jsonify({"error": "Invalid key or account not active"}), 401

#     except psycopg2.Error as e:
#         # Handle database connection errors
#         logging.error(f"Error connecting to PostgreSQL: {e}")
#         return jsonify({"error": "Error connecting to the database"}), 500


#DELETE USER HISTORY
@app.route('/api/delete_user_history', methods=['POST'])
def delete_user_history():
    try:
        # Get auth token (key) from the request parameters
        auth_token = request.json.get('key')

        if not auth_token:
            return jsonify({"error": "Authorization token (key) is required"}), 400

        with psycopg2.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                query = sql.SQL("SELECT * FROM users WHERE key = {} AND status = TRUE").format(
                    sql.Literal(auth_token)
                )
                cursor.execute(query)

                user = cursor.fetchone()

                if user:
                    # Delete user's conversation history from conversation_history table
                    delete_query = sql.SQL("""
                        DELETE FROM conversation_history
                        WHERE user_id = {}
                    """).format(
                        sql.Literal(user[0])  #  'user_id' is at index 0
                    )
                    cursor.execute(delete_query)

                    return jsonify({"message": "User history deleted successfully"}), 200

                else:
                    return jsonify({"error": "Invalid key or account not active"}), 401

    except psycopg2.Error as e:
        # Handle database connection errors
        logging.error(f"Error connecting to PostgreSQL: {e}")
        return jsonify({"error": "Error connecting to the database"}), 500


if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5001, ssl_context='adhoc')
