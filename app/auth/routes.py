from flask import render_template, redirect, url_for, flash, request, session, current_app
from app.auth import auth
from app.supabase_client import get_supabase, get_supabase_admin
from functools import wraps


# ─────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = session.get('user')
            if not user:
                flash('Please log in.', 'warning')
                return redirect(url_for('auth.login'))
            if user.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.smart_redirect'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def trainee_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return redirect(url_for('auth.trainee_login'))
        if user.get('role') != 'trainee':
            flash('Trainee access only.', 'danger')
            return redirect(url_for('auth.smart_redirect'))
        return f(*args, **kwargs)
    return decorated


def institute_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return redirect(url_for('auth.institute_login'))
        if user.get('role') not in ('admin', 'instructor'):
            flash('Institute staff access only.', 'danger')
            return redirect(url_for('auth.smart_redirect'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# Smart redirect based on role
# ─────────────────────────────────────────────

@auth.route('/redirect')
def smart_redirect():
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    role = user.get('role')
    if role == 'trainee':
        return redirect(url_for('trainee_dash.index'))
    elif role in ('admin', 'instructor'):
        return redirect(url_for('dashboard.index'))
    elif role == 'employer':
        return redirect(url_for('employer.index'))
    return redirect(url_for('auth.login'))


# ─────────────────────────────────────────────
# Landing / portal selector
# ─────────────────────────────────────────────

@auth.route('/login')
def login():
    """Portal selector — redirects to correct login."""
    if session.get('user'):
        return redirect(url_for('auth.smart_redirect'))
    return render_template('auth/portal.html')


# ─────────────────────────────────────────────
# Trainee Login
# ─────────────────────────────────────────────

@auth.route('/trainee/login', methods=['GET', 'POST'])
def trainee_login():
    if session.get('user'):
        return redirect(url_for('auth.smart_redirect'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/trainee_login.html')

        try:
            sb = get_supabase()
            response = sb.auth.sign_in_with_password({'email': email, 'password': password})

            if response.user:
                profile_resp = sb.table('profiles').select('*').eq('id', response.user.id).single().execute()
                profile = profile_resp.data or {}

                if profile.get('role') != 'trainee':
                    sb.auth.sign_out()
                    flash('This portal is for trainees only. Use the Institute login.', 'warning')
                    return render_template('auth/trainee_login.html')

                session['user'] = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'role': 'trainee',
                    'full_name': profile.get('full_name', email),
                    'profile_photo_url': profile.get('profile_photo_url', ''),
                }
                session.permanent = True
                flash(f'Welcome back, {profile.get("full_name", email)}!', 'success')
                return redirect(url_for('trainee_dash.index'))
            else:
                flash('Invalid email or password.', 'danger')
        except Exception as e:
            err = str(e)
            if 'Invalid login credentials' in err:
                flash('Invalid email or password.', 'danger')
            elif 'Email not confirmed' in err:
                flash('Please confirm your email address first.', 'warning')
            else:
                flash('Login failed. Please try again.', 'danger')

    return render_template('auth/trainee_login.html')


# ─────────────────────────────────────────────
# Institute Login (admin / instructor)
# ─────────────────────────────────────────────

@auth.route('/institute/login', methods=['GET', 'POST'])
def institute_login():
    if session.get('user'):
        return redirect(url_for('auth.smart_redirect'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/institute_login.html')

        try:
            sb = get_supabase()
            response = sb.auth.sign_in_with_password({'email': email, 'password': password})

            if response.user:
                profile_resp = sb.table('profiles').select('*').eq('id', response.user.id).single().execute()
                profile = profile_resp.data or {}

                if profile.get('role') not in ('admin', 'instructor'):
                    sb.auth.sign_out()
                    flash('This portal is for institute staff only. Use the Trainee login.', 'warning')
                    return render_template('auth/institute_login.html')

                session['user'] = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'role': profile.get('role'),
                    'full_name': profile.get('full_name', email),
                    'profile_photo_url': profile.get('profile_photo_url', ''),
                }
                session.permanent = True
                flash(f'Welcome, {profile.get("full_name", email)}!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid credentials.', 'danger')
        except Exception as e:
            err = str(e)
            if 'Invalid login credentials' in err:
                flash('Invalid email or password.', 'danger')
            else:
                flash('Login failed. Please try again.', 'danger')

    return render_template('auth/institute_login.html')


# ─────────────────────────────────────────────
# Forgot Password
# ─────────────────────────────────────────────

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('auth/forgot_password.html')
        try:
            sb = get_supabase()
            # Build the reset URL pointing back to our reset page
            redirect_url = request.host_url.rstrip('/') + url_for('auth.reset_password')
            sb.auth.reset_password_email(email, options={'redirect_to': redirect_url})
            flash('Password reset email sent! Check your inbox (and spam folder).', 'success')
            return redirect(url_for('auth.trainee_login'))
        except Exception as e:
            # Always show success to prevent email enumeration
            flash('If that email exists, a reset link has been sent.', 'info')
            return redirect(url_for('auth.trainee_login'))

    return render_template('auth/forgot_password.html')


# ─────────────────────────────────────────────
# Reset Password (from email link)
# ─────────────────────────────────────────────

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        access_token = request.form.get('access_token', '')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/reset_password.html', access_token=access_token)
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', access_token=access_token)

        try:
            sb = get_supabase()
            # Use the access token from the reset email
            sb.auth.update_user({'password': password})
            flash('Password updated successfully! Please log in.', 'success')
            return redirect(url_for('auth.trainee_login'))
        except Exception as e:
            flash('Reset failed. The link may have expired. Request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))

    # GET — token comes as URL fragment (#access_token=...) handled by JS
    access_token = request.args.get('access_token', '')
    return render_template('auth/reset_password.html', access_token=access_token)


# ─────────────────────────────────────────────
# Change Password (logged-in trainee)
# ─────────────────────────────────────────────

@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user = session.get('user')
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if len(new_pw) < 8:
        flash('New password must be at least 8 characters.', 'danger')
        return redirect(url_for('trainee_dash.settings'))
    if new_pw != confirm_pw:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('trainee_dash.settings'))

    try:
        # Re-authenticate to verify current password
        sb = get_supabase()
        sb.auth.sign_in_with_password({'email': user['email'], 'password': current_pw})
        # Update password
        sb_admin = get_supabase_admin()
        sb_admin.auth.admin.update_user_by_id(user['id'], {'password': new_pw})
        flash('Password changed successfully!', 'success')
    except Exception as e:
        err = str(e)
        if 'Invalid login credentials' in err:
            flash('Current password is incorrect.', 'danger')
        else:
            flash('Password change failed. Please try again.', 'danger')

    return redirect(url_for('trainee_dash.settings'))


# ─────────────────────────────────────────────
# Register (Trainee self-registration)
# ─────────────────────────────────────────────

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('auth.smart_redirect'))

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
            sb_admin = get_supabase_admin()
            courses = sb_admin.table('courses').select('id, name, code, department_id').eq('is_active', True).order('name').execute().data or []
            departments = sb_admin.table('departments').select('id, name, code').order('name').execute().data or []
            return render_template('auth/register.html', courses=courses, departments=departments, form_data=data)

        try:
            sb_admin = get_supabase_admin()
            auth_response = sb_admin.auth.admin.create_user({
                'email': data['email'],
                'password': data['password'],
                'email_confirm': True,
                'user_metadata': {'full_name': data['full_name']}
            })

            if auth_response.user:
                user_id = auth_response.user.id
                sb_admin.table('profiles').insert({
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
                }).execute()

                sb_admin.table('trainees').insert({
                    'profile_id': user_id,
                    'admission_number': data['admission_number'],
                    'course_id': data['course_id'] or None,
                    'department_id': data['department_id'] or None,
                    'intake_year': int(data['intake_year']) if data['intake_year'] else None,
                    'graduation_year': int(data['graduation_year']) if data['graduation_year'] else None,
                    'status': 'active',
                }).execute()

                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth.trainee_login'))
            else:
                flash('Registration failed. Please try again.', 'danger')

        except Exception as e:
            err = str(e)
            if 'already registered' in err or 'already exists' in err:
                flash('An account with this email already exists.', 'danger')
            elif 'duplicate key' in err and 'admission_number' in err:
                flash('This admission number is already registered.', 'danger')
            else:
                flash(f'Registration failed: {err[:120]}', 'danger')

    try:
        sb_admin = get_supabase_admin()
        courses = sb_admin.table('courses').select('id, name, code, department_id').eq('is_active', True).order('name').execute().data or []
        departments = sb_admin.table('departments').select('id, name, code').order('name').execute().data or []
    except Exception:
        courses = []
        departments = []

    return render_template('auth/register.html', courses=courses, departments=departments, form_data={})


# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────

@auth.route('/logout')
def logout():
    role = session.get('user', {}).get('role', '')
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    session.clear()
    flash('You have been logged out.', 'info')
    if role == 'trainee':
        return redirect(url_for('auth.trainee_login'))
    return redirect(url_for('auth.institute_login'))


# ─────────────────────────────────────────────
# Profile (shared)
# ─────────────────────────────────────────────

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
        except Exception:
            flash('Failed to update profile.', 'danger')
        return redirect(url_for('auth.profile'))

    try:
        profile_data = sb.table('profiles').select('*').eq('id', user['id']).single().execute().data or {}
        trainee_data = sb.table('trainees').select('*, courses(*), departments(*)').eq('profile_id', user['id']).single().execute().data or {}
    except Exception:
        profile_data = {}
        trainee_data = {}

    return render_template('auth/profile.html', profile=profile_data, trainee=trainee_data)
