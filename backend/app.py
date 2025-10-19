# -*- coding: utf-8 -*-
import flask
import flask_login
import mysql.connector
import os
import xml.etree.ElementTree as ET
from datetime import datetime

app: flask.Flask = flask.Flask(
    __name__, template_folder="../templates", static_folder="../static"
)
app.secret_key = "wielkiedildo33cm"


def compute_free_paid(applications):
    """Compute free_bags and paid_bags for each application in the list.

    Rule: one free bag per estate per calendar year. For each application we
    count prior bags in the same estate and year (strictly earlier by date or
    by id if same timestamp) and allocate up to 1 free bag in total per estate
    per year; remaining bags are paid.
    This mutates the dicts in-place (sets 'free_bags' and 'paid_bags').
    """
    if not applications:
        return

    # nothing to do here; we'll mutate or replace elements in-place
    sum_cur = db_connection.cursor(dictionary=True)
    try:
        # iterate by index so we can replace non-dict rows with dicts
        for idx, orig in enumerate(applications):
            # work on a mutable dict copy or the original dict
            if isinstance(orig, dict):
                a = orig
            else:
                try:
                    a = dict(orig)
                except Exception:
                    # fallback to a minimal dict view
                    a = {
                        "id_estate": getattr(orig, "id_estate", None),
                        "creation_date": getattr(orig, "creation_date", None),
                        "id_application": getattr(
                            orig, "id_application", None
                        ),
                        "bag_count": getattr(orig, "bag_count", 0),
                    }

            try:
                estate_id = a.get("id_estate")
                creation = a.get("creation_date")
                app_id = a.get("id_application")
                bag_count = int(a.get("bag_count") or 0)
            except Exception:
                estate_id = None
                creation = None
                app_id = None
                bag_count = 0

            if not estate_id or not creation:
                a["free_bags"] = 0
                a["paid_bags"] = bag_count
            else:
                sum_sql = (
                    "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                    "FROM application "
                    "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                    "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                )
                sum_cur.execute(
                    sum_sql, (estate_id, creation, creation, creation, app_id)
                )
                srow = sum_cur.fetchone()
                prior_bags = (
                    srow["prior_bags"] if srow and "prior_bags" in srow else 0
                )

                free_remaining = max(0, 1 - int(prior_bags or 0))
                free_for_this = min(free_remaining, bag_count)
                paid_for_this = bag_count - free_for_this

                a["free_bags"] = free_for_this
                a["paid_bags"] = paid_for_this

            # ensure the caller's list contains the mutated dict so callers see values
            if not isinstance(orig, dict):
                applications[idx] = a
    finally:
        sum_cur.close()


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


### XML export helpers (per-sector files)
XML_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "xml")


def _ensure_xml_dir():
    try:
        os.makedirs(XML_OUT_DIR, exist_ok=True)
    except Exception:
        # best-effort
        pass


def _sector_file_path(sector_id: int) -> str:
    _ensure_xml_dir()
    filename = f"sector_{sector_id}.xml"
    return os.path.join(XML_OUT_DIR, filename)


