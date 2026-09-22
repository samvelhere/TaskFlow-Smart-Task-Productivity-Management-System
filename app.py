from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFError
from mysql.connector import pooling
import threading
import time
import os
import logging


load_dotenv()


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


app = Flask(__name__)

app.secret_key = os.environ["SECRET_KEY"]

app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get(
        "SESSION_COOKIE_SECURE",
        "false"
    ).lower() == "true",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)


csrf = CSRFProtect(app)


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        error_code=404,
        error_title="Page not found",
        error_message="The page you are looking for does not exist or has been moved."
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template(
        "error.html",
        error_code=500,
        error_title="Something went wrong",
        error_message="TaskFlow could not complete this request. Please try again."
    ), 500


@app.errorhandler(CSRFError)
def csrf_error(error):
    return render_template(
        "error.html",
        error_code=400,
        error_title="Request could not be verified",
        error_message="Your form session has expired or the security token is invalid. Refresh the page and try again."
    ), 400


@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "error.html",
        error_code=403,
        error_title="Access not available",
        error_message="You do not have permission to access this page."
    ), 403


@app.errorhandler(405)
def method_not_allowed(error):
    return render_template(
        "error.html",
        error_code=405,
        error_title="Action not available",
        error_message="That action is not available for this page. Return to the dashboard and try again."
    ), 405


DELETE_REASONS = {
    "completed_elsewhere": "Task completed elsewhere",
    "no_longer_needed": "No longer needed",
    "duplicate": "Duplicate task",
    "created_by_mistake": "Created by mistake",
    "priority_changed": "Changed priority",
    "not_relevant": "Not relevant anymore"
}


ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
    "urgent"
}


ALLOWED_STATUSES = {
    "not_started",
    "in_progress",
    "completed",
    "overdue"
}


db_pool = pooling.MySQLConnectionPool(
    pool_name="taskflow_pool",
    pool_size=10,
    pool_reset_session=True,
    host=os.environ["MYSQL_HOST"],
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"]
)


def mysql_db():
    return db_pool.get_connection()


def login_required():
    return "user_id" in session


def log_activity(
    cursor,
    user_id,
    action_type,
    entity_type,
    entity_id=None,
    title="",
    details=None
):
    cursor.execute(
        """
        INSERT INTO activity_logs
        (
            user_id,
            action_type,
            entity_type,
            entity_id,
            title,
            details
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            user_id,
            action_type,
            entity_type,
            entity_id,
            title,
            details
        )
    )


def ensure_notification_table():
    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                task_id INT NULL,
                notification_type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NULL,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME NULL,
                INDEX idx_notifications_user_created (
                    user_id,
                    created_at
                ),
                INDEX idx_notifications_user_read (
                    user_id,
                    is_read,
                    created_at
                ),
                CONSTRAINT fk_notifications_user
                    FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_notifications_task
                    FOREIGN KEY (task_id)
                    REFERENCES tasks(id)
                    ON DELETE SET NULL
            )
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Failed to create notifications table")
        raise
    finally:
        cursor.close()
        connection.close()


def create_notification(
    cursor,
    user_id,
    notification_type,
    title,
    message=None,
    task_id=None
):
    cursor.execute(
        """
        INSERT INTO notifications
        (
            user_id,
            task_id,
            notification_type,
            title,
            message
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            user_id,
            task_id,
            notification_type,
            title,
            message
        )
    )


def ensure_activity_table():
    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                entity_type VARCHAR(30) NOT NULL,
                entity_id INT NULL,
                title VARCHAR(1000) NOT NULL,
                details TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_activity_user_created (
                    user_id,
                    created_at
                ),
                CONSTRAINT fk_activity_user
                    FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to create activity_logs table")
        raise

    finally:
        cursor.close()
        connection.close()


