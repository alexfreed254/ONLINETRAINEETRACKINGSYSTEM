from flask import render_template, session, redirect, url_for, request, jsonify
from app.dashboard import dashboard
from app.auth.routes import login_required, institute_required
from app.supabase_client import get_supabase_admin
from datetime import datetime


@dashboard.route('/')
@institute_required
def index():
    user = session.get('user')
    sb = get_supabase_admin()

    stats = {'total_trainees': 0, 'media_today': 0, 'verified_skills': 0,
             'active_internships': 0, 'total_media': 0, 'graduated': 0}
    recent_media = []
    top_departments = []
    recent_trainees = []
    internship_locations = []

    try:
        today = datetime.now().date().isoformat()

        stats['total_trainees'] = sb.table('trainees').select('id', count='exact').eq('status', 'active').execute().count or 0
        stats['media_today'] = sb.table('media_uploads').select('id', count='exact').gte('created_at', today).execute().count or 0
        stats['verified_skills'] = sb.table('trainee_competencies').select('id', count='exact').eq('status', 'verified').execute().count or 0
        stats['active_internships'] = sb.table('internships').select('id', count='exact').eq('status', 'active').execute().count or 0
        stats['total_media'] = sb.table('media_uploads').select('id', count='exact').execute().count or 0
        stats['graduated'] = sb.table('trainees').select('id', count='exact').eq('status', 'graduated').execute().count or 0

        recent_media = sb.table('media_uploads').select(
            '*, trainees(*, profiles(full_name, profile_photo_url, county_region))'
        ).eq('approval_status', 'approved').order('created_at', desc=True).limit(20).execute().data or []

        recent_trainees = sb.table('trainees').select(
            '*, profiles(full_name, profile_photo_url, county_region, email), courses(name), departments(name)'
        ).order('created_at', desc=True).limit(8).execute().data or []

        departments = sb.table('departments').select('id, name').execute().data or []
        for dept in departments:
            dept['trainee_count'] = sb.table('trainees').select('id', count='exact').eq('department_id', dept['id']).execute().count or 0
        top_departments = sorted(departments, key=lambda x: x['trainee_count'], reverse=True)[:6]

        internship_locations = sb.table('internships').select(
            'company_name, location_name, latitude, longitude, status, trainees(profiles(full_name))'
        ).not_.is_('latitude', 'null').execute().data or []

    except Exception:
        pass

    return render_template('dashboard/index.html',
                           stats=stats,
                           recent_media=recent_media,
                           top_departments=top_departments,
                           recent_trainees=recent_trainees,
                           internship_locations=internship_locations,
                           user=user)


@dashboard.route('/feed')
@institute_required
def live_feed():
    user = session.get('user')
    sb = get_supabase_admin()

    department_id = request.args.get('department')
    category = request.args.get('category')
    page = int(request.args.get('page', 1))
    per_page = 12

    media = []
    departments = []
    categories = ['Workshop', 'Internship', 'Project', 'Assessment', 'Innovation', 'Field Work']

    try:
        query = sb.table('media_uploads').select(
            '*, trainees(*, profiles(full_name, profile_photo_url, county_region), departments(name), courses(name))'
        ).eq('approval_status', 'approved')

        if category:
            query = query.eq('category', category)

        media = query.order('created_at', desc=True).range(
            (page - 1) * per_page, page * per_page - 1
        ).execute().data or []

        if department_id:
            media = [m for m in media if (m.get('trainees') or {}).get('department_id') == department_id]

        departments = sb.table('departments').select('*').execute().data or []

    except Exception:
        pass

    return render_template('dashboard/live_feed.html',
                           media=media,
                           departments=departments,
                           categories=categories,
                           current_department=department_id,
                           current_category=category,
                           page=page,
                           user=user)


@dashboard.route('/api/stats')
@login_required
def api_stats():
    sb = get_supabase_admin()
    try:
        today = datetime.now().date().isoformat()
        return jsonify({
            'total_trainees': sb.table('trainees').select('id', count='exact').eq('status', 'active').execute().count or 0,
            'media_today': sb.table('media_uploads').select('id', count='exact').gte('created_at', today).execute().count or 0,
            'verified_skills': sb.table('trainee_competencies').select('id', count='exact').eq('status', 'verified').execute().count or 0,
            'active_internships': sb.table('internships').select('id', count='exact').eq('status', 'active').execute().count or 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard.route('/map')
@institute_required
def geo_map():
    user = session.get('user')
    sb = get_supabase_admin()

    internships = []
    media_locations = []

    try:
        internships = sb.table('internships').select(
            '*, trainees(profiles(full_name, county_region), courses(name), departments(name))'
        ).not_.is_('latitude', 'null').execute().data or []

        media_locations = sb.table('media_uploads').select(
            'title, location_name, latitude, longitude, skill_tags, trainees(profiles(full_name))'
        ).not_.is_('latitude', 'null').eq('approval_status', 'approved').execute().data or []

    except Exception:
        pass

    return render_template('dashboard/map.html',
                           internships=internships,
                           media_locations=media_locations,
                           user=user)
