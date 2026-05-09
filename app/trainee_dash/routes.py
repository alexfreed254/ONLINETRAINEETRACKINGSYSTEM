from flask import render_template, session, redirect, url_for, flash, request
from app.trainee_dash import trainee_dash
from app.auth.routes import trainee_required
from app.supabase_client import get_supabase, get_supabase_admin


def _get_trainee(user_id):
    """Fetch trainee record using admin client (bypasses RLS)."""
    try:
        sb = get_supabase_admin()
        result = sb.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('profile_id', user_id).single().execute()
        return result.data
    except Exception:
        return None


def _trainee_not_found():
    """Show a friendly error instead of logging the user out."""
    flash(
        'Your trainee profile was not found. '
        'Please contact the institute to complete your registration.',
        'warning'
    )
    return render_template('trainee_dash/no_profile.html'), 200


# ─────────────────────────────────────────────
# Trainee Dashboard Home
# ─────────────────────────────────────────────

@trainee_dash.route('/')
@trainee_required
def index():
    user = session.get('user')
    trainee = _get_trainee(user['id'])

    if not trainee:
        return _trainee_not_found()

    stats = {
        'total_media': 0, 'approved_media': 0, 'pending_media': 0,
        'verified_skills': 0, 'internships': 0, 'attendance_rate': 0
    }
    recent_media = []
    academic = []
    internships = []

    try:
        sb = get_supabase_admin()
        tid = trainee['id']

        stats['total_media'] = sb.table('media_uploads').select('id', count='exact').eq('trainee_id', tid).execute().count or 0
        stats['approved_media'] = sb.table('media_uploads').select('id', count='exact').eq('trainee_id', tid).eq('approval_status', 'approved').execute().count or 0
        stats['pending_media'] = sb.table('media_uploads').select('id', count='exact').eq('trainee_id', tid).eq('approval_status', 'pending').execute().count or 0
        stats['verified_skills'] = sb.table('trainee_competencies').select('id', count='exact').eq('trainee_id', tid).eq('status', 'verified').execute().count or 0
        stats['internships'] = sb.table('internships').select('id', count='exact').eq('trainee_id', tid).execute().count or 0

        att_total = sb.table('attendance').select('id', count='exact').eq('trainee_id', tid).execute().count or 0
        att_present = sb.table('attendance').select('id', count='exact').eq('trainee_id', tid).eq('status', 'present').execute().count or 0
        stats['attendance_rate'] = round(att_present / att_total * 100, 1) if att_total > 0 else 0

        recent_media = sb.table('media_uploads').select('*').eq('trainee_id', tid).order('created_at', desc=True).limit(6).execute().data or []
        academic = sb.table('academic_records').select('*').eq('trainee_id', tid).order('semester').limit(5).execute().data or []
        internships = sb.table('internships').select('*').eq('trainee_id', tid).order('start_date', desc=True).limit(3).execute().data or []

    except Exception:
        pass

    return render_template('trainee_dash/index.html',
                           user=user, trainee=trainee,
                           stats=stats, recent_media=recent_media,
                           academic=academic, internships=internships)


# ─────────────────────────────────────────────
# My Evidence / Media
# ─────────────────────────────────────────────

@trainee_dash.route('/evidence')
@trainee_required
def evidence():
    user = session.get('user')
    trainee = _get_trainee(user['id'])
    if not trainee:
        return _trainee_not_found()

    category = request.args.get('category', '')
    status_filter = request.args.get('status', '')

    try:
        sb = get_supabase_admin()
        query = sb.table('media_uploads').select('*').eq('trainee_id', trainee['id'])
        if category:
            query = query.eq('category', category)
        if status_filter:
            query = query.eq('approval_status', status_filter)
        media = query.order('created_at', desc=True).execute().data or []
    except Exception:
        media = []

    from app.media.routes import SKILL_CATEGORIES
    return render_template('trainee_dash/evidence.html',
                           user=user, trainee=trainee, media=media,
                           categories=SKILL_CATEGORIES,
                           current_category=category,
                           current_status=status_filter)


# ─────────────────────────────────────────────
# My Academic Progress
# ─────────────────────────────────────────────

@trainee_dash.route('/progress')
@trainee_required
def progress():
    user = session.get('user')
    trainee = _get_trainee(user['id'])
    if not trainee:
        return _trainee_not_found()

    academic = []
    competencies = []
    certifications = []
    internships = []
    att_total = []
    att_rate = 0

    try:
        sb = get_supabase_admin()
        tid = trainee['id']
        academic = sb.table('academic_records').select('*').eq('trainee_id', tid).order('semester').execute().data or []
        competencies = sb.table('trainee_competencies').select('*, competencies(*)').eq('trainee_id', tid).execute().data or []
        certifications = sb.table('certifications').select('*').eq('trainee_id', tid).execute().data or []
        internships = sb.table('internships').select('*').eq('trainee_id', tid).order('start_date', desc=True).execute().data or []
        att_total = sb.table('attendance').select('id, status, date').eq('trainee_id', tid).order('date', desc=True).execute().data or []
        present = len([a for a in att_total if a['status'] == 'present'])
        att_rate = round(present / len(att_total) * 100, 1) if att_total else 0
    except Exception:
        pass

    return render_template('trainee_dash/progress.html',
                           user=user, trainee=trainee,
                           academic=academic, competencies=competencies,
                           certifications=certifications, internships=internships,
                           attendance=att_total, att_rate=att_rate)


# ─────────────────────────────────────────────
# Settings (profile + password)
# ─────────────────────────────────────────────

@trainee_dash.route('/settings', methods=['GET', 'POST'])
@trainee_required
def settings():
    user = session.get('user')
    trainee = _get_trainee(user['id'])
    if not trainee:
        return _trainee_not_found()

    if request.method == 'POST':
        action = request.form.get('action', 'profile')
        if action == 'profile':
            update_data = {
                'full_name': request.form.get('full_name', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'county_region': request.form.get('county_region', '').strip(),
                'emergency_contact': request.form.get('emergency_contact', '').strip(),
                'emergency_phone': request.form.get('emergency_phone', '').strip(),
            }
            try:
                sb = get_supabase_admin()
                sb.table('profiles').update(update_data).eq('id', user['id']).execute()
                session['user']['full_name'] = update_data['full_name']
                flash('Profile updated successfully.', 'success')
            except Exception:
                flash('Failed to update profile.', 'danger')
        return redirect(url_for('trainee_dash.settings'))

    try:
        sb = get_supabase_admin()
        profile_data = sb.table('profiles').select('*').eq('id', user['id']).single().execute().data or {}
    except Exception:
        profile_data = {}

    return render_template('trainee_dash/settings.html',
                           user=user, trainee=trainee, profile=profile_data)


# ─────────────────────────────────────────────
# My Portfolio (public link)
# ─────────────────────────────────────────────

@trainee_dash.route('/portfolio')
@trainee_required
def my_portfolio():
    user = session.get('user')
    trainee = _get_trainee(user['id'])
    if not trainee:
        return _trainee_not_found()
    return redirect(url_for('portfolio.view', trainee_id=trainee['id']))
