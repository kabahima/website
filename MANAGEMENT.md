# Flask/PostgreSQL management

The original HTML portfolio remains available as the public homepage. The Flask app adds:

- `/journal` and `/journal/<slug>` for published articles
- `/manage` for protected content management
- PostgreSQL-backed journal articles, skills, experience, and work projects
- `featured` projects for selected work

## Run

1. Create a PostgreSQL database named `ernest_portfolio`.
2. Copy `.env.example` to `.env` and set `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `SECRET_KEY`.
3. Install dependencies with `python -m pip install -r requirements.txt`.
4. Initialize tables with `flask --app app init-db`.
5. Start the app with `flask --app app run --debug`.

Open `http://127.0.0.1:5000/manage` to sign in and manage content.

The current CRUD surface intentionally keeps the first version small. Editing can be added next with pre-filled forms; deletion and creation are already protected by the admin session.