def ensure_subtask_due_date_column():
    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'subtasks'
              AND column_name = 'due_date'
            """
        )

        (column_count,) = cursor.fetchone()

        if column_count == 0:
            cursor.execute(
                """
                ALTER TABLE subtasks
                ADD COLUMN due_date DATE NULL
                """
            )
            connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to add due_date column to subtasks")
        raise

    finally:
        cursor.close()
        connection.close()


@app.route("/")
def hello():

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        if not user:
            session.clear()
            return redirect(url_for("login"))

        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at,
                completed_at,
                notification,
                created_at
            FROM tasks
            WHERE user_id = %s
            ORDER BY
                CASE
                    WHEN status = 'completed' THEN 2
                    ELSE 1
                END,
                due_date ASC,
                id DESC
            """,
            (session["user_id"],)
        )

        tasks = cursor.fetchall()

        for task in tasks:

            cursor.execute(
                """
                SELECT
                    id,
                    task_id,
                    title,
                    status,
                    due_date,
                    created_at,
                    completed_at
                FROM subtasks
                WHERE task_id = %s
                ORDER BY id ASC
                """,
                (task["id"],)
            )

            subtasks = cursor.fetchall()

            task["subtasks"] = subtasks

            total_subtasks = len(subtasks)

            completed_subtasks = sum(
                1
                for subtask in subtasks
                if subtask["status"] == "completed"
            )

            task["total_subtasks"] = total_subtasks
            task["completed_subtasks"] = completed_subtasks

            if total_subtasks:
                task["subtask_progress"] = round(
                    (completed_subtasks / total_subtasks) * 100
                )
            else:
                task["subtask_progress"] = 0

        return render_template(
            "demo.html",
            tasks=tasks,
            user=user,
            today=date.today().isoformat()
        )

    except Exception:
        logger.exception("Failed to load dashboard")
        return render_template(
            "demo.html",
            tasks=[],
            user={"name": "TaskFlow", "email": ""},
            today=date.today().isoformat(),
            error="We could not load your tasks right now. Please refresh and try again."
        ), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.", name=name, email=email), 400

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email), 400

    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email), 400

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return render_template("register.html", error="An account with this email already exists.", name=name, email=email), 400

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password_hash
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                name,
                email,
                password_hash
            )
        )

        user_id = cursor.lastrowid

        log_activity(
            cursor,
            user_id,
            "registered",
            "account",
            user_id,
            "Created account",
            "TaskFlow account registered"
        )

        connection.commit()

        session.clear()
        session["user_id"] = user_id

        return redirect(url_for("hello"))

    except Exception:
        connection.rollback()
        logger.exception("User registration failed")
        return render_template("register.html", error="We could not create your account right now. Please try again.", name=name, email=email), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/login", methods=["GET", "POST"])
