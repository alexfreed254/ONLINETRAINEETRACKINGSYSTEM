from flask import render_template, session, redirect, url_for, flash, request, jsonify, current_app
from app.media import media
from app.auth.routes import login_required
from app.supabase_client import get_supabase_admin
import uuid
from datetime import datetime

SKILL_CATEGORIES = [
    'Electrical Installation', 'Mechanical Engineering', 'Welding & Fabrication',
    'Civil Construction', 'Automotive', 'ICT / Software', 'Plumbing',
    'Carpentry', 'Workshop Practice', 'Internship', 'Field Project',
    'Innovation', 'Assessment', 'Other'
]


def detect_media_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return 'image'
    elif ext in current_app.config['ALLOWED_VIDEO_EXTENSIONS']:
        return 'video'
    elif ext in current_app.config['ALLOWED_DOC_EXTENSIONS']:
        return 'document'
    return None


# ─────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────

@media.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    user = session.get('user')
    sb = get_supabase_admin()

    trainee_id = request.args.get('trainee_id') or request.form.get('trainee_id')

    # Trainee: auto-find their own record
    if user.get('role') == 'trainee' and not trainee_id:
        try:
            result = sb.table('trainees').select('id').eq('profile_id', user['id']).execute()
            rows = result.data or []
            trainee_id = rows[0]['id'] if rows else None
        except Exception:
            trainee_id = None

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '')
        location_name = request.form.get('location_name', '').strip()
        latitude = request.form.get('latitude', '')
        longitude = request.form.get('longitude', '')
        skill_tags = [t.strip() for t in request.form.get('skill_tags', '').split(',') if t.strip()]

        if not title:
            flash('Title is required.', 'danger')
            return redirect(request.url)

        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return redirect(request.url)

        media_type = detect_media_type(file.filename)
        if not media_type:
            flash('Unsupported file type. Use JPG, PNG, MP4, MOV, or PDF.', 'danger')
            return redirect(request.url)

        if not trainee_id:
            flash('Could not identify your trainee record. Contact the institute.', 'danger')
            return redirect(request.url)

        try:
            file_bytes = file.read()
            file_size = len(file_bytes)
            ext = file.filename.rsplit('.', 1)[-1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            storage_path = f"media/{trainee_id}/{unique_name}"

            sb.storage.from_('trainee-media').upload(
                storage_path,
                file_bytes,
                {'content-type': file.content_type or 'application/octet-stream'}
            )
            file_url = sb.storage.from_('trainee-media').get_public_url(storage_path)

            # Thumbnail for images
            thumbnail_url = file_url
            if media_type == 'image':
                try:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(file_bytes))
                    img.thumbnail((400, 400))
                    thumb_io = io.BytesIO()
                    img_format = 'JPEG' if ext in ('jpg', 'jpeg') else 'PNG'
                    img.save(thumb_io, format=img_format, quality=75)
                    thumb_path = f"thumbnails/{trainee_id}/{unique_name}"
                    sb.storage.from_('trainee-media').upload(
                        thumb_path, thumb_io.getvalue(),
                        {'content-type': f'image/{img_format.lower()}'}
                    )
                    thumbnail_url = sb.storage.from_('trainee-media').get_public_url(thumb_path)
                except Exception:
                    thumbnail_url = file_url

            approval_status = 'approved' if user.get('role') in ('admin', 'instructor') else 'pending'

            sb.table('media_uploads').insert({
                'trainee_id': trainee_id,
                'uploader_id': user['id'],
                'title': title,
                'description': description,
                'media_type': media_type,
                'file_url': file_url,
                'thumbnail_url': thumbnail_url,
                'file_size': file_size,
                'file_name': file.filename,
                'mime_type': file.content_type,
                'skill_tags': skill_tags,
                'category': category,
                'location_name': location_name,
                'latitude': float(latitude) if latitude else None,
                'longitude': float(longitude) if longitude else None,
                'approval_status': approval_status,
            }).execute()

            msg = 'Evidence uploaded successfully!'
            if approval_status == 'pending':
                msg += ' It will appear after institute approval.'
            flash(msg, 'success')

            if user.get('role') == 'trainee':
                return redirect(url_for('trainee_dash.evidence'))
            if trainee_id:
                return redirect(url_for('trainees.detail', trainee_id=trainee_id))
            return redirect(url_for('media.gallery'))

        except Exception as e:
            err = str(e)
            if 'Bucket not found' in err:
                flash('Storage not configured yet. Ask the institute admin to create '
                      'the "trainee-media" bucket in Supabase Storage.', 'danger')
            else:
                flash(f'Upload failed: {err[:150]}', 'danger')

    # GET — load trainee list for admins
    trainees_list = []
    if user.get('role') in ('admin', 'instructor'):
        try:
            trainees_list = sb.table('trainees').select(
                'id, admission_number, profiles(full_name)'
            ).eq('status', 'active').execute().data or []
        except Exception:
            pass

    return render_template('media/upload.html',
                           user=user,
                           trainee_id=trainee_id,
                           trainees_list=trainees_list,
                           categories=SKILL_CATEGORIES)


