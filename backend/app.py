# -*- coding: utf-8 -*-
import flask
import mysql.connector

app: flask.Flask = flask.Flask(__name__)


def get_db_connection() -> mysql.connector.connection.MySQLConnection:
    """Establishes and returns a connection to the MySQL database."""
    connection: mysql.connector.connection.MySQLConnection = mysql.connector.connect(
        host="localhost", user="root", password="", database="bigbag"
    )
    return connection


@app.route("/")
def index() -> str:
    """Renders the index page."""
    return flask.render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
