# Thika Technical Training Institute — Online Trainee Tracking System

A full-stack web application built with Flask and Supabase for tracking trainee progress, skill evidence, and employer verifications.

## Portals

| Portal | URL | Access |
|---|---|---|
| Landing | `/` | Public |
| Trainee Login | `/auth/trainee/login` | Trainees |
| Institute Login | `/auth/institute/login` | Admin / Instructors |
| Employer Login | `/employer/login` | Employers |

## Features

- **Trainee Portal** — Personal dashboard, upload skill evidence (photos/videos/PDFs), track academic progress, manage account, reset password
- **Institute Dashboard** — View all trainees, approve media, live activity feed, GIS map, employer verifications
- **Employer Portal** — Register company account, search trainees by name/ID, submit recommendations (read-only for trainees)
- **Digital Portfolio** — Public shareable trainee portfolio with verified skills and employer reviews
- **Media Evidence** — Upload with geolocation, skill tags, category, approval workflow
- **GIS Map** — Internship and project locations on interactive Leaflet map

## Setup

### Prerequisites
- Python 3.11+
- [Supabase](https://supabase.com) project

### Local Development

```bash
# Clone and install
git clone <repo-url>
cd <repo>
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

# Run
python run.py
```

### Database Setup

1. Run `supabase_schema.sql` in Supabase SQL Editor
2. Run `supabase_rls_fix.sql` to add public read policies and seed departments/courses
3. Run `supabase_employers.sql` to add the employers table
4. Run `python setup_db.py` to seed data and create admin user

### Create Institute Admin

1. Supabase Dashboard → Authentication → Users → Add User
2. Copy the UUID
3. Run in SQL Editor:
```sql
INSERT INTO profiles (id, role, full_name, email, is_active)
VALUES ('YOUR-UUID', 'admin', 'Administrator', 'admin@ttti.ac.ke', true)
ON CONFLICT (id) DO UPDATE SET role = 'admin', is_active = true;
```

## Deployment (Render)

1. Push to GitHub
2. Connect repo on [render.com](https://render.com)
3. Set environment variables: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `INSTITUTION_NAME`

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `INSTITUTION_NAME` | Institution display name |
| `FLASK_ENV` | `development` or `production` |
