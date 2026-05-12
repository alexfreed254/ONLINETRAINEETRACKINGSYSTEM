from flask import render_template, session, redirect, url_for, flash, request, jsonify
from app.employer import employer
from app.auth.routes import login_required
from app.supabase_client import get_supabase_admin
from datetime import datetime
from functools import wraps


def employer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return redirect(url_for('employer.login'))
        if user.get('role') != 'employer':
            flash('Employer access only.', 'danger')
            return redirect(url_for('employer.login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Employer Register
# ─────────────────────────────────────────────

@employer.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user', {}).get('role') == 'employer':
        return redirect(url_for('employer.dashboard'))

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        industry = request.form.get('industry', '').strip()

        errors = []
        if not company_name:
            errors.append('Company name is required.')
        if not email:
            errors.append('Official email is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('employer/register.html', form_data=request.form)

        try:
            sb_admin = get_supabase_admin()
            auth_resp = sb_admin.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'full_name': company_name, 'role': 'employer'}
            })

            if auth_resp.user:
                uid = auth_resp.user.id
                # Create profile
                sb_admin.table('profiles').insert({
                    'id': uid,
                    'role': 'employer',
                    'full_name': company_name,
                    'email': email,
                    'phone': phone or None,
                    'county_region': location or None,
                }).execute()
                # Create employer record
                sb_admin.table('employers').insert({
                    'profile_id': uid,
                    'company_name': company_name,
                    'official_email': email,
                    'phone': phone or None,
                    'location': location or None,
                    'industry': industry or None,
                }).execute()

                flash('Employer account created! You can now log in.', 'success')
                return redirect(url_for('employer.login'))
            else:
                flash('Registration failed. Please try again.', 'danger')

        except Exception as e:
            err = str(e)
            if 'already registered' in err or 'already exists' in err:
                flash('An account with this email already exists.', 'danger')
            else:
                flash(f'Registration failed: {err[:120]}', 'danger')

    return render_template('employer/register.html', form_data={})


# ─────────────────────────────────────────────
# Employer Login
# ─────────────────────────────────────────────

