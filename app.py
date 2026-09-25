import os
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for

from models import Experience, JournalArticle, Skill, WorkProject, db
from sqlalchemy.exc import IntegrityError, OperationalError

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ernest_portfolio"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

STATIC_PAGES = {"about.html", "experience.html", "skills.html", "projects.html"}
CONTENT_MODELS = {
    "article": JournalArticle,
    "skill": Skill,
    "experience": Experience,
    "project": WorkProject,
}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def safe_next(value):
    if value:
        parsed = urlparse(value)
        if not parsed.netloc and parsed.path.startswith("/"):
            return value
    return url_for("manage")


def build_item(kind, form):
    """Factory that constructs the correct model instance from form data."""
    model = CONTENT_MODELS.get(kind)
    if model is JournalArticle:
        return JournalArticle(
            title=form["title"], slug=form["slug"],
            excerpt=form["excerpt"], body=form["body"],
            published=form.get("published") == "on",
        )
    if model is Skill:
        return Skill(
            category=form["category"], name=form["name"],
            sort_order=int(form.get("sort_order", 0)),
        )
    if model is Experience:
        return Experience(
            role=form["role"], organization=form["organization"],
            period=form["period"], summary=form["summary"],
            sort_order=int(form.get("sort_order", 0)),
        )
    if model is WorkProject:
        return WorkProject(
            title=form["title"], category=form["category"],
            description=form["description"], stack=form["stack"],
            url=form.get("url", ""), featured=form.get("featured") == "on",
            sort_order=int(form.get("sort_order", 0)),
        )
    abort(400)


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def static_page(filename):
    if filename.startswith(("manage", "journal")) or filename not in STATIC_PAGES:
        abort(404)
    return send_from_directory(BASE_DIR, filename)


@app.get("/journal")
def journal():
    try:
        articles = JournalArticle.query.filter_by(published=True).order_by(JournalArticle.created_at.desc()).all()
    except OperationalError:
        articles = []
    return render_template("journal.html", articles=articles)


@app.get("/journal/<slug>")
def article(slug):
    try:
        item = JournalArticle.query.filter_by(slug=slug, published=True).first_or_404()
    except OperationalError:
        abort(503)
    return render_template("article.html", article=item)


@app.route("/manage/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == os.getenv("ADMIN_USERNAME", "admin")
            and request.form.get("password") == os.getenv("ADMIN_PASSWORD", "change-this-password")
        ):
            session["admin_authenticated"] = True
            return redirect(safe_next(request.args.get("next")))
        flash("Invalid management credentials.", "error")
    return render_template("login.html")


@app.get("/manage/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/manage", methods=["GET", "POST"])
@admin_required
def manage():
    if request.method == "POST":
        kind = request.form.get("kind")
        try:
            db.session.add(build_item(kind, request.form))
            db.session.commit()
            flash("Content saved.", "success")
        except (KeyError, ValueError, IntegrityError, OperationalError) as error:
            db.session.rollback()
            flash(f"Could not save content: {error}", "error")
        return redirect(url_for("manage"))

    return render_template(
        "manage.html",
        articles=JournalArticle.query.order_by(JournalArticle.created_at.desc()).all(),
        skills=Skill.query.order_by(Skill.category, Skill.sort_order).all(),
        experiences=Experience.query.order_by(Experience.sort_order).all(),
        projects=WorkProject.query.order_by(WorkProject.sort_order).all(),
    )


@app.post("/manage/delete/<kind>/<int:item_id>")
@admin_required
def delete_item(kind, item_id):
    model = CONTENT_MODELS.get(kind)
    if model is None:
        abort(404)
    item = db.session.get(model, item_id)
    if item is None:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Content deleted.", "success")
    return redirect(url_for("manage"))


@app.errorhandler(OperationalError)
def handle_db_error(e):
    return render_template("error.html", code=503, message="Database connection unavailable. Please try again later."), 503


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables created.")


if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Warning: Could not initialize database ({e}). Static pages will still work.")
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