def _application_element_from_row(row: dict, attachments: list) -> ET.Element:
    app = ET.Element("application")
    app.set("id", str(row.get("id_application") or ""))
    # metadata attributes
    if row.get("creation_date"):
        app.set("created", str(row.get("creation_date")))
    # basic fields
    def sub(tag, text):
        el = ET.SubElement(app, tag)
        el.text = "" if text is None else str(text)
        return el

    # applicant (include extra fields: pesel, nip, reg_address, phone_number, birth_date, email)
    applicant = ET.SubElement(app, "applicant")
    for t in ("first_name", "last_name", "email", "phone_number", "pesel", "nip", "reg_address", "birth_date"):
        v = row.get(t)
        el = ET.SubElement(applicant, t)
        el.text = "" if v is None else str(v)

    # estate
    estate = ET.SubElement(app, "estate")
    for t in ("street", "building_number", "apartment_number", "postal_code", "city", "id_estate", "id_sector"):
        v = row.get(t)
        el = ET.SubElement(estate, t)
        el.text = "" if v is None else str(v)

    # application details
    sub("bag_count", row.get("bag_count") or 0)
    sub("free_bags", row.get("free_bags") if row.get("free_bags") is not None else 0)
    sub("paid_bags", row.get("paid_bags") if row.get("paid_bags") is not None else 0)
    sub("bag_arrival_date", row.get("bag_arrival_date") or "")
    sub("bag_depart_date", row.get("bag_depart_date") or "")
    sub("status", row.get("status") or "")
    sub("notes", row.get("notes") or "")

    # attachments
    atts_el = ET.SubElement(app, "attachments")
    for att in attachments:
        ael = ET.SubElement(atts_el, "attachment")
        ael.set("id", str(att.get("id_attachment")))
        fn = ET.SubElement(ael, "file_name")
        fn.text = att.get("file_name") or ""
        ft = ET.SubElement(ael, "file_type")
        ft.text = att.get("file_type") or ""
        # include download URL relative to the app
        dl = ET.SubElement(ael, "download_url")
        dl.text = f"/attachment/{att.get('id_attachment')}" if att.get("id_attachment") else ""

    return app


def _write_sector_application(row: dict, attachments: list):
    """Write or update application element in sector XML file."""
    sector_id = row.get("id_sector") or 0
    path = _sector_file_path(sector_id)

    # load or create root
    if os.path.exists(path):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except Exception:
            # corrupt file? start fresh
            root = ET.Element("applications")
            tree = ET.ElementTree(root)
    else:
        root = ET.Element("applications")
        tree = ET.ElementTree(root)

    app_id = str(row.get("id_application"))
    # find existing element
    existing = None
    for el in root.findall("application"):
        if el.get("id") == app_id:
            existing = el
            break

    new_el = _application_element_from_row(row, attachments)

    if existing is not None:
        # replace existing element
        root.remove(existing)
    root.append(new_el)

    # write atomically
    tmp = path + ".tmp"
    try:
        tree.write(tmp, encoding="utf-8", xml_declaration=True)
        os.replace(tmp, path)
    except Exception:
        try:
            tree.write(path, encoding="utf-8", xml_declaration=True)
        except Exception:
            pass