@employer.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user', {}).get('role') == 'employer':
        return redirect(url_for('employer.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('employer/login.html')

        try:
            from app.supabase_client import get_supabase
            sb_anon = get_supabase()
            resp = sb_anon.auth.sign_in_with_password({'email': email, 'password': password})

            if resp.user:
                sb = get_supabase_admin()
                profile = sb.table('profiles').select('*').eq('id', resp.user.id).execute().data
                profile = profile[0] if profile else {}

                if profile.get('role') != 'employer':
                    sb_anon.auth.sign_out()
                    flash('This portal is for employers only.', 'warning')
                    return render_template('employer/login.html')

                emp_rows = sb.table('employers').select('*').eq('profile_id', resp.user.id).execute().data or []
                emp = emp_rows[0] if emp_rows else {}

                session['user'] = {
                    'id': resp.user.id,
                    'email': resp.user.email,
                    'access_token': resp.session.access_token,
                    'role': 'employer',
                    'full_name': emp.get('company_name', email),
                    'employer_id': emp.get('id', ''),
                    'profile_photo_url': '',
                }
                session.permanent = True
                flash(f'Welcome, {emp.get("company_name", email)}!', 'success')
                return redirect(url_for('employer.dashboard'))
            else:
                flash('Invalid email or password.', 'danger')

        except Exception as e:
            err = str(e)
            if 'Invalid login credentials' in err:
                flash('Invalid email or password.', 'danger')
            else:
                flash('Login failed. Please try again.', 'danger')

    return render_template('employer/login.html')


# ─────────────────────────────────────────────
# Employer Logout
# ─────────────────────────────────────────────

@employer.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('employer.login'))


# ─────────────────────────────────────────────
# Employer Dashboard
# ─────────────────────────────────────────────

@employer.route('/dashboard')
@employer_required
def dashboard():
    user = session.get('user')
    sb = get_supabase_admin()

    employer_id = user.get('employer_id', '')

    try:
        my_verifications = sb.table('employer_verifications').select(
            '*, trainees(*, profiles(full_name, profile_photo_url), departments(name), courses(name))'
        ).eq('employer_id', employer_id).order('created_at', desc=True).execute().data or []

        stats = {
            'total': len(my_verifications),
            'verified': len([v for v in my_verifications if v['status'] == 'verified']),
            'pending': len([v for v in my_verifications if v['status'] == 'pending']),
        }

        emp_rows = sb.table('employers').select('*').eq('id', employer_id).execute().data or []
        emp_profile = emp_rows[0] if emp_rows else {}

        my_jobs = sb.table('job_postings').select('*').eq(
            'employer_id', employer_id
        ).order('created_at', desc=True).limit(5).execute().data or []

    except Exception:
        my_verifications = []
        stats = {'total': 0, 'verified': 0, 'pending': 0}
        emp_profile = {}
        my_jobs = []

    return render_template('employer/dashboard.html',
                           user=user,
                           verifications=my_verifications,
                           stats=stats,
                           emp_profile=emp_profile,
                           jobs=my_jobs)


# ─────────────────────────────────────────────
# Search Trainee
# ─────────────────────────────────────────────

@employer.route('/search', methods=['GET', 'POST'])
@employer_required
def search():
    user = session.get('user')
    sb_admin = get_supabase_admin()

    results = []
    query_str = ''

    if request.method == 'POST' or request.args.get('q'):
        query_str = (request.form.get('query') or request.args.get('q', '')).strip()

        if query_str:
            try:
                # Search by full name or national ID
                all_trainees = sb_admin.table('trainees').select(
                    '*, profiles(full_name, national_id, profile_photo_url, email, phone, county_region), '
                    'courses(name), departments(name)'
                ).eq('status', 'active').execute().data or []

                q = query_str.lower()
                results = [
                    t for t in all_trainees
                    if q in (t.get('profiles') or {}).get('full_name', '').lower()
                    or q in ((t.get('profiles') or {}).get('national_id') or '').lower()
                    or q in t.get('admission_number', '').lower()
                ]
            except Exception as e:
                flash(f'Search error: {str(e)[:80]}', 'danger')

    return render_template('employer/search.html',
                           user=user,
                           results=results,
                           query=query_str)


# ─────────────────────────────────────────────
# Submit Recommendation / Verification
# ─────────────────────────────────────────────

@employer.route('/recommend/<trainee_id>', methods=['GET', 'POST'])
@employer_required
def recommend(trainee_id):
    user = session.get('user')
    sb_admin = get_supabase_admin()

    try:
        rows = sb_admin.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).execute().data or []
        trainee = rows[0] if rows else None
    except Exception:
        trainee = None

    if not trainee:
        flash('Trainee not found.', 'danger')
        return redirect(url_for('employer.search'))

    if request.method == 'POST':
        verification_type = request.form.get('verification_type', 'employment')
        rating = request.form.get('rating', '')
        comments = request.form.get('comments', '').strip()
        status = request.form.get('status', 'verified')

        if not comments:
            flash('Please provide a comment or recommendation.', 'danger')
            return render_template('employer/recommend.html', user=user, trainee=trainee)

        try:
            emp_rows = sb_admin.table('employers').select('company_name, official_email').eq(
                'id', user['employer_id']
            ).execute().data or []
            emp = emp_rows[0] if emp_rows else {}

            sb_admin.table('employer_verifications').insert({
                'trainee_id': trainee_id,
                'employer_id': user['employer_id'],
                'employer_name': emp.get('company_name', user['full_name']),
                'employer_email': emp.get('official_email', user['email']),
                'employer_company': emp.get('company_name', ''),
                'verification_type': verification_type,
                'status': status,
                'rating': int(rating) if rating else None,
                'comments': comments,
                'verified_at': datetime.now().isoformat() if status == 'verified' else None,
            }).execute()

            flash('Recommendation submitted successfully!', 'success')
            return redirect(url_for('employer.dashboard'))

        except Exception as e:
            flash(f'Submission failed: {str(e)[:100]}', 'danger')

    return render_template('employer/recommend.html', user=user, trainee=trainee)


# ─────────────────────────────────────────────
# Institute-facing employer portal (admin view)
# ─────────────────────────────────────────────

