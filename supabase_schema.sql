-- ============================================================
-- TSEPIP - Online Trainee Tracking System
-- Supabase Database Schema
-- Run this in your Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- PROFILES TABLE (extends Supabase auth.users)
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'trainee' CHECK (role IN ('admin', 'instructor', 'trainee', 'employer')),
    full_name TEXT NOT NULL,
    national_id TEXT,
    admission_number TEXT UNIQUE,
    email TEXT NOT NULL,
    phone TEXT,
    gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
    date_of_birth DATE,
    profile_photo_url TEXT,
    county_region TEXT,
    emergency_contact TEXT,
    emergency_phone TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DEPARTMENTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE,
    description TEXT,
    head_instructor_id UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COURSES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    code TEXT UNIQUE,
    department_id UUID REFERENCES departments(id),
    duration_months INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRAINEES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS trainees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    admission_number TEXT UNIQUE NOT NULL,
    course_id UUID REFERENCES courses(id),
    department_id UUID REFERENCES departments(id),
    intake_year INTEGER,
    graduation_year INTEGER,
    current_semester INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'graduated', 'suspended', 'deferred', 'withdrawn')),
    gpa DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ACADEMIC RECORDS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS academic_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    semester INTEGER NOT NULL,
    academic_year TEXT NOT NULL,
    unit_name TEXT NOT NULL,
    unit_code TEXT,
    grade TEXT,
    score DECIMAL(5,2),
    status TEXT DEFAULT 'enrolled' CHECK (status IN ('enrolled', 'completed', 'failed', 'deferred')),
    instructor_id UUID REFERENCES profiles(id),
    remarks TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ATTENDANCE TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late', 'excused')),
    session TEXT,
    instructor_id UUID REFERENCES profiles(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COMPETENCIES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS competencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    course_id UUID REFERENCES courses(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRAINEE COMPETENCIES (junction)
-- ============================================================
CREATE TABLE IF NOT EXISTS trainee_competencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    competency_id UUID REFERENCES competencies(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    verified_by UUID REFERENCES profiles(id),
    verified_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MEDIA UPLOADS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS media_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    uploader_id UUID REFERENCES profiles(id),
    title TEXT NOT NULL,
    description TEXT,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video', 'document')),
    file_url TEXT NOT NULL,
    thumbnail_url TEXT,
    file_size INTEGER,
    file_name TEXT,
    mime_type TEXT,
    skill_tags TEXT[],
    category TEXT,
    location_name TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    watermarked_url TEXT,
    approval_status TEXT DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_by UUID REFERENCES profiles(id),
    approved_at TIMESTAMPTZ,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INTERNSHIPS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS internships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    supervisor_name TEXT,
    supervisor_email TEXT,
    supervisor_phone TEXT,
    start_date DATE,
    end_date DATE,
    location_name TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'terminated')),
    description TEXT,
    skills_gained TEXT[],
    employer_rating INTEGER CHECK (employer_rating BETWEEN 1 AND 5),
    employer_comments TEXT,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CERTIFICATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS certifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuing_body TEXT,
    issue_date DATE,
    expiry_date DATE,
    certificate_url TEXT,
    verification_code TEXT UNIQUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- EMPLOYER VERIFICATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS employer_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    employer_name TEXT NOT NULL,
    employer_email TEXT NOT NULL,
    employer_company TEXT,
    verification_type TEXT CHECK (verification_type IN ('internship', 'employment', 'project', 'skill')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'verified', 'rejected', 'requires_rework')),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    media_url TEXT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- NOTIFICATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info' CHECK (type IN ('info', 'success', 'warning', 'error')),
    is_read BOOLEAN DEFAULT FALSE,
    link TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PORTFOLIO VIEWS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainee_id UUID REFERENCES trainees(id) ON DELETE CASCADE,
    viewer_ip TEXT,
    viewer_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_trainees_profile ON trainees(profile_id);
