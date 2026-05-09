from flask import render_template, session, redirect, url_for, flash, request, jsonify
from app.employer import employer
from app.auth.routes import login_required
from app.supabase_client import get_supabase, get_supabase_admin
from datetime import datetime


@employer.route('/')
@login_required
def index():
    user = session.get('user')
    sb = get_supabase()

    current_status = request.args.get('status', '')

    try:
        query = sb.table('employer_verifications').select(
            '*, trainees(*, profiles(full_name, profile_photo_url), departments(name), courses(name))'
        )
        if current_status:
            query = query.eq('status', current_status)

        verifications = query.order('created_at', desc=True).execute().data or []

        # Stats
        all_v = sb.table('employer_verifications').select('id, status').execute().data or []
        stats = {
            'total': len(all_v),
            'pending': len([v for v in all_v if v['status'] == 'pending']),
            'verified': len([v for v in all_v if v['status'] == 'verified']),
            'rejected': len([v for v in all_v if v['status'] == 'rejected']),
        }
    except Exception as e:
        verifications = []
        stats = {'total': 0, 'pending': 0, 'verified': 0, 'rejected': 0}

    return render_template('employer/index.html',
                           verifications=verifications,
                           stats=stats,
                           current_status=current_status,
                           user=user)


@employer.route('/verify/<trainee_id>', methods=['GET'])
def verify(trainee_id):
    """Public-facing verification form — no login required for employers."""
    sb = get_supabase()
    user = session.get('user')

    try:
        trainee = sb.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).single().execute().data
    except Exception:
        trainee = None

    return render_template('employer/verify.html', trainee=trainee, user=user)


@employer.route('/verify/<trainee_id>/submit', methods=['POST'])
def submit_verification(trainee_id):
    """Submit employer verification."""
    sb_admin = get_supabase_admin()

    data = {
        'trainee_id': trainee_id,
        'employer_name': request.form.get('employer_name', '').strip(),
        'employer_email': request.form.get('employer_email', '').strip(),
        'employer_company': request.form.get('employer_company', '').strip(),
        'verification_type': request.form.get('verification_type', 'internship'),
        'status': request.form.get('status', 'pending'),
        'rating': int(request.form.get('rating', 0)) if request.form.get('rating') else None,
        'comments': request.form.get('comments', '').strip(),
    }

    if not data['employer_name'] or not data['employer_email']:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('employer.verify', trainee_id=trainee_id))

    try:
        sb_admin.table('employer_verifications').insert(data).execute()
        flash('Verification submitted successfully. Thank you!', 'success')
        return redirect(url_for('portfolio.view', trainee_id=trainee_id))
    except Exception as e:
        flash(f'Submission failed: {str(e)[:100]}', 'danger')
        return redirect(url_for('employer.verify', trainee_id=trainee_id))


@employer.route('/verification/<verification_id>/update', methods=['POST'])
@login_required
def update_verification(verification_id):
    """Admin/instructor updates verification status."""
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
        flash(f'Verification status updated to {new_status}.', 'success')
    except Exception as e:
        flash('Update failed.', 'danger')

    return redirect(request.referrer or url_for('employer.index'))