@employer.route('/')
@login_required
def index():
    user = session.get('user')
    if user.get('role') == 'employer':
        return redirect(url_for('employer.dashboard'))

    sb = get_supabase_admin()
    current_status = request.args.get('status', '')

    try:
        query = sb.table('employer_verifications').select(
            '*, trainees(*, profiles(full_name, profile_photo_url), departments(name), courses(name))'
        )
        if current_status:
            query = query.eq('status', current_status)

        verifications = query.order('created_at', desc=True).execute().data or []
        all_v = sb.table('employer_verifications').select('id, status').execute().data or []
        stats = {
            'total': len(all_v),
            'pending': len([v for v in all_v if v['status'] == 'pending']),
            'verified': len([v for v in all_v if v['status'] == 'verified']),
            'rejected': len([v for v in all_v if v['status'] == 'rejected']),
        }
    except Exception:
        verifications = []
        stats = {'total': 0, 'pending': 0, 'verified': 0, 'rejected': 0}

    return render_template('employer/index.html',
                           verifications=verifications,
                           stats=stats,
                           current_status=current_status,
                           user=user)


@employer.route('/verification/<verification_id>/update', methods=['POST'])
@login_required
def update_verification(verification_id):
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        flash('Permission denied.', 'danger')
        return redirect(url_for('employer.index'))

    sb_admin = get_supabase_admin()
    new_status = request.form.get('status', 'verified')
    try:
        sb_admin.table('employer_verifications').update({
            'status': new_status,
            'verified_at': datetime.now().isoformat() if new_status == 'verified' else None,
        }).eq('id', verification_id).execute()
        flash(f'Status updated to {new_status}.', 'success')
    except Exception:
        flash('Update failed.', 'danger')

    return redirect(request.referrer or url_for('employer.index'))


# ─────────────────────────────────────────────
# Browse Trainee Profiles (with skill filters)
# ─────────────────────────────────────────────

@employer.route('/browse')
@employer_required
def browse():
    user = session.get('user')
    sb = get_supabase_admin()

    dept_filter = request.args.get('department', '')
    skill_filter = request.args.get('skill', '').strip()
    course_filter = request.args.get('course', '')
    status_filter = request.args.get('status', 'active')

    trainees = []
    departments = []
    courses = []

    try:
        query = sb.table('trainees').select(
            '*, profiles(full_name, profile_photo_url, county_region, email), '
            'courses(name, code), departments(name)'
        ).eq('status', status_filter or 'active')

        if dept_filter:
            query = query.eq('department_id', dept_filter)
        if course_filter:
            query = query.eq('course_id', course_filter)

        all_trainees = query.order('created_at', desc=True).execute().data or []

        # Filter by skill tag if provided (check media uploads)
        if skill_filter:
            q = skill_filter.lower()
            # Get trainee IDs that have media with matching skill tags
            media = sb.table('media_uploads').select(
                'trainee_id, skill_tags'
            ).eq('approval_status', 'approved').execute().data or []

            matching_ids = set()
            for m in media:
                tags = [t.lower() for t in (m.get('skill_tags') or [])]
                if any(q in tag for tag in tags):
                    matching_ids.add(m['trainee_id'])

            # Also check competencies
            comps = sb.table('trainee_competencies').select(
                'trainee_id, competencies(name, category)'
            ).eq('status', 'verified').execute().data or []
            for c in comps:
                comp = c.get('competencies') or {}
                if q in comp.get('name', '').lower() or q in comp.get('category', '').lower():
                    matching_ids.add(c['trainee_id'])

            all_trainees = [t for t in all_trainees if t['id'] in matching_ids]

        trainees = all_trainees
        departments = sb.table('departments').select('id, name').execute().data or []
        courses = sb.table('courses').select('id, name').execute().data or []

    except Exception as e:
        flash(f'Error loading trainees: {str(e)[:80]}', 'danger')

    return render_template('employer/browse.html',
                           user=user,
                           trainees=trainees,
                           departments=departments,
                           courses=courses,
                           dept_filter=dept_filter,
                           skill_filter=skill_filter,
                           course_filter=course_filter)


# ─────────────────────────────────────────────
# Job / Internship Postings — List & Create
# ─────────────────────────────────────────────

