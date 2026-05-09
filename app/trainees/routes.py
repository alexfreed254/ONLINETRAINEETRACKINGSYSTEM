from flask import render_template, session, redirect, url_for, flash, request
from app.trainees import trainees
from app.auth.routes import login_required, institute_required
from app.supabase_client import get_supabase_admin
from datetime import datetime


@trainees.route('/')
@institute_required
def index():
    user = session.get('user')
    sb = get_supabase_admin()

    search = request.args.get('search', '')
    department_id = request.args.get('department', '')
    course_id = request.args.get('course', '')
    status = request.args.get('status', '')
    page = int(request.args.get('page', 1))
    per_page = 16

    all_trainees = []
    departments = []
    courses = []

    try:
        query = sb.table('trainees').select(
            '*, profiles(full_name, profile_photo_url, email, phone, county_region, gender), '
            'courses(name, code), departments(name, code)'
        )

        if status:
            query = query.eq('status', status)
        if department_id:
            query = query.eq('department_id', department_id)
        if course_id:
            query = query.eq('course_id', course_id)

        all_trainees = query.order('created_at', desc=True).execute().data or []

        if search:
            q = search.lower()
            all_trainees = [
                t for t in all_trainees
                if q in (t.get('profiles') or {}).get('full_name', '').lower()
                or q in t.get('admission_number', '').lower()
                or q in (t.get('profiles') or {}).get('email', '').lower()
                or q in ((t.get('profiles') or {}).get('national_id') or '').lower()
            ]

        departments = sb.table('departments').select('*').execute().data or []
        courses = sb.table('courses').select('*').execute().data or []

    except Exception as e:
        flash(f'Error loading trainees: {str(e)[:80]}', 'danger')

    total = len(all_trainees)
    start = (page - 1) * per_page
    paginated = all_trainees[start:start + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template('trainees/index.html',
                           trainees=paginated,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           departments=departments,
                           courses=courses,
                           search=search,
                           current_department=department_id,
                           current_course=course_id,
                           current_status=status,
                           user=user)


@trainees.route('/<trainee_id>')
@login_required
def detail(trainee_id):
    user = session.get('user')
    sb = get_supabase_admin()

    try:
        rows = sb.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).execute().data or []
        trainee = rows[0] if rows else None

        if not trainee:
            flash('Trainee not found.', 'danger')
            return redirect(url_for('trainees.index'))

        academic = sb.table('academic_records').select(
            '*, profiles(full_name)'
        ).eq('trainee_id', trainee_id).order('semester').execute().data or []

        media = sb.table('media_uploads').select('*').eq(
            'trainee_id', trainee_id
        ).order('created_at', desc=True).execute().data or []

        competencies = sb.table('trainee_competencies').select(
            '*, competencies(*), profiles(full_name)'
        ).eq('trainee_id', trainee_id).execute().data or []

        internships_data = sb.table('internships').select('*').eq(
            'trainee_id', trainee_id
        ).order('start_date', desc=True).execute().data or []

        certs = sb.table('certifications').select('*').eq(
            'trainee_id', trainee_id
        ).execute().data or []

        att_total = sb.table('attendance').select('id', count='exact').eq('trainee_id', trainee_id).execute().count or 0
        att_present = sb.table('attendance').select('id', count='exact').eq('trainee_id', trainee_id).eq('status', 'present').execute().count or 0
        attendance_rate = round(att_present / att_total * 100, 1) if att_total > 0 else 0

        verifications = sb.table('employer_verifications').select('*').eq(
            'trainee_id', trainee_id
        ).order('created_at', desc=True).execute().data or []

        stats = {
            'media_count': len(media),
            'competencies_verified': len([c for c in competencies if c.get('status') == 'verified']),
            'attendance_rate': attendance_rate,
            'certifications': len(certs),
            'internships': len(internships_data),
        }

    except Exception as e:
        flash(f'Error loading trainee: {str(e)[:100]}', 'danger')
        return redirect(url_for('trainees.index'))

    return render_template('trainees/detail.html',
                           trainee=trainee,
                           academic=academic,
                           media=media,
                           competencies=competencies,
                           internships=internships_data,
                           certifications=certs,
                           verifications=verifications,
                           stats=stats,
                           user=user)