def login():

    if login_required():
        return redirect(url_for("hello"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.", email=email), 400

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user:
            return render_template("login.html", error="Invalid email or password.", email=email), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return render_template("login.html", error="Invalid email or password.", email=email), 401

        log_activity(
            cursor,
            user["id"],
            "logged_in",
            "account",
            user["id"],
            "Logged in",
            "Successful login"
        )

        connection.commit()

        session.clear()
        session["user_id"] = user["id"]

        return redirect(url_for("hello"))

    except Exception:
        connection.rollback()
        logger.exception("Login failed")
        return render_template("login.html", error="We could not sign you in right now. Please try again.", email=email), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/logout")
def logout():

    user_id = session.get("user_id")

    if user_id:

        connection = mysql_db()
        cursor = connection.cursor()

        try:

            log_activity(
                cursor,
                user_id,
                "logged_out",
                "account",
                user_id,
                "Logged out",
                "User logged out of TaskFlow"
            )

            connection.commit()

        except Exception:
            connection.rollback()
            logger.exception("Failed to log logout activity")

        finally:
            cursor.close()
            connection.close()

    session.clear()

    return redirect(url_for("login"))


@app.route("/add", methods=["POST"])
def add():

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    priority = request.form.get(
        "priority",
        "medium"
    ).strip().lower()

    status = request.form.get(
        "status",
        "not_started"
    ).strip().lower()

    start_date_string = request.form.get(
        "start_date",
        ""
    ).strip()

    due_date_string = request.form.get(
        "due_date",
        ""
    ).strip()

    reminder_date = request.form.get(
        "reminder_date",
        ""
    ).strip()

    reminder_time = request.form.get(
        "reminder_time",
        ""
    ).strip()

    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("hello"))

    if priority not in ALLOWED_PRIORITIES:
        flash("Please choose a valid priority.", "error")
        return redirect(url_for("hello"))

    if status not in ALLOWED_STATUSES:
        status = "not_started"

    try:

        start_date = (
            datetime.strptime(
                start_date_string,
                "%Y-%m-%d"
            ).date()
            if start_date_string
            else None
        )

        due_date = (
            datetime.strptime(
                due_date_string,
                "%Y-%m-%d"
            ).date()
            if due_date_string
            else None
        )

    except ValueError:
        flash("Please enter a valid start date and due date.", "error")
        return redirect(url_for("hello"))

    if start_date and due_date and due_date < start_date:
        flash("Due date cannot be before start date.", "error")
        return redirect(url_for("hello"))

    reminder_at = None

    if reminder_date or reminder_time:

        if not reminder_date or not reminder_time:
            flash("Both reminder date and reminder time are required.", "error")
            return redirect(url_for("hello"))

        try:

            reminder_at = datetime.strptime(
                f"{reminder_date} {reminder_time}",
                "%Y-%m-%d %H:%M"
            )

        except ValueError:
            flash("Please enter a valid reminder date and time.", "error")
            return redirect(url_for("hello"))

        if reminder_at < datetime.now():
            flash("Reminder cannot be in the past.", "error")
            return redirect(url_for("hello"))

    completed_at = (
        datetime.now()
        if status == "completed"
        else None
    )

    connection = mysql_db()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO tasks
            (
                user_id,
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at,
                completed_at,
                notification
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                FALSE
            )
            """,
            (
                session["user_id"],
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at,
                completed_at
            )
        )

        task_id = cursor.lastrowid

        details = (
            f"Priority: {priority.replace('_', ' ').title()}"
        )

        if due_date:
            details += (
                f" | Due date: "
                f"{due_date.strftime('%d %b %Y')}"
            )

        log_activity(
            cursor,
            session["user_id"],
            "created",
            "task",
            task_id,
            "Created task",
            f"{title} | {details}"
        )

        connection.commit()

    except Exception:

        connection.rollback()
        logger.exception("Failed to create task")
        flash("We could not create the task because of a database problem. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task added successfully.", "success")
    return redirect(url_for("hello"))


@app.route("/start/<int:task_id>", methods=["POST"])
def start_task(task_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                status
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        if task["status"] == "completed":
            return redirect(url_for("hello"))

        cursor.execute(
            """
            UPDATE tasks
            SET status = 'in_progress'
            WHERE id = %s
              AND user_id = %s
              AND status != 'completed'
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        log_activity(
            cursor,
            session["user_id"],
            "started",
            "task",
            task_id,
            "Started task",
            task["title"]
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to start task")
        flash("We could not start the task. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task started.", "success")
    return redirect(url_for("hello"))


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                status
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        if task["status"] == "completed":
            return redirect(url_for("hello"))

        cursor.execute(
            """
            UPDATE tasks
            SET
                status = 'completed',
                completed_at = NOW(),
                notification = TRUE
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        log_activity(
            cursor,
            session["user_id"],
            "completed",
            "task",
            task_id,
            "Completed task",
            task["title"]
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to complete task")
        flash("We could not complete the task. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task completed.", "success")
    return redirect(url_for("hello"))


@app.route("/continue-tomorrow/<int:task_id>", methods=["POST"])
def continue_tomorrow(task_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                due_date,
                start_date,
                status
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        current_due_date = task["due_date"]

        if current_due_date:
            new_due_date = (
                current_due_date +
                timedelta(days=1)
            )
        else:
            new_due_date = (
                date.today() +
                timedelta(days=1)
            )

        cursor.execute(
            """
            UPDATE tasks
            SET
                due_date = %s,
                status = 'in_progress',
                notification = FALSE
            WHERE id = %s
              AND user_id = %s
            """,
            (
                new_due_date,
                task_id,
                session["user_id"]
            )
        )

        log_activity(
            cursor,
            session["user_id"],
            "continued_tomorrow",
            "task",
            task_id,
            "Continued task to tomorrow",
            f"{task['title']} | New due date: "
            f"{new_due_date.strftime('%d %b %Y')}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to continue task tomorrow")
        flash("We could not move the task to tomorrow. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task moved to tomorrow.", "success")
    return redirect(url_for("hello"))


@app.route("/reschedule/<int:task_id>", methods=["POST"])
def reschedule(task_id):

    if not login_required():
        return redirect(url_for("login"))

    new_date_string = request.form.get(
        "new_date",
        ""
    ).strip()

    if not new_date_string:
        flash("Please choose a new due date.", "error")
        return redirect(url_for("hello"))

    try:

        new_date = datetime.strptime(
            new_date_string,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        flash("Please enter a valid date.", "error")
        return redirect(url_for("hello"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                start_date,
                due_date
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        if (
            task["start_date"] and
            new_date < task["start_date"]
        ):
            flash("Due date cannot be before start date.", "error")
            return redirect(url_for("hello"))

        old_due_date = task["due_date"]

        cursor.execute(
            """
            UPDATE tasks
            SET
                due_date = %s,
                status = 'in_progress',
                notification = FALSE
            WHERE id = %s
              AND user_id = %s
            """,
            (
                new_date,
                task_id,
                session["user_id"]
            )
        )

        old_date_text = (
            old_due_date.strftime("%d %b %Y")
            if old_due_date
            else "No due date"
        )

        log_activity(
            cursor,
            session["user_id"],
            "rescheduled",
            "task",
            task_id,
            "Rescheduled task",
            f"{task['title']} | "
            f"{old_date_text} → "
            f"{new_date.strftime('%d %b %Y')}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to reschedule task")
        flash("We could not reschedule the task. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task rescheduled successfully.", "success")
    return redirect(url_for("hello"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):

    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    deletion_reason = request.form.get(
        "deletion_reason",
        ""
    ).strip()

    custom_reason = request.form.get(
        "custom_reason",
        ""
    ).strip()

    if deletion_reason == "other":

        if not custom_reason:
            flash("Please provide a reason before deleting the task.", "error")
            return redirect(url_for("hello"))

        deletion_reason = custom_reason

    elif deletion_reason in DELETE_REASONS:

        deletion_reason = DELETE_REASONS[
            deletion_reason
        ]

    else:

        flash("Please choose a valid deletion reason.", "error")
        return redirect(url_for("hello"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                user_id
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        log_activity(
            cursor,
            user_id,
            "deleted",
            "task",
            task_id,
            "Deleted task",
            f"{task['title']} | Reason: {deletion_reason}"
        )

        cursor.execute(
            """
            INSERT INTO deleted_tasks
            (
                original_task_id,
                user_id,
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at,
                deletion_reason
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                task["id"],
                task["user_id"],
                task["title"],
                task["description"],
                task["priority"],
                task["status"],
                task["start_date"],
                task["due_date"],
                task["reminder_at"],
                deletion_reason
            )
        )

        cursor.execute(
            """
            DELETE FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                user_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to delete task")
        flash("We could not delete the task. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Task deleted successfully.", "success")
    return redirect(url_for("hello"))


@app.route("/add-subtask/<int:task_id>", methods=["POST"])
def add_subtask(task_id):

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    due_date_string = request.form.get(
        "due_date",
        ""
    ).strip()

    if not title:
        flash("Please enter a subtask name.", "error")
        return redirect(url_for("hello"))

    subtask_due_date = None

    if due_date_string:
        try:
            subtask_due_date = datetime.strptime(
                due_date_string,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Please enter a valid subtask due date.", "error")
            return redirect(url_for("hello"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                due_date
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return redirect(url_for("hello"))

        if (
            subtask_due_date and
            task["due_date"] and
            subtask_due_date > task["due_date"]
        ):
            flash("Subtask due date cannot be after the task's due date.", "error")
            return redirect(url_for("hello"))

        cursor.execute(
            """
            INSERT INTO subtasks
            (
                task_id,
                title,
                status,
                due_date
            )
            VALUES
            (
                %s,
                %s,
                'not_started',
                %s
            )
            """,
            (
                task_id,
                title,
                subtask_due_date
            )
        )

        subtask_id = cursor.lastrowid

        log_activity(
            cursor,
            session["user_id"],
            "created",
            "subtask",
            subtask_id,
            "Added subtask",
            f"{title} | Task: {task['title']}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to create subtask")
        flash("We could not add the subtask. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Subtask added successfully.", "success")
    return redirect(url_for("hello"))


@app.route("/reschedule-subtask/<int:subtask_id>", methods=["POST"])
def reschedule_subtask(subtask_id):

    if not login_required():
        return redirect(url_for("login"))

    new_date_string = request.form.get(
        "new_date",
        ""
    ).strip()

    new_due_date = None

    if new_date_string:
        try:
            new_due_date = datetime.strptime(
                new_date_string,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Please enter a valid date.", "error")
            return redirect(url_for("hello"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                subtasks.id,
                subtasks.title,
                tasks.title AS task_title,
                tasks.due_date AS task_due_date
            FROM subtasks
            JOIN tasks
                ON subtasks.task_id = tasks.id
            WHERE subtasks.id = %s
              AND tasks.user_id = %s
            """,
            (
                subtask_id,
                session["user_id"]
            )
        )

        subtask = cursor.fetchone()

        if not subtask:
            return redirect(url_for("hello"))

        if (
            new_due_date and
            subtask["task_due_date"] and
            new_due_date > subtask["task_due_date"]
        ):
            flash("Subtask due date cannot be after the task's due date.", "error")
            return redirect(url_for("hello"))

        cursor.execute(
            """
            UPDATE subtasks
            SET due_date = %s
            WHERE id = %s
            """,
            (
                new_due_date,
                subtask_id
            )
        )

        log_activity(
            cursor,
            session["user_id"],
            "updated",
            "subtask",
            subtask_id,
            "Set subtask due date",
            f"{subtask['title']} | Task: {subtask['task_title']}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to reschedule subtask")
        flash("We could not update the subtask date. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Subtask date updated.", "success")
    return redirect(url_for("hello"))


@app.route("/complete-subtask/<int:subtask_id>", methods=["POST"])
def complete_subtask(subtask_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                subtasks.id,
                subtasks.title,
                tasks.title AS task_title
            FROM subtasks
            JOIN tasks
                ON subtasks.task_id = tasks.id
            WHERE subtasks.id = %s
              AND tasks.user_id = %s
            """,
            (
                subtask_id,
                session["user_id"]
            )
        )

        subtask = cursor.fetchone()

        if not subtask:
            return redirect(url_for("hello"))

        cursor.execute(
            """
            UPDATE subtasks
            SET
                status = 'completed',
                completed_at = NOW()
            WHERE id = %s
            """,
            (subtask_id,)
        )

        log_activity(
            cursor,
            session["user_id"],
            "completed",
            "subtask",
            subtask_id,
            "Completed subtask",
            f"{subtask['title']} | Task: {subtask['task_title']}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to complete subtask")
        flash("We could not complete the subtask. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Subtask completed.", "success")
    return redirect(url_for("hello"))


@app.route("/uncomplete-subtask/<int:subtask_id>", methods=["POST"])
def uncomplete_subtask(subtask_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                subtasks.id,
                subtasks.title,
                tasks.title AS task_title,
                subtasks.status
            FROM subtasks
            JOIN tasks
                ON subtasks.task_id = tasks.id
            WHERE subtasks.id = %s
              AND tasks.user_id = %s
            """,
            (
                subtask_id,
                session["user_id"]
            )
        )

        subtask = cursor.fetchone()

        if not subtask:
            return redirect(url_for("hello"))

        cursor.execute(
            """
            UPDATE subtasks
            SET
                status = 'not_started',
                completed_at = NULL
            WHERE id = %s
            """,
            (subtask_id,)
        )

        log_activity(
            cursor,
            session["user_id"],
            "reopened",
            "subtask",
            subtask_id,
            "Marked subtask as incomplete",
            f"{subtask['title']} | Task: {subtask['task_title']}"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to reopen subtask")
        flash("We could not reopen the subtask. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Subtask marked incomplete.", "success")
    return redirect(url_for("hello"))


@app.route("/delete-subtask/<int:subtask_id>", methods=["POST"])
def delete_subtask(subtask_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                subtasks.id,
                subtasks.title,
                tasks.title AS task_title
            FROM subtasks
            JOIN tasks
                ON subtasks.task_id = tasks.id
            WHERE subtasks.id = %s
              AND tasks.user_id = %s
            """,
            (
                subtask_id,
                session["user_id"]
            )
        )

        subtask = cursor.fetchone()

        if not subtask:
            return redirect(url_for("hello"))

        log_activity(
            cursor,
            session["user_id"],
            "deleted",
            "subtask",
            subtask_id,
            "Deleted subtask",
            f"{subtask['title']} | Task: {subtask['task_title']}"
        )

        cursor.execute(
            """
            DELETE FROM subtasks
            WHERE id = %s
            """,
            (subtask_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Failed to delete subtask")
        flash("We could not delete the subtask. Please try again.", "error")
        return redirect(url_for("hello"))

    finally:
        cursor.close()
        connection.close()

    flash("Subtask deleted successfully.", "success")
    return redirect(url_for("hello"))


@app.route("/activity")
def activity():

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                action_type,
                entity_type,
                entity_id,
                title,
                details,
                created_at
            FROM activity_logs
            WHERE user_id = %s
            ORDER BY
                created_at DESC,
                id DESC
            LIMIT 500
            """,
            (
                session["user_id"],
            )
        )

        activities = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = %s
            """,
            (
                session["user_id"],
            )
        )

        user = cursor.fetchone()

        return render_template(
            "activity.html",
            activities=activities,
            user=user
        )

    except Exception:
        logger.exception("Failed to load activity")
        return render_template(
            "activity.html",
            activities=[],
            user=None,
            error="We could not load the activity log right now. Please refresh and try again."
        ), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/calendar")
def calendar():

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        return render_template(
            "calendar.html",
            user=user
        )

    except Exception:
        logger.exception("Failed to load calendar")
        return render_template(
            "calendar.html",
            user=None,
            error="We could not load your profile right now. Please refresh and try again."
        ), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/calendar-data")
def calendar_data():

    if not login_required():
        return jsonify({
            "error": "Unauthorized"
        }), 401

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                priority,
                status,
                start_date,
                due_date,
                reminder_at,
                completed_at
            FROM tasks
            WHERE user_id = %s
            ORDER BY due_date ASC
            """,
            (
                session["user_id"],
            )
        )

        tasks = cursor.fetchall()

        for task in tasks:

            # Use strftime rather than isoformat(): if this column ever
            # comes back as a datetime (not a plain date), isoformat()
            # would append a "T00:00:00" suffix that silently fails to
            # match any day in the calendar grid on the frontend.
            if task["start_date"]:
                task["start_date"] = (
                    task["start_date"].strftime("%Y-%m-%d")
                )

            if task["due_date"]:
                task["due_date"] = (
                    task["due_date"].strftime("%Y-%m-%d")
                )

            if task["reminder_at"]:
                task["reminder_at"] = (
                    task["reminder_at"]
                    .strftime("%Y-%m-%d %H:%M:%S")
                )

            if task["completed_at"]:
                task["completed_at"] = (
                    task["completed_at"]
                    .strftime("%Y-%m-%d %H:%M:%S")
                )

        return jsonify(tasks)

    except Exception:
        logger.exception("Failed to load calendar data")

        return jsonify({
            "error": "Failed to load calendar data"
        }), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/reminders")
def reminders():

    if not login_required():
        return jsonify([])

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                reminder_at
            FROM tasks
            WHERE user_id = %s
              AND reminder_at IS NOT NULL
              AND reminder_at <= NOW()
              AND notification = FALSE
              AND status != 'completed'
            ORDER BY reminder_at ASC
            """,
            (session["user_id"],)
        )

        due_tasks = cursor.fetchall()

        for task in due_tasks:
            create_notification(
                cursor,
                session["user_id"],
                "task_reminder",
                "Task reminder",
                task["title"],
                task["id"]
            )

            cursor.execute(
                """
                UPDATE tasks
                SET notification = TRUE
                WHERE id = %s
                  AND user_id = %s
                """,
                (
                    task["id"],
                    session["user_id"]
                )
            )

            log_activity(
                cursor,
                session["user_id"],
                "reminder_created",
                "task",
                task["id"],
                "Reminder notification created",
                task["title"]
            )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                task_id,
                notification_type,
                title,
                message,
                is_read,
                created_at,
                read_at
            FROM notifications
            WHERE user_id = %s
              AND is_read = FALSE
            ORDER BY created_at DESC, id DESC
            LIMIT 50
            """,
            (session["user_id"],)
        )

        notifications_list = cursor.fetchall()

        for item in notifications_list:
            if item["created_at"]:
                item["created_at"] = item["created_at"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if item["read_at"]:
                item["read_at"] = item["read_at"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        return jsonify(notifications_list)

    except Exception:
        connection.rollback()
        logger.exception("Failed to load reminders")
        return jsonify([])

    finally:
        cursor.close()
        connection.close()


@app.route("/mark-reminder/<int:task_id>", methods=["POST"])
def mark_reminder(task_id):

    if not login_required():
        return jsonify({
            "success": False
        }), 401

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                title
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        task = cursor.fetchone()

        if not task:
            return jsonify({
                "success": False
            }), 404

        cursor.execute(
            """
            UPDATE tasks
            SET notification = TRUE
            WHERE id = %s
              AND user_id = %s
            """,
            (
                task_id,
                session["user_id"]
            )
        )

        log_activity(
            cursor,
            session["user_id"],
            "reminder_seen",
            "task",
            task_id,
            "Viewed task reminder",
            task["title"]
        )

        connection.commit()

        return jsonify({
            "success": True
        })

    except Exception:
        connection.rollback()
        logger.exception("Failed to mark reminder")

        return jsonify({
            "success": False
        }), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/notifications")
def notifications():

    if not login_required():
        return jsonify([])

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                task_id,
                notification_type,
                title,
                message,
                is_read,
                created_at,
                read_at
            FROM notifications
            WHERE user_id = %s
              AND is_read = FALSE
            ORDER BY created_at DESC, id DESC
            LIMIT 50
            """,
            (session["user_id"],)
        )

        notifications_list = cursor.fetchall()

        for item in notifications_list:
            if item["created_at"]:
                item["created_at"] = item["created_at"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if item["read_at"]:
                item["read_at"] = item["read_at"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        return jsonify(notifications_list)

    except Exception:
        logger.exception("Failed to load unread notifications")
        return jsonify([])

    finally:
        cursor.close()
        connection.close()


@app.route("/notifications/unread-count")
def unread_notification_count():

    if not login_required():
        return jsonify({"count": 0})

    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = %s
              AND is_read = FALSE
            """,
            (session["user_id"],)
        )

        return jsonify({"count": cursor.fetchone()[0]})

    except Exception:
        logger.exception("Failed to load unread notification count")
        return jsonify({"count": 0})

    finally:
        cursor.close()
        connection.close()


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):

    if not login_required():
        return jsonify({"success": False}), 401

    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE notifications
            SET
                is_read = TRUE,
                read_at = NOW()
            WHERE id = %s
              AND user_id = %s
            """,
            (
                notification_id,
                session["user_id"]
            )
        )

        connection.commit()

        return jsonify({
            "success": cursor.rowcount > 0
        })

    except Exception:
        connection.rollback()
        logger.exception("Failed to mark notification as read")
        return jsonify({"success": False}), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():

    if not login_required():
        return jsonify({"success": False}), 401

    connection = mysql_db()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE notifications
            SET
                is_read = TRUE,
                read_at = NOW()
            WHERE user_id = %s
              AND is_read = FALSE
            """,
            (session["user_id"],)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "updated": cursor.rowcount
        })

    except Exception:
        connection.rollback()
        logger.exception("Failed to mark all notifications as read")
        return jsonify({"success": False}), 500

    finally:
        cursor.close()
        connection.close()


