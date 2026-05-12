-- ============================================================
-- Job Postings Table — Run in Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS job_postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employer_id UUID REFERENCES employers(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('job', 'internship', 'attachment', 'apprenticeship')),
    description TEXT NOT NULL,
    requirements TEXT,
    skills_required TEXT[],
    department_preference TEXT,
    location TEXT,
    salary_range TEXT,
    deadline DATE,
    slots INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE job_postings ENABLE ROW LEVEL SECURITY;

-- Anyone can read active postings
CREATE POLICY "Active job postings are public"
ON job_postings FOR SELECT USING (is_active = true);

-- Employers manage their own postings
CREATE POLICY "Employers manage own postings"
ON job_postings FOR ALL
USING (true) WITH CHECK (true);

-- Index
CREATE INDEX IF NOT EXISTS idx_jobs_employer ON job_postings(employer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON job_postings(is_active, created_at DESC);
