from flask import render_template, session, redirect, url_for, request, jsonify
from app.dashboard import dashboard
from app.auth.routes import login_required
from app.supabase_client import get_supabase, get_supabase_admin
from datetime import datetime, timedelta


@dashboard.route('/')
@login_required
def index():
    user = session.get('user')
    sb = get_supabase()

    stats = {}
    recent_media = []
    top_departments = []
    recent_trainees = []
    internship_locations = []

    try:
        # Total active trainees
        trainees_resp = sb.table('trainees').select('id', count='exact').eq('status', 'active').execute()
        stats['total_trainees'] = trainees_resp.count or 0

        # Media uploaded today
        today = datetime.now().date().isoformat()
        media_today = sb.table('media_uploads').select('id', count='exact').gte('created_at', today).execute()
        stats['media_today'] = media_today.count or 0

        # Total verified skills
        verified_skills = sb.table('trainee_competencies').select('id', count='exact').eq('status', 'verified').execute()
        stats['verified_skills'] = verified_skills.count or 0

        # Active internships
        active_internships = sb.table('internships').select('id', count='exact').eq('status', 'active').execute()
        stats['active_internships'] = active_internships.count or 0

        # Total media uploads
        total_media = sb.table('media_uploads').select('id', count='exact').execute()
        stats['total_media'] = total_media.count or 0

        # Graduated trainees
        graduated = sb.table('trainees').select('id', count='exact').eq('status', 'graduated').execute()
        stats['graduated'] = graduated.count or 0

        # Recent approved media for live feed
        recent_media = sb.table('media_uploads').select(
            '*, trainees(*, profiles(full_name, profile_photo_url, county_region))'
        ).eq('approval_status', 'approved').order('created_at', desc=True).limit(20).execute().data or []

        # Recent trainees
        recent_trainees = sb.table('trainees').select(
            '*, profiles(full_name, profile_photo_url, county_region, email), courses(name), departments(name)'
        ).order('created_at', desc=True).limit(8).execute().data or []

        # Department stats
        departments = sb.table('departments').select('id, name').execute().data or []
        for dept in departments:
            count_resp = sb.table('trainees').select('id', count='exact').eq('department_id', dept['id']).execute()
            dept['trainee_count'] = count_resp.count or 0
        top_departments = sorted(departments, key=lambda x: x['trainee_count'], reverse=True)[:6]

        # Internship locations for map
        internship_locations = sb.table('internships').select(
            'company_name, location_name, latitude, longitude, status, trainees(profiles(full_name))'
        ).not_.is_('latitude', 'null').execute().data or []

    except Exception as e:
        stats = {
            'total_trainees': 0, 'media_today': 0, 'verified_skills': 0,
            'active_internships': 0, 'total_media': 0, 'graduated': 0
        }

    return render_template('dashboard/index.html',
                           stats=stats,
                           recent_media=recent_media,
                           top_departments=top_departments,
                           recent_trainees=recent_trainees,
                           internship_locations=internship_locations,
                           user=user)


@dashboard.route('/feed')
@login_required
def live_feed():
    """Live activity feed with filters."""
    user = session.get('user')
    sb = get_supabase()

    # Filters
    department_id = request.args.get('department')
    category = request.args.get('category')
    skill_tag = request.args.get('skill')
    page = int(request.args.get('page', 1))
    per_page = 12

    try:
        query = sb.table('media_uploads').select(
            '*, trainees(*, profiles(full_name, profile_photo_url, county_region), departments(name), courses(name))'
        ).eq('approval_status', 'approved')

        if category:
            query = query.eq('category', category)

        media = query.order('created_at', desc=True).range(
            (page - 1) * per_page, page * per_page - 1
        ).execute().data or []

        # Filter by department if specified
        if department_id:
            media = [m for m in media if m.get('trainees', {}).get('department_id') == department_id]

        departments = sb.table('departments').select('*').execute().data or []
        categories = ['Workshop', 'Internship', 'Project', 'Assessment', 'Innovation', 'Field Work']

    except Exception as e:
        media = []
        departments = []
        categories = []

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
    """API endpoint for real-time stats."""
    sb = get_supabase()
    try:
        today = datetime.now().date().isoformat()
        trainees = sb.table('trainees').select('id', count='exact').eq('status', 'active').execute()
        media_today = sb.table('media_uploads').select('id', count='exact').gte('created_at', today).execute()
        verified = sb.table('trainee_competencies').select('id', count='exact').eq('status', 'verified').execute()
        internships = sb.table('internships').select('id', count='exact').eq('status', 'active').execute()

        return jsonify({
            'total_trainees': trainees.count or 0,
            'media_today': media_today.count or 0,
            'verified_skills': verified.count or 0,
            'active_internships': internships.count or 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard.route('/map')
@login_required
def geo_map():
    """GIS Skill Deployment Map."""
    user = session.get('user')
    sb = get_supabase()

    try:
        internships = sb.table('internships').select(
            '*, trainees(profiles(full_name, county_region), courses(name), departments(name))'
        ).not_.is_('latitude', 'null').execute().data or []

        media_locations = sb.table('media_uploads').select(
            'title, location_name, latitude, longitude, skill_tags, trainees(profiles(full_name))'
        ).not_.is_('latitude', 'null').eq('approval_status', 'approved').execute().data or []

    except Exception:
        internships = []
        media_locations = []

    return render_template('dashboard/map.html',
                           internships=internships,
                           media_locations=media_locations,
                           user=user)
