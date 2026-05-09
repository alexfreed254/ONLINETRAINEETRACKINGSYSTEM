from flask import render_template, session, redirect, url_for, flash, request
from app.portfolio import portfolio
from app.supabase_client import get_supabase_admin


@portfolio.route('/<trainee_id>')
def view(trainee_id):
    """Public portfolio view — uses admin client to bypass RLS."""
    sb = get_supabase_admin()
    user = session.get('user')

    trainee = None
    media = []
    competencies = []
    internships = []
    certifications = []
    verifications = []
    stats = {}

    try:
        result = sb.table('trainees').select(
            '*, profiles(*), courses(*), departments(*)'
        ).eq('id', trainee_id).execute()

        data = result.data or []
        trainee = data[0] if data else None

        if not trainee:
            flash('Portfolio not found.', 'danger')
            return redirect(url_for('trainees.index') if user else url_for('auth.login'))

        media = sb.table('media_uploads').select('*').eq(
            'trainee_id', trainee_id
        ).eq('approval_status', 'approved').order('created_at', desc=True).execute().data or []

        competencies = sb.table('trainee_competencies').select(
            '*, competencies(*)'
        ).eq('trainee_id', trainee_id).execute().data or []

        internships = sb.table('internships').select('*').eq(
            'trainee_id', trainee_id
        ).order('start_date', desc=True).execute().data or []

        certifications = sb.table('certifications').select('*').eq(
            'trainee_id', trainee_id
        ).execute().data or []

        verifications = sb.table('employer_verifications').select('*').eq(
            'trainee_id', trainee_id
        ).execute().data or []

        # Track portfolio view (best-effort)
        try:
            sb.table('portfolio_views').insert({
                'trainee_id': trainee_id,
                'viewer_ip': request.remote_addr,
                'viewer_agent': (request.user_agent.string[:200]
                                 if request.user_agent else None),
            }).execute()
        except Exception:
            pass

        stats = {
            'media_count': len(media),
            'competencies_verified': len([c for c in competencies
                                          if c.get('status') == 'verified']),
            'internships': len(internships),
            'certifications': len(certifications),
        }

    except Exception as e:
        flash(f'Error loading portfolio: {str(e)[:120]}', 'danger')
        return redirect(url_for('trainees.index') if user else url_for('auth.login'))

    return render_template('portfolio/view.html',
                           trainee=trainee,
                           media=media,
                           competencies=competencies,
                           internships=internships,
                           certifications=certifications,
                           verifications=verifications,
                           stats=stats,
                           user=user)