# ─────────────────────────────────────────────
# Gallery
# ─────────────────────────────────────────────

@media.route('/gallery')
@login_required
def gallery():
    user = session.get('user')
    sb = get_supabase_admin()

    category = request.args.get('category', '')
    media_type_filter = request.args.get('type', '')
    page = int(request.args.get('page', 1))
    per_page = 18

    try:
        query = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name, profile_photo_url), departments(name))'
        )

        # Trainees only see their own uploads (all statuses) + approved from others
        if user.get('role') == 'trainee':
            rows = sb.table('trainees').select('id').eq('profile_id', user['id']).execute().data or []
            if rows:
                tid = rows[0]['id']
                query = query.or_(f"trainee_id.eq.{tid},approval_status.eq.approved")
            else:
                query = query.eq('approval_status', 'approved')
        # Admins/instructors see everything — no filter needed

        if category:
            query = query.eq('category', category)
        if media_type_filter:
            query = query.eq('media_type', media_type_filter)

        all_media = query.order('created_at', desc=True).execute().data or []
        total = len(all_media)
        start = (page - 1) * per_page
        paginated = all_media[start:start + per_page]

    except Exception:
        paginated = []
        total = 0

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template('media/gallery.html',
                           media=paginated,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           categories=SKILL_CATEGORIES,
                           current_category=category,
                           current_type=media_type_filter,
                           user=user)


# ─────────────────────────────────────────────
# View single media item
# ─────────────────────────────────────────────

@media.route('/<media_id>')
@login_required
def view(media_id):
    user = session.get('user')
    sb = get_supabase_admin()

    try:
        result = sb.table('media_uploads').select(
            '*, trainees(*, profiles(*), courses(name), departments(name))'
        ).eq('id', media_id).execute()

        rows = result.data or []
        item = rows[0] if rows else None

        if not item:
            flash('Media not found.', 'danger')
            return redirect(url_for('media.gallery'))

        # Increment view count
        sb.table('media_uploads').update(
            {'view_count': (item.get('view_count') or 0) + 1}
        ).eq('id', media_id).execute()

        related = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name))'
        ).eq('trainee_id', item['trainee_id']).eq(
            'approval_status', 'approved'
        ).neq('id', media_id).limit(6).execute().data or []

    except Exception:
        flash('Error loading media.', 'danger')
        return redirect(url_for('media.gallery'))

    return render_template('media/view.html', item=item, related=related, user=user)


# ─────────────────────────────────────────────
# Approve / Reject
# ─────────────────────────────────────────────

@media.route('/approve/<media_id>', methods=['POST'])
@login_required
def approve(media_id):
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        return jsonify({'error': 'Permission denied'}), 403

    action = request.form.get('action', 'approved')
    sb = get_supabase_admin()
    try:
        sb.table('media_uploads').update({
            'approval_status': action,
            'approved_by': user['id'],
            'approved_at': datetime.now().isoformat(),
        }).eq('id', media_id).execute()
        flash(f'Media {action}.', 'success')
    except Exception:
        flash('Action failed.', 'danger')

    return redirect(request.referrer or url_for('media.gallery'))


# ─────────────────────────────────────────────
# Pending review queue
# ─────────────────────────────────────────────

@media.route('/pending')
@login_required
def pending():
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard.index'))

    sb = get_supabase_admin()
    try:
        items = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name, admission_number), departments(name))'
        ).eq('approval_status', 'pending').order('created_at').execute().data or []
    except Exception:
        items = []

    return render_template('media/pending.html', items=items, user=user)


# ─────────────────────────────────────────────
# Delete
# ─────────────────────────────────────────────

@media.route('/delete/<media_id>', methods=['POST'])
@login_required
def delete(media_id):
    user = session.get('user')
    sb = get_supabase_admin()

    try:
        rows = sb.table('media_uploads').select('uploader_id').eq('id', media_id).execute().data or []
        if not rows:
            flash('Not found.', 'danger')
            return redirect(url_for('media.gallery'))

        item = rows[0]
        if item['uploader_id'] != user['id'] and user.get('role') != 'admin':
            flash('Permission denied.', 'danger')
            return redirect(url_for('media.gallery'))

        sb.table('media_uploads').delete().eq('id', media_id).execute()
        flash('Media deleted.', 'success')
    except Exception:
        flash('Delete failed.', 'danger')

    # Redirect trainee back to their evidence page
    if user.get('role') == 'trainee':
        return redirect(url_for('trainee_dash.evidence'))
    return redirect(request.referrer or url_for('media.gallery'))
