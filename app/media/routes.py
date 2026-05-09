from flask import render_template, session, redirect, url_for, flash, request, jsonify, current_app
from app.media import media
from app.auth.routes import login_required
from app.supabase_client import get_supabase, get_supabase_admin
import base64
import os
import uuid
from datetime import datetime

SKILL_CATEGORIES = [
    'Electrical Installation', 'Mechanical Engineering', 'Welding & Fabrication',
    'Civil Construction', 'Automotive', 'ICT / Software', 'Plumbing',
    'Carpentry', 'Workshop Practice', 'Internship', 'Field Project',
    'Innovation', 'Assessment', 'Other'
]


def allowed_file(filename, file_type='image'):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if file_type == 'image':
        return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']
    elif file_type == 'video':
        return ext in current_app.config['ALLOWED_VIDEO_EXTENSIONS']
    elif file_type == 'document':
        return ext in current_app.config['ALLOWED_DOC_EXTENSIONS']
    return False


def detect_media_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return 'image'
    elif ext in current_app.config['ALLOWED_VIDEO_EXTENSIONS']:
        return 'video'
    elif ext in current_app.config['ALLOWED_DOC_EXTENSIONS']:
        return 'document'
    return None


@media.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    user = session.get('user')
    sb = get_supabase()
    sb_admin = get_supabase_admin()

    # Determine trainee_id
    trainee_id = request.args.get('trainee_id') or request.form.get('trainee_id')

    # If trainee, find own trainee record
    if user.get('role') == 'trainee' and not trainee_id:
        try:
            t = sb.table('trainees').select('id').eq('profile_id', user['id']).single().execute().data
            trainee_id = t['id'] if t else None
        except Exception:
            trainee_id = None

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '')
        location_name = request.form.get('location_name', '').strip()
        latitude = request.form.get('latitude', '')
        longitude = request.form.get('longitude', '')
        skill_tags_raw = request.form.get('skill_tags', '')
        skill_tags = [t.strip() for t in skill_tags_raw.split(',') if t.strip()]

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

        try:
            file_bytes = file.read()
            file_size = len(file_bytes)
            ext = file.filename.rsplit('.', 1)[-1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            storage_path = f"media/{trainee_id}/{unique_name}"

            # Upload to Supabase Storage
            sb_admin.storage.from_('trainee-media').upload(
                storage_path,
                file_bytes,
                {'content-type': file.content_type or 'application/octet-stream'}
            )

            # Get public URL
            file_url = sb_admin.storage.from_('trainee-media').get_public_url(storage_path)

            # Generate thumbnail for images
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
                    thumb_bytes = thumb_io.getvalue()
                    thumb_path = f"thumbnails/{trainee_id}/{unique_name}"
                    sb_admin.storage.from_('trainee-media').upload(
                        thumb_path,
                        thumb_bytes,
                        {'content-type': f'image/{img_format.lower()}'}
                    )
                    thumbnail_url = sb_admin.storage.from_('trainee-media').get_public_url(thumb_path)
                except Exception:
                    thumbnail_url = file_url

            # Determine approval status
            approval_status = 'approved' if user.get('role') in ('admin', 'instructor') else 'pending'

            record = {
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
            }

            sb_admin.table('media_uploads').insert(record).execute()
            flash('Media uploaded successfully!' + (' Pending approval.' if approval_status == 'pending' else ''), 'success')

            if trainee_id:
                return redirect(url_for('trainees.detail', trainee_id=trainee_id))
            return redirect(url_for('media.gallery'))

        except Exception as e:
            flash(f'Upload failed: {str(e)[:150]}', 'danger')

    # GET
    try:
        trainees_list = []
        if user.get('role') in ('admin', 'instructor'):
            trainees_list = sb.table('trainees').select(
                'id, admission_number, profiles(full_name)'
            ).eq('status', 'active').execute().data or []
    except Exception:
        trainees_list = []

    return render_template('media/upload.html',
                           user=user,
                           trainee_id=trainee_id,
                           trainees_list=trainees_list,
                           categories=SKILL_CATEGORIES)


@media.route('/gallery')
@login_required
def gallery():
    user = session.get('user')
    sb = get_supabase()

    category = request.args.get('category', '')
    media_type = request.args.get('type', '')
    page = int(request.args.get('page', 1))
    per_page = 18

    try:
        query = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name, profile_photo_url), departments(name))'
        )

        # Trainees only see approved + own
        if user.get('role') == 'trainee':
            trainee = sb.table('trainees').select('id').eq('profile_id', user['id']).single().execute().data
            if trainee:
                query = query.or_(f"approval_status.eq.approved,trainee_id.eq.{trainee['id']}")
        else:
            pass  # admins see all

        if category:
            query = query.eq('category', category)
        if media_type:
            query = query.eq('media_type', media_type)

        all_media = query.order('created_at', desc=True).execute().data or []
        total = len(all_media)
        start = (page - 1) * per_page
        paginated = all_media[start:start + per_page]

    except Exception as e:
        paginated = []
        total = 0

    total_pages = (total + per_page - 1) // per_page

    return render_template('media/gallery.html',
                           media=paginated,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           categories=SKILL_CATEGORIES,
                           current_category=category,
                           current_type=media_type,
                           user=user)