@employer.route('/jobs')
@employer_required
def jobs():
    user = session.get('user')
    sb = get_supabase_admin()
    employer_id = user.get('employer_id', '')

    try:
        my_jobs = sb.table('job_postings').select('*').eq(
            'employer_id', employer_id
        ).order('created_at', desc=True).execute().data or []
    except Exception:
        my_jobs = []

    return render_template('employer/jobs.html', user=user, jobs=my_jobs)


@employer.route('/jobs/post', methods=['GET', 'POST'])
@employer_required
def post_job():
    user = session.get('user')
    sb = get_supabase_admin()
    employer_id = user.get('employer_id', '')

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        job_type = request.form.get('type', 'job')
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        skills_raw = request.form.get('skills_required', '')
        skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
        location = request.form.get('location', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        deadline = request.form.get('deadline', '') or None
        slots = request.form.get('slots', '1')
        dept_pref = request.form.get('department_preference', '').strip()

        if not title or not description:
            flash('Title and description are required.', 'danger')
        else:
            try:
                sb.table('job_postings').insert({
                    'employer_id': employer_id,
                    'title': title,
                    'type': job_type,
                    'description': description,
                    'requirements': requirements or None,
                    'skills_required': skills,
                    'department_preference': dept_pref or None,
                    'location': location or None,
                    'salary_range': salary_range or None,
                    'deadline': deadline,
                    'slots': int(slots) if slots.isdigit() else 1,
                    'is_active': True,
                }).execute()
                flash('Job posting published successfully!', 'success')
                return redirect(url_for('employer.jobs'))
            except Exception as e:
                flash(f'Failed to post job: {str(e)[:100]}', 'danger')

    departments = []
    try:
        departments = sb.table('departments').select('id, name').execute().data or []
    except Exception:
        pass

    return render_template('employer/post_job.html',
                           user=user, departments=departments)


@employer.route('/jobs/<job_id>/toggle', methods=['POST'])
@employer_required
def toggle_job(job_id):
    user = session.get('user')
    sb = get_supabase_admin()
    try:
        rows = sb.table('job_postings').select('is_active, employer_id').eq('id', job_id).execute().data or []
        if not rows or rows[0].get('employer_id') != user.get('employer_id'):
            flash('Not found or permission denied.', 'danger')
        else:
            new_state = not rows[0]['is_active']
            sb.table('job_postings').update({'is_active': new_state}).eq('id', job_id).execute()
            flash(f'Posting {"activated" if new_state else "deactivated"}.', 'success')
    except Exception:
        flash('Action failed.', 'danger')
    return redirect(url_for('employer.jobs'))


@employer.route('/jobs/<job_id>/delete', methods=['POST'])
@employer_required
def delete_job(job_id):
    user = session.get('user')
    sb = get_supabase_admin()
    try:
        rows = sb.table('job_postings').select('employer_id').eq('id', job_id).execute().data or []
        if not rows or rows[0].get('employer_id') != user.get('employer_id'):
            flash('Not found or permission denied.', 'danger')
        else:
            sb.table('job_postings').delete().eq('id', job_id).execute()
            flash('Posting deleted.', 'success')
    except Exception:
        flash('Delete failed.', 'danger')
    return redirect(url_for('employer.jobs'))


# ─────────────────────────────────────────────
# Public job board (visible to trainees too)
# ─────────────────────────────────────────────

@employer.route('/jobs/board')
def job_board():
    """Public job board — no login required."""
    sb = get_supabase_admin()
    user = session.get('user')

    type_filter = request.args.get('type', '')
    dept_filter = request.args.get('department', '')

    try:
        query = sb.table('job_postings').select(
            '*, employers(company_name, location, industry)'
        ).eq('is_active', True)

        if type_filter:
            query = query.eq('type', type_filter)

        jobs = query.order('created_at', desc=True).execute().data or []

        if dept_filter:
            jobs = [j for j in jobs if (j.get('department_preference') or '') == dept_filter]

        departments = sb.table('departments').select('id, name').execute().data or []

    except Exception:
        jobs = []
        departments = []

    return render_template('employer/job_board.html',
                           user=user, jobs=jobs,
                           departments=departments,
                           type_filter=type_filter,
                           dept_filter=dept_filter)