def _mark_application_revoked(app_id: int):
    """Mark the application as revoked in any sector XML file where it exists."""
    _ensure_xml_dir()
    # scan files in XML_OUT_DIR
    for fname in os.listdir(XML_OUT_DIR):
        if not fname.endswith(".xml"):
            continue
        path = os.path.join(XML_OUT_DIR, fname)
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except Exception:
            continue

        changed = False
        for el in root.findall("application"):
            if el.get("id") == str(app_id):
                # set attribute revoked and add revoked child with timestamp
                if el.get("revoked") == "true":
                    continue
                el.set("revoked", "true")
                rev = ET.SubElement(el, "revoked_at")
                rev.text = datetime.utcnow().isoformat()
                changed = True

        if changed:
            tmp = path + ".tmp"
            try:
                tree.write(tmp, encoding="utf-8", xml_declaration=True)
                os.replace(tmp, path)
            except Exception:
                try:
                    tree.write(path, encoding="utf-8", xml_declaration=True)
                except Exception:
                    pass


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
            return flask.redirect(flask.url_for("staff_dashboard"))
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

    if flask.request.method == "POST":
        # handle form submission: insert estate if new, then application, then attachment
        form = flask.request.form
        files = flask.request.files

        id_estate = form.get("id_estate")
        # if adding new estate, insert into estate table
        if id_estate == "new":
            new_type = form.get("new_est_type") or ""
            # map Polish 'mieszkanie'/'dom' to DB enum 'apartment'/'house'
            estate_type = "apartment" if new_type == "mieszkanie" else "house"
            postal = form.get("new_est_postal") or ""
            city = "Płock"
            street = form.get("new_est_street") or ""
            building = form.get("new_est_building") or ""
            apartment_num = form.get("new_est_apartment") or None

            try:
                sector_val = form.get("new_est_osiedle") or "1"
                try:
                    id_sector = int(sector_val)
                except Exception:
                    id_sector = 1

                cur = db_connection.cursor()
                cur.execute(
                    "INSERT INTO estate (id_citizen, id_sector, estate_type, postal_code, city, street, building_number, apartment_number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        flask_login.current_user.id,
                        id_sector,
                        estate_type,
                        postal,
                        city,
                        street,
                        building,
                        apartment_num,
                    ),
                )
                db_connection.commit()
                id_estate = cur.lastrowid
                cur.close()
            except mysql.connector.Error as err:
                print("Error inserting estate:", err)
                return flask.render_template(
                    "application_form.html",
                    estates=[],
                    error="Błąd przy dodawaniu nieruchomości",
                )

        # now insert application
        try:
            cur = db_connection.cursor()
            bag_arrival = form.get("bag_arrival_date") or None
            bag_depart = form.get("bag_depart_date") or None
            notes = form.get("notes") or None
            # parse bag_count from form, enforce integer >= 1
            bag_count_raw = form.get("bag_count")
            try:
                bag_count = (
                    int(bag_count_raw) if bag_count_raw is not None else 1
                )
            except Exception:
                bag_count = 1
            if bag_count < 1:
                bag_count = 1
            cur.execute(
                "INSERT INTO application (id_estate, id_citizen, status, bag_count, bag_arrival_date, bag_depart_date, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    id_estate,
                    flask_login.current_user.id,
                    "awaiting",
                    bag_count,
                    bag_arrival,
                    bag_depart,
                    notes,
                ),
            )
            db_connection.commit()
            id_application = cur.lastrowid
            cur.close()
        except mysql.connector.Error as err:
            print("Error inserting application:", err)
            return flask.render_template(
                "application_form.html",
                estates=[],
                error="Błąd przy tworzeniu wniosku",
            )

        # handle attachment file (if provided)
        if "new_est_attachment" in files:
            f = files["new_est_attachment"]
            if f and f.filename:
                data = f.read()
                try:
                    cur = db_connection.cursor()
                    cur.execute(
                        "INSERT INTO attachment (id_application, file_name, file_type, file_data) VALUES (%s, %s, %s, %s)",
                        (
                            id_application,
                            f.filename,
                            f.content_type or "",
                            data,
                        ),
                    )
                    db_connection.commit()
                    cur.close()
                except mysql.connector.Error as err:
                    print("Error inserting attachment:", err)
                    # continue without failing the whole request

        return flask.redirect(flask.url_for("resident_dashboard"))

    # GET: render form
    cursor.execute(
        "SELECT * FROM estate WHERE id_citizen = %s",
        (flask_login.current_user.id,),
    )
    estates = cursor.fetchall()
    cursor.close()
    return flask.render_template("application_form.html", estates=estates)


