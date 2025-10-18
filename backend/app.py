# -*- coding: utf-8 -*-
from typing import Any
import flask
import flask_login
import mysql.connector

app: flask.Flask = flask.Flask(
    __name__, template_folder="../templates", static_folder="../static"
)
app.secret_key = "wielkiedildo33cm"

flask_login_manager: flask_login.LoginManager = flask_login.LoginManager()


class User(flask_login.UserMixin):
    """Represents a user for authentication purposes."""

    def __init__(self, id: str, type: str) -> None:
        super().__init__()
        self.id = id
        self.type: str = type
        self.first_name: str = self._get_first_name()

    @staticmethod
    def get(user_id: str, type: str) -> "User | None":
        cursor = db_connection.cursor(dictionary=True)
        if type == "citizen":
            cursor.execute(
                "SELECT id_citizen FROM citizen WHERE id_citizen = %s",
                (user_id,),
            )
        else:
            cursor.execute(
                "SELECT id_employee FROM employee WHERE id_employee = %s",
                (user_id,),
            )
        result = cursor.fetchone()
        cursor.close()
        if result:
            if type == "citizen":
                return User(str(result["id_citizen"]), "citizen")
            else:
                return User(str(result["id_employee"]), "employee")
        return None

    def _get_first_name(self) -> str:
        """Return the first name of the user."""
        cursor = db_connection.cursor(dictionary=True)
        print(self.type)
        if self.type == "citizen":
            cursor.execute(
                "SELECT first_name FROM citizen WHERE id_citizen = %s",
                (self.id,),
            )
        else:
            cursor.execute(
                "SELECT first_name FROM employee WHERE id_employee = %s",
                (self.id,),
            )
        result = cursor.fetchone()
        cursor.close()
        print(f"Fetched first name for user {self.id}: {result}")
        if result:
            return result["first_name"]
        return "BRAK IMIENIA"

    def get_id(self) -> str:
        """Return the unique identifier for the user."""
        return self.id

    def __str__(self) -> str:
        return f"User(id={self.id}, type={self.type})"

    def __repr__(self) -> str:
        return f"User(id={self.id}, type={self.type})"


def load_user(user_id):
    user_type = flask.session.get("user_type")
    if not user_type:
        return None
    return User.get(user_id, user_type)


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


@app.route("/logowanie", methods=["GET", "POST"])
def login() -> flask.Response | str:
    """Renders the login page."""
    if flask.request.method == "POST":
        email: str = flask.request.form.get("email", "")
        password: str = flask.request.form.get("password", "")

        # check if e-mail and password are correct
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM citizen WHERE email = %s AND password = %s",
            (email, password),
        )
        user_record = cursor.fetchone()
        cursor.close()

        if user_record:
            user = User(str(user_record["id_citizen"]), "citizen")
            flask.session["user_type"] = "citizen"
            flask_login.login_user(user)
            print(f"Zalogowano użytkownika: {user}")
            return flask.redirect(flask.url_for("resident_dashboard"))
        else:
            return flask.render_template(
                "login.html", error="Nieprawidłowy e-mail lub hasło."
            )

    return flask.render_template("login.html")


@app.route("/logowanie/urzednik", methods=["GET", "POST"])
def login_staff() -> str:
    """Renders the official login page."""
    if flask.request.method == "POST":
        email: str = flask.request.form.get("email", "")
        password: str = flask.request.form.get("password", "")

        # check if e-mail and password are correct
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM employee WHERE email = %s AND password = %s",
            (email, password),
        )
        user_record = cursor.fetchone()
        cursor.close()

        if user_record:
            user = User(str(user_record["id_employee"]), "employee")
            flask.session["user_type"] = "employee"
            flask_login.login_user(user)
            print(f"Zalogowano urzędnika: {user}")
            return flask.redirect(flask.url_for("index"))
        else:
            return flask.render_template(
                "login_staff.html", error="Nieprawidłowy e-mail lub hasło."
            )
    return flask.render_template("login_staff.html")


@app.route("/wyloguj")
@flask_login.login_required
def logout() -> flask.Response:
    """Logs out the current user."""
    flask_login.logout_user()
    return flask.redirect(flask.url_for("index"))


@app.route("/rejestracja", methods=["GET", "POST"])
def signup() -> str:
    """Renders the signup page."""
    if flask.request.method == "POST":
        pesel: str = flask.request.form.get("pesel", "")
        first_name: str = flask.request.form.get("first_name", "")
        last_name: str = flask.request.form.get("last_name", "")
        phone_number: str = flask.request.form.get("phone_number", "")
        birth_date: str = flask.request.form.get("birth_date", "")
        reg_address: str = flask.request.form.get("reg_address", "")
        nip: str = flask.request.form.get("nip", "")
        email: str = flask.request.form.get("email", "")
        password: str = flask.request.form.get("password", "")

        print("WIELKIE DILDO")
        cursor = db_connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO citizen (pesel, first_name, last_name, phone_number, birth_date, reg_address, nip, email, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    pesel,
                    first_name,
                    last_name,
                    phone_number,
                    birth_date,
                    reg_address,
                    nip,
                    email,
                    password,
                ),
            )
        except mysql.connector.Error as err:
            print(f"Błąd podczas rejestracji użytkownika: {err}")
            cursor.close()
            return flask.render_template(
                "signup.html",
                error="Konto z podanym e-mailem lub PESEL już istnieje.",
            )
        db_connection.commit()
        new_user_id = cursor.lastrowid
        cursor.close()

        print(
            f"Zarejestrowano nowego użytkownika: ({new_user_id}) {first_name} {last_name}"
        )
        return flask.redirect(flask.url_for("login"))

    return flask.render_template("signup.html")


@app.route("/wniosek", methods=["GET", "POST"])
@flask_login.login_required
def application_form() -> str:
    """Renders the wniosek page."""
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM estate WHERE id_citizen = %s",
        (flask_login.current_user.id,),
    )
    estates = cursor.fetchall()
    cursor.close()
    print(estates)
    return flask.render_template("application_form.html", estates=estates)


@app.route("/panel/mieszkaniec")
@flask_login.login_required
def resident_dashboard() -> str:
    """Renders the panel for residents."""
    print(flask_login.current_user)
    if flask_login.current_user.type != "citizen":
        return flask.redirect(flask.url_for("index"))
    return flask.render_template("resident_dashboard.html")


@app.route("/panel/urzednik")
@flask_login.login_required
def staff_dashboard() -> str:
    """Renders the panel for staff."""
    print(flask_login.current_user)
    return "Panel urzędnika - w budowie"


if __name__ == "__main__":
    db_connection = get_db_connection()
    flask_login_manager.init_app(app)
    flask_login_manager.login_view = "login"
    flask_login_manager.user_loader(load_user)
    app.run(debug=True)
