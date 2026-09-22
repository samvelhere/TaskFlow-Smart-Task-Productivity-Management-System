# TaskFlow

TaskFlow is a full-stack productivity and task management web app built with Python, Flask, MySQL, HTML, CSS, and JavaScript. It helps users organize work, manage deadlines, create reminders, track overdue tasks, and review activity history from a clean dashboard.

## Features
- Secure user registration and login
- Task and subtask management
- Priorities, statuses, due dates, and reminders
- Calendar view for upcoming work
- Notifications and overdue tracking
- Activity log for recent actions
- Search and filtering for tasks
- Responsive UI for desktop and mobile

## Quick start

### 1) Clone the project

```bash
git clone https://github.com/samvelhere/TaskFlow-Smart-Task-Productivity-Management-System.git
cd TaskFlow-Smart-Task-Productivity-Management-System
```

### 2) Create and activate a virtual environment

On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Create your environment file

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Then update `.env` with your local MySQL details:

```env
SECRET_KEY=change_this_to_a_long_random_string
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=taskflow
FLASK_DEBUG=false
```

### 5) Set up MySQL

Create a MySQL database:

```sql
CREATE DATABASE taskflow;
```

Make sure MySQL is running locally and that the credentials in `.env` match your installation.

### 6) Run the app

```bash
python app.py
```

The app will start locally at:

```text
http://localhost:5000
```

Open that URL in your browser to access the app.

## Access flow for users

A typical user journey is:

1. Open `http://localhost:5000`
2. Create an account or sign in
3. View the dashboard
4. Add tasks, set deadlines and reminders
5. Use Calendar, Activity, and Notifications pages

## Project structure

```text
TaskFlow-Smart-Task-Productivity-Management-System/
├── app.py
├── app.js
├── activity.css
├── activity.html
├── base.html
├── calendar.html
├── calendar.js
├── dashboard.css
├── dashboard.js
├── demo.html
├── error.html
├── login.html
├── notifications.html
├── notifications.js
├── register.html
├── taskflow.css
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── static/
```

## Deployment guide

For public access, deploy the app to a hosting service with a MySQL database, such as:
- Render
- Railway
- PythonAnywhere
- Azure App Service
- VPS + Nginx + Gunicorn

When deploying, make sure you:
- set `SECRET_KEY`
- provide production MySQL values
- set `FLASK_DEBUG=false`
- open the correct port for your hosting platform

Example deployment run command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Notes
- Never commit your real `.env` file to GitHub.
- Keep `.env` local only.
- If you need to change the app port, update the runtime configuration in your hosting environment.

## License
This project is for educational and portfolio purposes.