@app.route("/panel/mieszkaniec")
@flask_login.login_required
def resident_dashboard() -> str:
    """Renders the panel for residents."""
    print(flask_login.current_user)
    if flask_login.current_user.type != "citizen":
        return flask.redirect(flask.url_for("index"))
    # pagination and filters
    try:
        page = int(flask.request.args.get("page", "1"))
    except ValueError:
        page = 1
    per_page = 25
    offset = (page - 1) * per_page

    status_filter = flask.request.args.get("status")
    q = flask.request.args.get("q", "").strip()

    cur = db_connection.cursor(dictionary=True)
    try:
        # build where clauses
        where_clauses = ["a.id_citizen = %s"]
        params = [flask_login.current_user.id]
        if status_filter:
            where_clauses.append("a.status = %s")
            params.append(status_filter)
        if q:
            where_clauses.append(
                "(e.street LIKE %s OR e.building_number LIKE %s OR e.apartment_number LIKE %s)"
            )
            likeq = f"%{q}%"
            params.extend([likeq, likeq, likeq])

        where_sql = " AND ".join(where_clauses)

        # total count
        count_sql = f"SELECT COUNT(*) as cnt FROM application a LEFT JOIN estate e ON a.id_estate = e.id_estate WHERE {where_sql}"
        cur.execute(count_sql, tuple(params))
        row = cur.fetchone()
        total = row["cnt"] if row and "cnt" in row else 0

        # paginated fetch
        fetch_sql = f"""
            SELECT a.*, e.id_sector, s.managing_company, s.company_address, s.company_hours, e.street, e.building_number, e.apartment_number
            FROM application a
            LEFT JOIN estate e ON a.id_estate = e.id_estate
            LEFT JOIN sector s ON e.id_sector = s.id_sector
            WHERE {where_sql}
            ORDER BY a.creation_date DESC
            LIMIT %s OFFSET %s
            """
        fetch_params = tuple(params + [per_page, offset])
        cur.execute(fetch_sql, fetch_params)
        applications = cur.fetchall()

        # attach computed free/paid bag counts so staff can see which bags are paid
        if applications:
            try:
                applications = [dict(a) for a in applications]
            except Exception:
                pass

            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    estate_id = a.get("id_estate")
                    creation = a.get("creation_date")
                    app_id = a.get("id_application")
                    bag_count = int(a.get("bag_count") or 0)

                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    a["free_bags"] = free_for_this
                    a["paid_bags"] = paid_for_this
            finally:
                sum_cur.close()

        # ensure applications are plain dicts so templates can read computed keys
        if applications:
            try:
                applications = [dict(a) for a in applications]
            except Exception:
                pass

        # compute free/paid bags for staff view (one free bag per estate per calendar year)
        if applications:
            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    estate_id = a.get("id_estate")
                    creation = a.get("creation_date")
                    app_id = a.get("id_application")
                    bag_count = int(a.get("bag_count") or 0)

                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    a["free_bags"] = free_for_this
                    a["paid_bags"] = paid_for_this
            finally:
                sum_cur.close()

        # normalize rows to plain dicts so we can attach computed keys
        if applications:
            try:
                applications = [dict(a) for a in applications]
            except Exception:
                # if conversion fails, keep original
                pass

        # Compute paid/free bags per application (one free bag per estate per calendar year)
        if applications:
            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    estate_id = (
                        a.get("id_estate")
                        if isinstance(a, dict)
                        else a["id_estate"]
                    )
                    creation = (
                        a.get("creation_date")
                        if isinstance(a, dict)
                        else a["creation_date"]
                    )
                    app_id = (
                        a.get("id_application")
                        if isinstance(a, dict)
                        else a["id_application"]
                    )
                    bag_count = int(
                        (
                            a.get("bag_count")
                            if isinstance(a, dict)
                            else a["bag_count"]
                        )
                        or 0
                    )

                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    # attach values
                    try:
                        a["free_bags"] = free_for_this
                        a["paid_bags"] = paid_for_this
                    except Exception:
                        # ignore if row type isn't mutable
                        pass
            finally:
                sum_cur.close()

        # Compute paid/free bags per application (one free bag per estate per calendar year)
        if applications:
            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    try:
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = int(a.get("bag_count") or 0)
                    except Exception:
                        # fallback defaults
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = a.get("bag_count") or 0

                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    a["free_bags"] = free_for_this
                    a["paid_bags"] = paid_for_this
            finally:
                sum_cur.close()

        # Compute paid/free bags per application (one free bag per estate per calendar year)
        if applications:
            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    try:
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = int(a.get("bag_count") or 0)
                    except Exception:
                        # fallback defaults
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = a.get("bag_count") or 0

                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    a["free_bags"] = free_for_this
                    a["paid_bags"] = paid_for_this
            finally:
                sum_cur.close()

        # Compute paid/free bags per application (one free bag per estate per calendar year)
        if applications:
            sum_cur = db_connection.cursor(dictionary=True)
            try:
                for a in applications:
                    try:
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = int(a.get("bag_count") or 0)
                    except Exception:
                        # fallback defaults
                        estate_id = a.get("id_estate")
                        creation = a.get("creation_date")
                        app_id = a.get("id_application")
                        bag_count = a.get("bag_count") or 0

                    # prior bags in same calendar year and earlier than this application
                    sum_sql = (
                        "SELECT COALESCE(SUM(bag_count),0) as prior_bags "
                        "FROM application "
                        "WHERE id_estate = %s AND YEAR(creation_date) = YEAR(%s) "
                        "AND (creation_date < %s OR (creation_date = %s AND id_application < %s))"
                    )
                    sum_cur.execute(
                        sum_sql,
                        (estate_id, creation, creation, creation, app_id),
                    )
                    srow = sum_cur.fetchone()
                    prior_bags = (
                        srow["prior_bags"]
                        if srow and "prior_bags" in srow
                        else 0
                    )

                    free_remaining = max(0, 1 - int(prior_bags or 0))
                    free_for_this = min(free_remaining, bag_count)
                    paid_for_this = bag_count - free_for_this

                    a["free_bags"] = free_for_this
                    a["paid_bags"] = paid_for_this
            finally:
                sum_cur.close()

        # fetch attachments for listed applications
        app_ids = (
            [a["id_application"] for a in applications] if applications else []
        )
        attachments_map = {}
        if app_ids:
            format_strings = ",".join(["%s"] * len(app_ids))
            cur.execute(
                f"SELECT id_attachment, id_application, file_name, file_type FROM attachment WHERE id_application IN ({format_strings})",
                tuple(app_ids),
            )
            atts = cur.fetchall()
            for att in atts:
                attachments_map.setdefault(att["id_application"], []).append(
                    att
                )
    finally:
        cur.close()

    # compute free/paid bags for resident view
    compute_free_paid(applications)

    total_pages = max(1, (total + per_page - 1) // per_page)

    return flask.render_template(
        "resident_dashboard.html",
        applications=applications,
        attachments_map=attachments_map,
        page=page,
        total_pages=total_pages,
        status_filter=status_filter,
        q=q,
    )
    # Serve attachment bytes endpoint


@app.route("/attachment/<int:attachment_id>")
@flask_login.login_required
def serve_attachment(attachment_id: int):
    """Return raw attachment bytes with authorization checks."""
    cur = db_connection.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT att.file_name, att.file_type, att.file_data, app.id_citizen
            FROM attachment att
            JOIN application app ON att.id_application = app.id_application
            WHERE att.id_attachment = %s
            """,
            (attachment_id,),
        )
        row = cur.fetchone()
        if not row:
            return flask.abort(404)

        # Authorization: allow if current user is the owner (citizen) or an employee
        owner_id = row["id_citizen"] if "id_citizen" in row else None
        if flask_login.current_user.type == "citizen":
            if str(owner_id) != str(flask_login.current_user.id):
                return flask.abort(403)

        file_name = row["file_name"] if "file_name" in row else "attachment"
        file_type = (
            row["file_type"]
            if "file_type" in row
            else "application/octet-stream"
        )
        data = row["file_data"]

        resp = flask.make_response(data)
        resp.headers["Content-Type"] = file_type
        # suggest inline for images and PDFs, otherwise force download
        if file_type.startswith("image/") or file_type == "application/pdf":
            disposition = f'inline; filename="{file_name}"'
        else:
            disposition = f'attachment; filename="{file_name}"'
        resp.headers["Content-Disposition"] = disposition
        return resp
    finally:
        cur.close()


@app.route("/attachment/view/<int:attachment_id>")
@flask_login.login_required
def attachment_view(attachment_id: int) -> str:
    """Render a small page showing the attachment preview and a download button.

    This endpoint only returns metadata and a small HTML page; the actual bytes
    are served by `serve_attachment` (which enforces authorization).
    """
    cur = db_connection.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT att.id_attachment, att.file_name, att.file_type, app.id_citizen
            FROM attachment att
            JOIN application app ON att.id_application = app.id_application
            WHERE att.id_attachment = %s
            """,
            (attachment_id,),
        )
        row = cur.fetchone()
        if not row:
            return flask.abort(404)

        owner_id = row["id_citizen"] if "id_citizen" in row else None
        if flask_login.current_user.type == "citizen":
            if str(owner_id) != str(flask_login.current_user.id):
                return flask.abort(403)

        return flask.render_template(
            "attachment_view.html",
            attachment_id=row["id_attachment"],
            file_name=row["file_name"],
            file_type=row["file_type"],
        )
    finally:
        cur.close()