@app.route("/notifications/all")
def notifications_page():

    if not login_required():
        return redirect(url_for("login"))

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                task_id,
                notification_type,
                title,
                message,
                is_read,
                created_at,
                read_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 500
            """,
            (session["user_id"],)
        )

        notifications_list = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        return render_template(
            "notifications.html",
            notifications=notifications_list,
            user=user
        )

    except Exception:
        logger.exception("Failed to load notification history")
        return render_template(
            "notifications.html",
            notifications=[],
            user=None,
            error="We could not load notification history right now. Please refresh and try again."
        ), 500

    finally:
        cursor.close()
        connection.close()


def overdue_time():

    connection = mysql_db()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                title
            FROM tasks
            WHERE due_date < CURDATE()
              AND status NOT IN (
                  'completed',
                  'overdue'
              )
            """
        )

        overdue_tasks = cursor.fetchall()

        for task in overdue_tasks:

            cursor.execute(
                """
                UPDATE tasks
                SET
                    status = 'overdue',
                    notification = TRUE
                WHERE id = %s
                  AND status NOT IN (
                      'completed',
                      'overdue'
                  )
                """,
                (
                    task["id"],
                )
            )

            if cursor.rowcount > 0:

                create_notification(
                    cursor,
                    task["user_id"],
                    "task_overdue",
                    "Task became overdue",
                    task["title"],
                    task["id"]
                )

                log_activity(
                    cursor,
                    task["user_id"],
                    "overdue",
                    "task",
                    task["id"],
                    "Task became overdue",
                    task["title"]
                )

        connection.commit()

    except Exception:
        connection.rollback()
        logger.exception("Overdue checker failed")

    finally:
        cursor.close()
        connection.close()


def background_checker():

    while True:

        try:
            overdue_time()

        except Exception:
            logger.exception(
                "Background checker failed"
            )

        time.sleep(60)


def start_background_thread():

    thread = threading.Thread(
        target=background_checker,
        daemon=True
    )

    thread.start()


if __name__ == "__main__":

    ensure_activity_table()
    ensure_notification_table()
    ensure_subtask_due_date_column()

    start_background_thread()

    app.run(
        debug=os.environ.get(
            "FLASK_DEBUG",
            "false"
        ).lower() == "true"
    )