@trainees.route('/<trainee_id>/academic', methods=['POST'])
@login_required
def academic(trainee_id):
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        flash('Permission denied.', 'danger')
        return redirect(url_for('trainees.detail', trainee_id=trainee_id))

    sb = get_supabase_admin()
    data = {
        'trainee_id': trainee_id,
        'semester': int(request.form.get('semester', 1)),
        'academic_year': request.form.get('academic_year', ''),
        'unit_name': request.form.get('unit_name', ''),
        'unit_code': request.form.get('unit_code', ''),
        'grade': request.form.get('grade', ''),
        'score': float(request.form.get('score')) if request.form.get('score') else None,
        'status': request.form.get('status', 'enrolled'),
        'instructor_id': user['id'],
        'remarks': request.form.get('remarks', ''),
    }
    try:
        sb.table('academic_records').insert(data).execute()
        flash('Academic record added successfully.', 'success')
    except Exception:
        flash('Failed to add record.', 'danger')
    return redirect(url_for('trainees.detail', trainee_id=trainee_id))


@trainees.route('/<trainee_id>/attendance', methods=['POST'])
@login_required
def add_attendance(trainee_id):
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        flash('Permission denied.', 'danger')
        return redirect(url_for('trainees.detail', trainee_id=trainee_id))

    sb = get_supabase_admin()
    try:
        sb.table('attendance').insert({
            'trainee_id': trainee_id,
            'date': request.form.get('date'),
            'status': request.form.get('status', 'present'),
            'session': request.form.get('session', ''),
            'instructor_id': user['id'],
            'notes': request.form.get('notes', ''),
        }).execute()
        flash('Attendance recorded.', 'success')
    except Exception:
        flash('Failed to record attendance.', 'danger')
    return redirect(url_for('trainees.detail', trainee_id=trainee_id))


@trainees.route('/<trainee_id>/internship', methods=['POST'])
@login_required
def add_internship(trainee_id):
    sb = get_supabase_admin()
    try:
        sb.table('internships').insert({
            'trainee_id': trainee_id,
            'company_name': request.form.get('company_name', ''),
            'supervisor_name': request.form.get('supervisor_name', ''),
            'supervisor_email': request.form.get('supervisor_email', ''),
            'supervisor_phone': request.form.get('supervisor_phone', ''),
            'start_date': request.form.get('start_date') or None,
            'end_date': request.form.get('end_date') or None,
            'location_name': request.form.get('location_name', ''),
            'status': 'active',
            'description': request.form.get('description', ''),
        }).execute()
        flash('Internship record added.', 'success')
    except Exception:
        flash('Failed to add internship.', 'danger')
    return redirect(url_for('trainees.detail', trainee_id=trainee_id))


@trainees.route('/edit/<trainee_id>', methods=['GET', 'POST'])
@institute_required
def edit(trainee_id):
    user = session.get('user')
    sb = get_supabase_admin()

    if request.method == 'POST':
        try:
            rows = sb.table('trainees').select('profile_id').eq('id', trainee_id).execute().data or []
            if not rows:
                flash('Trainee not found.', 'danger')
                return redirect(url_for('trainees.index'))
            profile_id = rows[0]['profile_id']

            sb.table('profiles').update({
                'full_name': request.form.get('full_name', ''),
                'phone': request.form.get('phone', ''),
                'gender': request.form.get('gender', ''),
                'county_region': request.form.get('county_region', ''),
                'emergency_contact': request.form.get('emergency_contact', ''),
                'emergency_phone': request.form.get('emergency_phone', ''),
            }).eq('id', profile_id).execute()

            sb.table('trainees').update({
                'course_id': request.form.get('course_id') or None,
                'department_id': request.form.get('department_id') or None,
                'intake_year': int(request.form.get('intake_year')) if request.form.get('intake_year') else None,
                'graduation_year': int(request.form.get('graduation_year')) if request.form.get('graduation_year') else None,
                'current_semester': int(request.form.get('current_semester', 1)),
                'status': request.form.get('status', 'active'),
            }).eq('id', trainee_id).execute()

            flash('Trainee updated successfully.', 'success')
        except Exception as e:
            flash(f'Update failed: {str(e)[:80]}', 'danger')
        return redirect(url_for('trainees.detail', trainee_id=trainee_id))

    try:
        rows = sb.table('trainees').select('*, profiles(*), courses(*), departments(*)').eq('id', trainee_id).execute().data or []
        trainee = rows[0] if rows else None
        if not trainee:
            flash('Trainee not found.', 'danger')
            return redirect(url_for('trainees.index'))
        courses = sb.table('courses').select('*').execute().data or []
        departments = sb.table('departments').select('*').execute().data or []
    except Exception:
        flash('Error loading trainee.', 'danger')
        return redirect(url_for('trainees.index'))

    return render_template('trainees/edit.html',
                           trainee=trainee, courses=courses,
                           departments=departments, user=user)