@app.route("/citizen/<int:citizen_id>/info")
@flask_login.login_required
def citizen_info(citizen_id: int):
    """Return basic citizen info (PESEL) for employees as JSON."""
    # only employees may fetch PESELs here
    if flask_login.current_user.type == "citizen":
        return flask.abort(403)

    cur = db_connection.cursor(dictionary=True)
    try:
        # select all citizen columns except password
        cur.execute(
            "SELECT id_citizen, pesel, first_name, last_name, phone_number, birth_date, reg_address, nip, creation_date, email FROM citizen WHERE id_citizen = %s",
            (citizen_id,),
        )
        row = cur.fetchone()
        if not row:
            return flask.jsonify({"ok": False, "error": "not_found"}), 404

        return flask.jsonify(
            {
                "ok": True,
                "id": row.get("id_citizen"),
                "pesel": row.get("pesel"),
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "phone_number": row.get("phone_number"),
                "birth_date": row.get("birth_date"),
                "reg_address": row.get("reg_address"),
                "nip": row.get("nip"),
                "creation_date": row.get("creation_date"),
                "email": row.get("email"),
            }
        )
    finally:
        cur.close()


@app.route("/panel/urzednik")
@flask_login.login_required
def staff_dashboard() -> str:
    """Renders the panel for staff - list all applications (paginated).

    Only users with type != 'citizen' are allowed (employees).
    """
    if flask_login.current_user.type == "citizen":
        return flask.redirect(flask.url_for("index"))

    try:
        page = int(flask.request.args.get("page", "1"))
    except ValueError:
        page = 1
    per_page = 25
    offset = (page - 1) * per_page

    # filters
    status_filter = flask.request.args.get("status")
    q = flask.request.args.get("q", "").strip()

    cur = db_connection.cursor(dictionary=True)
    try:
        where_clauses = []
        params = []
        if status_filter:
            where_clauses.append("a.status = %s")
            params.append(status_filter)
        if q:
            # search in address and citizen fields
            where_clauses.append(
                "(e.street LIKE %s OR e.building_number LIKE %s OR e.apartment_number LIKE %s OR c.first_name LIKE %s OR c.last_name LIKE %s OR c.email LIKE %s)"
            )
            likeq = f"%{q}%"
            params.extend([likeq, likeq, likeq, likeq, likeq, likeq])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1"

        # total count
        count_sql = f"SELECT COUNT(*) as cnt FROM application a LEFT JOIN estate e ON a.id_estate = e.id_estate LEFT JOIN citizen c ON a.id_citizen = c.id_citizen WHERE {where_sql}"
        cur.execute(count_sql, tuple(params))
        row = cur.fetchone()
        total = row["cnt"] if row and "cnt" in row else 0

        # paginated fetch: include citizen info and estate address
        fetch_sql = f"""
            SELECT a.*, e.id_sector, e.street, e.building_number, e.apartment_number, s.managing_company, s.company_address, s.company_hours, c.first_name, c.last_name, c.email
            FROM application a
            LEFT JOIN estate e ON a.id_estate = e.id_estate
            LEFT JOIN sector s ON e.id_sector = s.id_sector
            LEFT JOIN citizen c ON a.id_citizen = c.id_citizen
            WHERE {where_sql}
            ORDER BY a.creation_date DESC
            LIMIT %s OFFSET %s
            """
        fetch_params = tuple(params + [per_page, offset])
        cur.execute(fetch_sql, fetch_params)
        applications = cur.fetchall()

        # fetch attachments for the listed applications
        app_ids = (
            [a["id_application"] for a in applications] if applications else []
        )
        attachments_map = {}
        if app_ids:
            format_strings = ",".join(["%s"] * len(app_ids))
            cur.execute(
                f"SELECT id_attachment, id_application, file_name, file_type FROM attachment WHERE id_application IN ({format_strings})",
                tuple(app_ids),
            )
            atts = cur.fetchall()
            for att in atts:
                attachments_map.setdefault(att["id_application"], []).append(
                    att
                )
    finally:
        cur.close()

    total_pages = max(1, (total + per_page - 1) // per_page)

    # compute free/paid bags for staff view and ensure keys exist
    compute_free_paid(applications)
    if applications:
        try:
            for a in applications:
                if isinstance(a, dict):
                    a.setdefault("free_bags", 0)
                    a.setdefault("paid_bags", 0)
        except Exception:
            pass

    return flask.render_template(
        "staff_dashboard.html",
        applications=applications,
        attachments_map=attachments_map,
        page=page,
        total_pages=total_pages,
        status_filter=status_filter,
        q=q,
    )


@app.route("/debug/staff_applications")
@flask_login.login_required
def debug_staff_applications():
    """Developer helper: return JSON list of staff applications with computed free/paid bags.

    Only employees (non-citizen) can access this. Designed for quick inspection during
    debugging; remove or protect in production.
    """
    if flask_login.current_user.type == "citizen":
        return flask.abort(403)

    cur = db_connection.cursor(dictionary=True)
    try:
        # fetch recent applications (limit to 100 for safety)
        cur.execute(
            """
            SELECT a.*, e.street, e.building_number, e.apartment_number, c.first_name, c.last_name, c.email
            FROM application a
            LEFT JOIN estate e ON a.id_estate = e.id_estate
            LEFT JOIN citizen c ON a.id_citizen = c.id_citizen
            ORDER BY a.creation_date DESC
            LIMIT 100
            """
        )
        apps = cur.fetchall()
        # ensure list and compute free/paid
        compute_free_paid(apps)
        # normalize and pick a few fields for clarity
        out = []
        for a in apps:
            try:
                row = dict(a)
            except Exception:
                row = a
            out.append(
                {
                    "id_application": row.get("id_application"),
                    "id_estate": row.get("id_estate"),
                    "bag_count": int(row.get("bag_count") or 0),
                    "free_bags": int(row.get("free_bags") or 0),
                    "paid_bags": int(row.get("paid_bags") or 0),
                    "creation_date": str(row.get("creation_date")),
                    "street": row.get("street"),
                    "building_number": row.get("building_number"),
                    "apartment_number": row.get("apartment_number"),
                    "first_name": row.get("first_name"),
                    "last_name": row.get("last_name"),
                }
            )
        return flask.jsonify(out)
    finally:
        cur.close()


@app.route("/application/<int:app_id>/decide", methods=["POST"])
@flask_login.login_required
def decide_application(app_id: int):
    """Allow an employee to approve or decline an application.

    Expects form field 'action' with values 'approve' or 'decline'. Only
    non-citizen (employee) users can perform this action.
    """
    if flask_login.current_user.type == "citizen":
        return flask.abort(403)

    action = flask.request.form.get("action")
    if action not in ("approve", "decline"):
        # invalid action
        if flask.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return flask.jsonify({"ok": False, "error": "invalid_action"}), 400
        return flask.redirect(flask.url_for("staff_dashboard"))

    new_status = "approved" if action == "approve" else "declined"

    # check current status to avoid useless transitions
    cur = db_connection.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT status FROM application WHERE id_application = %s",
            (app_id,),
        )
        row = cur.fetchone()
        if not row:
            if (
                flask.request.headers.get("X-Requested-With")
                == "XMLHttpRequest"
            ):
                return flask.make_response(
                    flask.jsonify({"ok": False, "error": "not_found"}), 404
                )
            return flask.redirect(flask.url_for("staff_dashboard"))

        current_status = row["status"]
        if current_status == new_status:
            # no-op
            if (
                flask.request.headers.get("X-Requested-With")
                == "XMLHttpRequest"
            ):
                return flask.make_response(
                    flask.jsonify(
                        {
                            "ok": False,
                            "error": "no_change",
                            "status": current_status,
                        }
                    ),
                    409,
                )
            return flask.redirect(flask.url_for("staff_dashboard"))
    finally:
        cur.close()

    # perform update
    cur2 = db_connection.cursor()
    try:
        cur2.execute(
            "UPDATE application SET status = %s WHERE id_application = %s",
            (new_status, app_id),
        )
        db_connection.commit()
        # after successful update, export to per-sector XML or mark revoked
        try:
            cur3 = db_connection.cursor(dictionary=True)
            try:
                cur3.execute(
                    "SELECT a.*, e.id_sector, e.street, e.building_number, e.apartment_number, c.* FROM application a LEFT JOIN estate e ON a.id_estate = e.id_estate LEFT JOIN citizen c ON a.id_citizen = c.id_citizen WHERE a.id_application = %s",
                    (app_id,),
                )
                row = cur3.fetchone()
                # fetch attachments
                cur3.execute(
                    "SELECT id_attachment, id_application, file_name, file_type FROM attachment WHERE id_application = %s",
                    (app_id,),
                )
                atts = cur3.fetchall()
                if row:
                    if new_status == 'approved':
                        try:
                            _write_sector_application(row, atts or [])
                        except Exception as e:
                            print("XML write error:", e)
                    else:
                        try:
                            _mark_application_revoked(app_id)
                        except Exception as e:
                            print("XML revoke error:", e)
            finally:
                cur3.close()
        except Exception:
            # ignore xml export errors for now
            pass
    except mysql.connector.Error as err:
        print("Error updating application status:", err)
        if flask.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return flask.make_response(
                flask.jsonify({"ok": False, "error": "db_error"}), 500
            )
    finally:
        cur2.close()

    # AJAX clients receive JSON; normal form posts are redirected back
    if flask.request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return flask.jsonify({"ok": True, "new_status": new_status})

    page = flask.request.form.get("page") or flask.request.args.get("page")
    if page:
        return flask.redirect(
            flask.url_for("staff_dashboard") + f"?page={page}"
        )
    return flask.redirect(flask.url_for("staff_dashboard"))


