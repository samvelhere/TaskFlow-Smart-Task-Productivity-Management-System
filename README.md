# 🚀 TaskFlow

### Smart Task & Productivity Management System

TaskFlow is a full-stack productivity and task management web application designed to help users organize, prioritize, and track their daily work efficiently.

Built with **Python, Flask, MySQL, HTML, CSS, and JavaScript**, TaskFlow provides a centralized workspace for managing tasks, subtasks, deadlines, reminders, notifications, and productivity activity.

---

## ✨ Features

### 🔐 Authentication

* User registration and login
* Secure password hashing
* Session-based authentication
* CSRF protection
* User-specific task management

### ✅ Task Management

* Create, edit, and delete tasks
* Task priorities
* Task status tracking
* Start and due dates
* Task completion tracking
* Reschedule tasks
* Continue incomplete tasks for the next day
* Search and filtering

### 📌 Subtasks

* Create subtasks under tasks
* Track subtask completion
* Edit and delete subtasks
* Subtask deadlines
* Visual progress tracking

### 📅 Calendar

* Dedicated calendar interface
* View tasks according to their dates
* Start and due date visualization
* Calendar-based task management

### 🔔 Notifications & Reminders

* Task reminders
* Overdue task detection
* In-app notifications
* Unread notification count
* Mark notifications as read
* Notification history

### 📊 Activity Tracking

* Task activity history
* Subtask activity tracking
* Completion and deletion records
* Delete reasons
* User activity timeline

### 🎨 Modern UI

* Responsive design
* Consistent design system
* Custom modals
* Confirmation dialogs
* Modern dashboard
* Mobile-friendly layout
* Accessibility-focused interface

---

## 🛠️ Technology Stack

| Technology       | Purpose                     |
| ---------------- | --------------------------- |
| **Python**       | Backend programming         |
| **Flask**        | Web framework               |
| **MySQL**        | Database                    |
| **HTML5**        | Page structure              |
| **CSS3**         | Styling & responsive design |
| **JavaScript**   | Frontend functionality      |
| **Font Awesome** | Icons                       |
| **Google Fonts** | Typography                  |

---

## 📂 Project Structure

```text
TaskFlow/
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── demo.html
│   ├── calendar.html
│   ├── activity.html
│   └── error.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       ├── app.js
│       └── calendar.js
│
└── database/
    └── schema.sql
```

> The exact structure may vary depending on your local project version.

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/taskflow.git
```

Move into the project directory:

```bash
cd taskflow
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🗄️ MySQL Setup

Make sure **MySQL Server** is installed and running.

Create the database:

```sql
CREATE DATABASE todo_app;
```

Then create the required tables using the provided database schema.

Example:

```sql
USE todo_app;
```

Import your schema:

```bash
mysql -u root -p todo_app < database/schema.sql
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key

MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=todo_app

FLASK_DEBUG=false
```

### ⚠️ Important

**Never upload `.env` to GitHub.**

Add it to `.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

You can provide an `.env.example` file instead:

```env
SECRET_KEY=your-secret-key
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=todo_app
FLASK_DEBUG=false
```

---

# ▶️ Run the Application

Start the Flask application:

```bash
python app.py
```

You should see something similar to:

```text
Running on http://127.0.0.1:5000
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

# 🔄 Application Flow

```text
                    ┌──────────────────┐
                    │      TaskFlow    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Authentication   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    Dashboard     │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼─────┐      ┌─────▼────┐      ┌─────▼──────┐
     │   Tasks  │      │ Calendar │      │ Activity   │
     └────┬─────┘      └──────────┘      └────────────┘
          │
     ┌────▼──────┐
     │  Subtasks │
     └────┬──────┘
          │
     ┌────▼─────────────┐
     │ Reminders &      │
     │ Notifications    │
     └──────────────────┘
```

---

# 🧠 Core Functionality

### Task Lifecycle

```text
Create
   ↓
Set Priority
   ↓
Set Start / Due Date
   ↓
Add Subtasks
   ↓
Work on Task
   ↓
Receive Reminders
   ↓
Complete / Reschedule
   ↓
Activity Recorded
```

Overdue tasks are automatically detected and reflected through the notification system.

---

# 🔔 Notification System

TaskFlow provides notifications for important task events such as:

* Upcoming reminders
* Overdue tasks
* Task-related activities
* Subtask events

Users can view notifications and mark them as read.

---

# 📅 Calendar System

The calendar provides a visual representation of scheduled work.

Users can:

* View scheduled tasks
* Identify deadlines
* Navigate between dates
* Track upcoming work
* Manage tasks based on their schedule

---

# 📋 Activity & Audit System

TaskFlow maintains an activity history to provide visibility into important actions.

Examples include:

```text
Task Created
Task Updated
Task Completed
Task Rescheduled
Subtask Created
Subtask Completed
Task Deleted
```

Deletion actions can also record the reason for deletion.

---

# 🔒 Security

TaskFlow implements several security practices:

* Password hashing
* Session authentication
* CSRF protection
* Parameterized SQL queries
* User-specific database access
* Environment-based configuration
* Secure session configuration

For production deployment, additional security hardening is recommended.

---

# 🚀 Future Improvements

Potential future improvements include:

* [ ] REST API documentation
* [ ] Flask Blueprints architecture
* [ ] Database migrations with Alembic/Flask-Migrate
* [ ] Automated unit and integration tests
* [ ] Docker support
* [ ] Production WSGI configuration
* [ ] Redis/Celery-based background jobs
* [ ] Email notifications
* [ ] Push notifications
* [ ] Task analytics dashboard
* [ ] Team collaboration
* [ ] Task sharing
* [ ] Role-based access control
* [ ] Dark mode
* [ ] Cloud deployment

---

# 📸 Screenshots

Add screenshots of the application here.

Recommended screenshots:

```text
Dashboard
Login
Register
Task Details
Calendar
Notifications
Activity History
```

Example:

```markdown
![Dashboard](screenshots/dashboard.png)
![Calendar](screenshots/calendar.png)
![Notifications](screenshots/notifications.png)
```

---

# 🎯 Project Objective

The goal of TaskFlow is to provide a centralized productivity platform where users can manage their tasks, subtasks, deadlines, reminders, notifications, and activity history from a single application.

The project also demonstrates practical implementation of:

* Full-stack web development
* Backend development with Flask
* Relational database design
* Authentication
* CRUD operations
* API-based frontend communication
* JavaScript-driven UI interactions
* Application security
* Responsive web design

---

# 👨‍💻 Author

**Samarth Pandey**

Full-Stack Development Project

---

## ⭐ If You Like This Project

If TaskFlow helped you or you found the project useful, consider giving the repository a ⭐ on GitHub.

---

## 📄 License

This project is created for educational and portfolio purposes.
