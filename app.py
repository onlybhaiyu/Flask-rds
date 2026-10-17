import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template_string

load_dotenv()

app = Flask(__name__)


# Connect to Amazon RDS MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=10
    )


# UI written directly inside app.py
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Flask RDS Contact Manager</title>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
        }

        .container {
            max-width: 750px;
            margin: 50px auto;
            padding: 25px;
        }

        .card {
            background: white;
            padding: 25px;
            margin-bottom: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.07);
        }

        h1 {
            color: #2563eb;
            margin-top: 0;
        }

        h2 {
            font-size: 20px;
        }

        input {
            width: 100%;
            padding: 12px;
            margin: 8px 0 15px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
        }

        button {
            background: #2563eb;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 6px;
            cursor: pointer;
        }

        button:hover {
            background: #1d4ed8;
        }

        .message {
            padding: 12px;
            background: #dcfce7;
            color: #166534;
            border-radius: 6px;
            margin-bottom: 15px;
        }

        .error {
            background: #fee2e2;
            color: #991b1b;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            overflow-wrap: anywhere;
        }

        th {
            background: #eff6ff;
        }

        .status {
            color: #15803d;
            font-weight: bold;
        }

        @media (max-width: 600px) {
            .container {
                margin: 15px auto;
                padding: 12px;
            }

            .card {
                padding: 18px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Contact Manager</h1>
            <p>Flask application connected to Amazon RDS MySQL.</p>
            <p class="status">Application is running</p>
        </div>

        {% if message %}
            <div class="message {% if error %}error{% endif %}">
                {{ message }}
            </div>
        {% endif %}

        <div class="card">
            <h2>Add a Contact</h2>
            <form action="/add" method="POST">
                <label for="name">Full Name</label>
                <input id="name" type="text" name="name"
                       maxlength="100" required
                       placeholder="Enter your name">

                <label for="email">Email Address</label>
                <input id="email" type="email" name="email"
                       maxlength="255" required
                       placeholder="Enter your email">

                <button type="submit">Save Contact</button>
            </form>
        </div>

        <div class="card">
            <h2>Saved Contacts</h2>
            {% if contacts %}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Email</th>
                    </tr>
                </thead>
                <tbody>
                    {% for contact in contacts %}
                    <tr>
                        <td>{{ contact[0] }}</td>
                        <td>{{ contact[1] }}</td>
                        <td>{{ contact[2] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
                <p>No contacts found.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    contacts = []
    message = request.args.get("message", "")
    error = request.args.get("error", "") == "1"
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, name, email FROM contacts ORDER BY id DESC"
        )
        contacts = cursor.fetchall()

    except mysql.connector.Error:
        app.logger.exception("Could not retrieve contacts")
        message = "Database connection failed. Check application logs."
        error = True

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return render_template_string(
        HTML, contacts=contacts, message=message, error=error
    )


@app.route("/add", methods=["POST"])
def add_contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email or len(name) > 100 or len(email) > 255:
        return redirect(url_for(
            "home", message="Please enter valid name and email values.",
            error=1
        ))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO contacts (name, email) VALUES (%s, %s)",
            (name, email)
        )
        connection.commit()

        return redirect(url_for(
            "home", message="Contact saved successfully!"
        ))

    except mysql.connector.Error:
        app.logger.exception("Could not save contact")
        return redirect(url_for(
            "home", message="Could not save contact. Check application logs.",
            error=1
        ))

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/db-check")
def db_check():
    connection = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]
        cursor.close()

        return {
            "status": "Connected successfully",
            "database": database
        }

    except mysql.connector.Error:
        app.logger.exception("Database connection failed")
        return {"status": "Connection failed"}, 500

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
