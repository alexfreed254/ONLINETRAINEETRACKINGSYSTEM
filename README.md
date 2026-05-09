# TSEPIP - Technical Skills Evidence & Progress Intelligence Platform

An Online Trainee Tracking System built with Flask and Supabase.

## Features

- **Authentication** - Secure login for admins, trainers, trainees, and employers
- **Dashboard** - Role-based dashboards with progress overviews
- **Trainee Management** - Track trainee profiles, skills, and progress
- **Media Uploads** - Upload images, videos, and documents as evidence
- **Portfolio** - Trainee skill portfolios with evidence
- **Employer Verification** - Employer access to verify trainee competencies

## Setup

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project

### Local Development

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd trainee-tracking-system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

5. Run the development server:
   ```bash
   FLASK_ENV=development python run.py
   ```

### Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key for session signing |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (admin operations) |
| `INSTITUTION_NAME` | Name of your institution |
| `FLASK_ENV` | `development` or `production` |

## Deployment

### Render

1. Push your code to a GitHub repository.
2. Create a new Web Service on [Render](https://render.com) and connect your repo.
3. Render will detect `render.yaml` and configure the service automatically.
4. Set the `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_SERVICE_KEY` environment variables in the Render dashboard.

## Project Structure

```
.
├── app/
│   ├── __init__.py          # App factory
│   ├── auth/                # Authentication blueprint
│   ├── dashboard/           # Dashboard blueprint
│   ├── trainees/            # Trainee management blueprint
│   ├── media/               # Media upload blueprint
│   ├── portfolio/           # Portfolio blueprint
│   ├── employer/            # Employer verification blueprint
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── base.html
│       ├── auth/
│       ├── dashboard/
│       ├── trainees/
│       ├── media/
│       ├── portfolio/
│       └── employer/
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── Procfile
└── render.yaml
```

## License

MIT
