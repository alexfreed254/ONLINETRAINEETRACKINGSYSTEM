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
    sb = get_supabase()
    sb_admin = get_supabase_admin()

    employer_id = user.get('employer_id', '')

    try:
        # My submitted verifications
        my_verifications = sb_admin.table('employer_verifications').select(
            '*, trainees(*, profiles(full_name, profile_photo_url), departments(name), courses(name))'
        ).eq('employer_id', employer_id).order('created_at', desc=True).execute().data or []

        stats = {
            'total': len(my_verifications),
            'verified': len([v for v in my_verifications if v['status'] == 'verified']),
            'pending': len([v for v in my_verifications if v['status'] == 'pending']),
        }

        # Employer profile
        emp_profile = sb_admin.table('employers').select('*').eq('id', employer_id).single().execute().data or {}

    except Exception:
        my_verifications = []
        stats = {'total': 0, 'verified': 0, 'pending': 0}
        emp_profile = {}

    return render_template('employer/dashboard.html',
                           user=user,
                           verifications=my_verifications,
                           stats=stats,
                           emp_profile=emp_profile)


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
        trainee = sb_admin.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).single().execute().data
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
            emp = sb_admin.table('employers').select('company_name, official_email').eq(
                'id', user['employer_id']
            ).single().execute().data or {}

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