@app.route("/application/<int:app_id>/print")
@flask_login.login_required
def application_print(app_id: int):
    """Render a printer-friendly page for an application.

    Employees may print any application. Citizens may print only their
    own application (match on id_citizen).
    """
    cur = db_connection.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT a.*, e.street, e.building_number, e.apartment_number, c.* FROM application a LEFT JOIN estate e ON a.id_estate = e.id_estate LEFT JOIN citizen c ON a.id_citizen = c.id_citizen WHERE a.id_application = %s",
            (app_id,),
        )
        row = cur.fetchone()
        if not row:
            return flask.abort(404)

        # if current user is a citizen, ensure they own this application
        if flask_login.current_user.type == "citizen":
            try:
                cur_user_id = int(flask_login.current_user.get_id())
            except Exception:
                return flask.abort(403)
            # row['id_citizen'] may be None or string/number; normalize to int when possible
            try:
                owner_id = int(row.get("id_citizen") or -1)
            except Exception:
                owner_id = -1
            if owner_id != cur_user_id:
                return flask.abort(403)

        # prepare a clean dict for template
        app_data = dict(row)
        return flask.render_template(
            "application_print.html", application=app_data
        )
    finally:
        cur.close()


if __name__ == "__main__":
    db_connection = get_db_connection()
    flask_login_manager = flask_login.LoginManager()
    flask_login_manager.init_app(app)
    flask_login_manager.login_view = "login"
    flask_login_manager.user_loader(load_user)
    app.run(debug=True)
