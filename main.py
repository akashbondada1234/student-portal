import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from database import get_db, init_db
from models import User
from security import hash_password, verify_password

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Student Portal", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "local-development-secret-change-me"),
    https_only=os.getenv("HTTPS_ONLY", "false").lower() == "true",
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


def render(request: Request, template: str, **context):
    context.setdefault("current_user_id", request.session.get("user_id"))
    return templates.TemplateResponse(request=request, name=template, context=context)


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        return None
    return db.get(User, user_id)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "home.html")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render(request, "register.html", errors=[], form={"name": "", "email": ""})


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    name = name.strip()
    email = email.strip().lower()
    errors = []
    if not name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Email address is required.")
    elif not EMAIL_PATTERN.fullmatch(email):
        errors.append("Enter a valid email address.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not errors and db.scalar(select(User).where(User.email == email)):
        errors.append("An account with that email already exists.")
    if errors:
        return render(request, "register.html", errors=errors, form={"name": name, "email": email})

    user = User(name=name, email=email, password_hash=hash_password(password), role="student")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render(
            request,
            "register.html",
            errors=["An account with that email already exists."],
            form={"name": name, "email": email},
        )
    return RedirectResponse(url="/login?registered=1", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    registered = request.query_params.get("registered") == "1"
    return render(request, "login.html", errors=[], registered=registered, form={"email": ""})


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            errors=["Email address or password is incorrect."],
            registered=False,
            form={"email": email},
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    return render(request, "dashboard.html", user=user)


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return redirect_to_login()
    if user.role != "admin":
        response = render(request, "access_denied.html", user=user)
        response.status_code = status.HTTP_403_FORBIDDEN
        return response
    return render(request, "admin.html", user=user)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