CREATE INDEX IF NOT EXISTS idx_trainees_course ON trainees(course_id);
CREATE INDEX IF NOT EXISTS idx_trainees_department ON trainees(department_id);
CREATE INDEX IF NOT EXISTS idx_media_trainee ON media_uploads(trainee_id);
CREATE INDEX IF NOT EXISTS idx_media_status ON media_uploads(approval_status);
CREATE INDEX IF NOT EXISTS idx_media_created ON media_uploads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_academic_trainee ON academic_records(trainee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_trainee ON attendance(trainee_id);
CREATE INDEX IF NOT EXISTS idx_internships_trainee ON internships(trainee_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE trainees ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE academic_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE internships ENABLE ROW LEVEL SECURITY;
ALTER TABLE certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE trainee_competencies ENABLE ROW LEVEL SECURITY;

-- Profiles: users can read all, update own
CREATE POLICY "Public profiles are viewable by everyone" ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Trainees: viewable by all authenticated
CREATE POLICY "Trainees viewable by authenticated" ON trainees FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Admins can manage trainees" ON trainees FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'instructor'))
);

-- Media: approved media viewable by all, own media by trainee
CREATE POLICY "Approved media viewable by all" ON media_uploads FOR SELECT USING (approval_status = 'approved' OR uploader_id = auth.uid());
CREATE POLICY "Trainees can upload media" ON media_uploads FOR INSERT WITH CHECK (uploader_id = auth.uid());
CREATE POLICY "Admins can manage media" ON media_uploads FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'instructor'))
);

-- Academic records: viewable by trainee and admins
CREATE POLICY "Trainees view own records" ON academic_records FOR SELECT USING (
    trainee_id IN (SELECT id FROM trainees WHERE profile_id = auth.uid())
    OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'instructor'))
);

-- Notifications: users see own
CREATE POLICY "Users see own notifications" ON notifications FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users update own notifications" ON notifications FOR UPDATE USING (user_id = auth.uid());

-- Departments & Courses: public read (reference data needed for registration)
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE competencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_views ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Departments are publicly readable" ON departments FOR SELECT USING (true);
CREATE POLICY "Courses are publicly readable" ON courses FOR SELECT USING (true);
CREATE POLICY "Competencies are publicly readable" ON competencies FOR SELECT USING (true);

-- ============================================================
-- SEED DATA - Departments
-- ============================================================
INSERT INTO departments (name, code, description) VALUES
    ('Electrical Engineering', 'EE', 'Electrical installation and maintenance'),
    ('Mechanical Engineering', 'ME', 'Mechanical systems and fabrication'),
    ('Information Technology', 'IT', 'Software development and networking'),
    ('Civil Engineering', 'CE', 'Construction and structural engineering'),
    ('Automotive Engineering', 'AE', 'Vehicle mechanics and diagnostics'),
    ('Welding & Fabrication', 'WF', 'Metal welding and fabrication'),
    ('Plumbing', 'PL', 'Plumbing and pipe fitting'),
    ('Carpentry', 'CA', 'Woodwork and furniture making')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED DATA - Courses
-- ============================================================
INSERT INTO courses (name, code, duration_months, description) VALUES
    ('Certificate in Electrical Installation', 'CEI', 24, 'Domestic and industrial electrical installation'),
    ('Diploma in Mechanical Engineering', 'DME', 36, 'Mechanical systems design and maintenance'),
    ('Certificate in ICT', 'CICT', 24, 'Information and communication technology'),
    ('Certificate in Civil Engineering', 'CCE', 24, 'Building and construction technology'),
    ('Certificate in Automotive Engineering', 'CAE', 24, 'Motor vehicle mechanics'),
    ('Certificate in Welding', 'CW', 18, 'Arc and MIG welding techniques'),
    ('Certificate in Plumbing', 'CP', 18, 'Plumbing and sanitation systems'),
    ('Certificate in Carpentry', 'CC', 18, 'Furniture making and joinery')
ON CONFLICT (code) DO NOTHING;
