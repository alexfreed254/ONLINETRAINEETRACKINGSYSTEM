from flask import render_template, redirect, url_for, flash, request, session, current_app
from app.auth import auth
from app.supabase_client import get_supabase, get_supabase_admin
import json


def get_current_user():
    """Get current user from session."""
    return session.get('user')


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = session.get('user')
            if not user:
                flash('Please log in.', 'warning')
                return redirect(url_for('auth.login'))
            if user.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        try:
            sb = get_supabase()
            response = sb.auth.sign_in_with_password({'email': email, 'password': password})

            if response.user:
                # Fetch profile
                profile_resp = sb.table('profiles').select('*').eq('id', response.user.id).single().execute()
                profile = profile_resp.data if profile_resp.data else {}

                session['user'] = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'role': profile.get('role', 'trainee'),
                    'full_name': profile.get('full_name', email),
                    'profile_photo_url': profile.get('profile_photo_url', ''),
                }
                session.permanent = True
                flash(f'Welcome back, {profile.get("full_name", email)}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.index'))
            else:
                flash('Invalid email or password.', 'danger')
        except Exception as e:
            error_msg = str(e)
            if 'Invalid login credentials' in error_msg:
                flash('Invalid email or password.', 'danger')
            elif 'Email not confirmed' in error_msg:
                flash('Please confirm your email address first.', 'warning')
            else:
                flash('Login failed. Please try again.', 'danger')

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        data = {
            'full_name': request.form.get('full_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', ''),
            'national_id': request.form.get('national_id', '').strip(),
            'admission_number': request.form.get('admission_number', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'gender': request.form.get('gender', ''),
            'date_of_birth': request.form.get('date_of_birth', ''),
            'county_region': request.form.get('county_region', '').strip(),
            'emergency_contact': request.form.get('emergency_contact', '').strip(),
            'emergency_phone': request.form.get('emergency_phone', '').strip(),
            'course_id': request.form.get('course_id', ''),
            'department_id': request.form.get('department_id', ''),
            'intake_year': request.form.get('intake_year', ''),
            'graduation_year': request.form.get('graduation_year', ''),
        }

        # Validation
        errors = []
        if not data['full_name']:
            errors.append('Full name is required.')
        if not data['email']:
            errors.append('Email is required.')
        if not data['password']:
            errors.append('Password is required.')
        if len(data['password']) < 8:
            errors.append('Password must be at least 8 characters.')
        if data['password'] != data['confirm_password']:
            errors.append('Passwords do not match.')
        if not data['admission_number']:
            errors.append('Admission number is required.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            # Fetch courses and departments for form
            sb = get_supabase()
            courses = sb.table('courses').select('*').eq('is_active', True).execute().data or []
            departments = sb.table('departments').select('*').execute().data or []
            return render_template('auth/register.html', courses=courses, departments=departments, form_data=data)

        try:
            sb_admin = get_supabase_admin()

            # Create auth user
            auth_response = sb_admin.auth.admin.create_user({
                'email': data['email'],
                'password': data['password'],
                'email_confirm': True,
                'user_metadata': {'full_name': data['full_name']}
            })

            if auth_response.user:
                user_id = auth_response.user.id

                # Create profile
                profile_data = {
                    'id': user_id,
                    'role': 'trainee',
                    'full_name': data['full_name'],
                    'national_id': data['national_id'] or None,
                    'admission_number': data['admission_number'],
                    'email': data['email'],
                    'phone': data['phone'] or None,
                    'gender': data['gender'] or None,
                    'date_of_birth': data['date_of_birth'] or None,
                    'county_region': data['county_region'] or None,
                    'emergency_contact': data['emergency_contact'] or None,
                    'emergency_phone': data['emergency_phone'] or None,
                }
                sb_admin.table('profiles').insert(profile_data).execute()

                # Create trainee record
                trainee_data = {
                    'profile_id': user_id,
                    'admission_number': data['admission_number'],
                    'course_id': data['course_id'] or None,
                    'department_id': data['department_id'] or None,
                    'intake_year': int(data['intake_year']) if data['intake_year'] else None,
                    'graduation_year': int(data['graduation_year']) if data['graduation_year'] else None,
                    'status': 'active',
                }
                sb_admin.table('trainees').insert(trainee_data).execute()

                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Registration failed. Please try again.', 'danger')

        except Exception as e:
            error_msg = str(e)
            if 'already registered' in error_msg or 'already exists' in error_msg:
                flash('An account with this email already exists.', 'danger')
            elif 'duplicate key' in error_msg and 'admission_number' in error_msg:
                flash('This admission number is already registered.', 'danger')
            else:
                flash(f'Registration failed: {error_msg[:100]}', 'danger')

    # GET request - load form data
    try:
        sb = get_supabase()
        courses = sb.table('courses').select('*').eq('is_active', True).execute().data or []
        departments = sb.table('departments').select('*').execute().data or []
    except Exception:
        courses = []
        departments = []

    return render_template('auth/register.html', courses=courses, departments=departments, form_data={})


@auth.route('/logout')
def logout():
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = session.get('user')
    sb = get_supabase()

    if request.method == 'POST':
        update_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'county_region': request.form.get('county_region', '').strip(),
            'emergency_contact': request.form.get('emergency_contact', '').strip(),
            'emergency_phone': request.form.get('emergency_phone', '').strip(),
        }
        try:
            sb_admin = get_supabase_admin()
            sb_admin.table('profiles').update(update_data).eq('id', user['id']).execute()
            session['user']['full_name'] = update_data['full_name']
            flash('Profile updated successfully.', 'success')
        except Exception as e:
            flash('Failed to update profile.', 'danger')
        return redirect(url_for('auth.profile'))

    try:
        profile_data = sb.table('profiles').select('*').eq('id', user['id']).single().execute().data or {}
        trainee_data = sb.table('trainees').select('*, courses(*), departments(*)').eq('profile_id', user['id']).single().execute().data or {}
    except Exception:
        profile_data = {}
        trainee_data = {}

    return render_template('auth/profile.html', profile=profile_data, trainee=trainee_data)