@media.route('/<media_id>')
@login_required
def view(media_id):
    user = session.get('user')
    sb = get_supabase()

    try:
        item = sb.table('media_uploads').select(
            '*, trainees(*, profiles(*), courses(name), departments(name))'
        ).eq('id', media_id).single().execute().data

        if not item:
            flash('Media not found.', 'danger')
            return redirect(url_for('media.gallery'))

        # Increment view count
        sb_admin = get_supabase_admin()
        sb_admin.table('media_uploads').update({'view_count': (item.get('view_count') or 0) + 1}).eq('id', media_id).execute()

        # Related media
        related = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name))'
        ).eq('trainee_id', item['trainee_id']).eq('approval_status', 'approved').neq('id', media_id).limit(6).execute().data or []

    except Exception as e:
        flash('Error loading media.', 'danger')
        return redirect(url_for('media.gallery'))

    return render_template('media/view.html', item=item, related=related, user=user)


@media.route('/approve/<media_id>', methods=['POST'])
@login_required
def approve(media_id):
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        return jsonify({'error': 'Permission denied'}), 403

    action = request.form.get('action', 'approved')
    sb_admin = get_supabase_admin()
    try:
        sb_admin.table('media_uploads').update({
            'approval_status': action,
            'approved_by': user['id'],
            'approved_at': datetime.now().isoformat(),
        }).eq('id', media_id).execute()
        flash(f'Media {action}.', 'success')
    except Exception:
        flash('Action failed.', 'danger')

    return redirect(request.referrer or url_for('media.gallery'))


@media.route('/pending')
@login_required
def pending():
    user = session.get('user')
    if user.get('role') not in ('admin', 'instructor'):
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard.index'))

    sb = get_supabase()
    try:
        items = sb.table('media_uploads').select(
            '*, trainees(profiles(full_name, admission_number), departments(name))'
        ).eq('approval_status', 'pending').order('created_at').execute().data or []
    except Exception:
        items = []

    return render_template('media/pending.html', items=items, user=user)


@media.route('/delete/<media_id>', methods=['POST'])
@login_required
def delete(media_id):
    user = session.get('user')
    sb = get_supabase()
    sb_admin = get_supabase_admin()

    try:
        item = sb.table('media_uploads').select('uploader_id, file_url').eq('id', media_id).single().execute().data
        if not item:
            flash('Not found.', 'danger')
            return redirect(url_for('media.gallery'))

        # Only uploader or admin can delete
        if item['uploader_id'] != user['id'] and user.get('role') not in ('admin',):
            flash('Permission denied.', 'danger')
            return redirect(url_for('media.gallery'))

        sb_admin.table('media_uploads').delete().eq('id', media_id).execute()
        flash('Media deleted.', 'success')
    except Exception:
        flash('Delete failed.', 'danger')

    return redirect(request.referrer or url_for('media.gallery'))
