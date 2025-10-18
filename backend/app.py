# -*- coding: utf-8 -*-
from typing import Any
import flask
import flask_login
import mysql.connector

app: flask.Flask = flask.Flask(
    __name__, template_folder="../templates", static_folder="../static"
)


def get_db_connection() -> mysql.connector.connection.MySQLConnection:
    """Establishes and returns a connection to the MySQL database."""
    connection = mysql.connector.connect(
        host="localhost", user="root", password="", database="bigbag"
    )
    return connection


@app.route("/")
def index() -> str:
    """Renders the index page."""
    return flask.render_template("index.html")


@app.route("/logowanie")
def login() -> str:
    """Renders the login page."""
    return flask.render_template("login.html")


@app.route("/logowanie/urzednik")
def login_staff() -> str:
    """Renders the official login page."""
    return flask.render_template("login_staff.html")


@app.route("/rejestracja")
def signup() -> str:
    """Renders the signup page."""
    return flask.render_template("signup.html")


@app.route("/wniosek")
def application_form() -> str:
    """Renders the wniosek page."""
    return flask.render_template("application_form.html")


@app.route("/panel/mieszkaniec")
def resident_dashboard() -> str:
    """Renders the panel for residents."""
    return flask.render_template("resident_dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)
