from flask import render_template, session, redirect, url_for, flash
from app.portfolio import portfolio
from app.supabase_client import get_supabase


@portfolio.route('/<trainee_id>')
def view(trainee_id):
    """Public portfolio view — no login required."""
    sb = get_supabase()
    user = session.get('user')

    try:
        trainee = sb.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).single().execute().data

        if not trainee:
            flash('Portfolio not found.', 'danger')
            return redirect(url_for('trainees.index') if user else '/')

        # Approved media only
        media = sb.table('media_uploads').select('*').eq(
            'trainee_id', trainee_id
        ).eq('approval_status', 'approved').order('created_at', desc=True).execute().data or []

        # Verified competencies
        competencies = sb.table('trainee_competencies').select(
            '*, competencies(*)'
        ).eq('trainee_id', trainee_id).execute().data or []

        # Completed internships
        internships = sb.table('internships').select('*').eq(
            'trainee_id', trainee_id
        ).order('start_date', desc=True).execute().data or []

        # Certifications
        certifications = sb.table('certifications').select('*').eq(
            'trainee_id', trainee_id
        ).execute().data or []

        # Employer verifications
        verifications = sb.table('employer_verifications').select('*').eq(
            'trainee_id', trainee_id
        ).execute().data or []

        # Track portfolio view
        try:
            from flask import request
            sb.table('portfolio_views').insert({
                'trainee_id': trainee_id,
                'viewer_ip': request.remote_addr,
                'viewer_agent': request.user_agent.string[:200] if request.user_agent else None,
            }).execute()
        except Exception:
            pass

        stats = {
            'media_count': len(media),
            'competencies_verified': len([c for c in competencies if c.get('status') == 'verified']),
            'internships': len(internships),
            'certifications': len(certifications),
        }

    except Exception as e:
        flash(f'Error loading portfolio: {str(e)[:100]}', 'danger')
        return redirect(url_for('trainees.index') if user else '/')

    return render_template('portfolio/view.html',
                           trainee=trainee,
                           media=media,
                           competencies=competencies,
                           internships=internships,
                           certifications=certifications,
                           verifications=verifications,
                           stats=stats,
                           user=user)
