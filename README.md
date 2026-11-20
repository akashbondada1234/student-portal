# Student Portal

A small server-rendered student account application built for the Student Portal assignment. Visitors can register as students, log in, view a protected dashboard, and log out. Administrators can access an additional protected page.

## Technology stack

- Python and FastAPI
- Jinja2 and HTML templates
- SQLite with SQLAlchemy
- `pwdlib[argon2]` for Argon2 password hashing
- Starlette `SessionMiddleware` for cookie-based sessions

No JavaScript, frontend framework, JWT, or external authentication provider is used.

## Project structure

```text
student_portal/
├── main.py             # FastAPI routes and application setup
├── database.py         # SQLAlchemy engine, session, and initialization
├── models.py           # users table model
├── security.py         # Argon2 hash and verification helpers
├── requirements.txt
├── .env.example
├── templates/          # Jinja2 pages
├── static/style.css
└── screenshots/        # demonstration screenshots
```

## Installation and setup

From this directory, create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and replace `SESSION_SECRET` with a long random value. The included `.env` is for local development only and is excluded from Git. `HTTPS_ONLY=false` is appropriate only for local HTTP development; set it to `true` behind HTTPS.

## Run the application

```bash
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. The SQLite database and `users` table are created automatically when the application starts.

## User workflow

1. Select **Register**, enter a full name, valid email, and password of at least eight characters.
2. The password is hashed with `PasswordHash.recommended()` (Argon2) before the user is saved. Only `password_hash` is stored.
3. Use **Login** to verify the password. On success, the session stores only `user_id` and redirects to the dashboard.
4. Dashboard and admin routes reload the user from the database. Logout clears the entire session.

## Assigning an admin for testing

Public registration always assigns `student`. After registering a trusted test account, use a controlled database operation from this project directory:

```bash
python -c "import sqlite3; c=sqlite3.connect('student_portal.db'); c.execute(\"UPDATE users SET role='admin' WHERE email=?\", ('admin@example.com',)); c.commit(); c.close()"
```

Replace the email with the trusted account's email. Log in again to see the Admin Page link. Students receive a backend-generated HTTP 403 access-denied page.

## Verification checklist

- Registration validates required fields, email format, password length, and duplicate email.
- Database stores an Argon2 hash, never the submitted password.
- Invalid login uses a generic error.
- Dashboard redirects unauthenticated visitors to Login.
- Admin authorization is checked in the backend against the database role.
- Logout clears the session and protected pages require login again.

CSRF protection is intentionally outside the scope of this assignment.
