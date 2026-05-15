-- ============================================================
-- JOB APPLICATIONS TABLE
-- Run in Supabase SQL Editor after supabase_jobs.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS job_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    trainee_id UUID NOT NULL REFERENCES trainees(id) ON DELETE CASCADE,
    cover_note TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'reviewed', 'shortlisted', 'rejected', 'accepted')),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (job_id, trainee_id)   -- one application per trainee per job
);

ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;

-- Trainees can see their own applications; employers can see applications for their jobs
DROP POLICY IF EXISTS "Trainees see own applications"   ON job_applications;
DROP POLICY IF EXISTS "Employers see their job apps"    ON job_applications;
DROP POLICY IF EXISTS "Trainees can apply"              ON job_applications;
DROP POLICY IF EXISTS "Admins manage all applications"  ON job_applications;

CREATE POLICY "Trainees see own applications"
    ON job_applications FOR SELECT
    USING (
        trainee_id IN (SELECT id FROM trainees WHERE profile_id = auth.uid())
    );

CREATE POLICY "Employers see their job apps"
    ON job_applications FOR SELECT
    USING (
        job_id IN (
            SELECT id FROM job_postings
            WHERE employer_id IN (SELECT id FROM employers WHERE profile_id = auth.uid())
        )
    );

CREATE POLICY "Trainees can apply"
    ON job_applications FOR INSERT
    WITH CHECK (
        trainee_id IN (SELECT id FROM trainees WHERE profile_id = auth.uid())
    );

CREATE POLICY "Admins manage all applications"
    ON job_applications FOR ALL
    USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_applications_job     ON job_applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_trainee ON job_applications(trainee_id);
CREATE INDEX IF NOT EXISTS idx_applications_status  ON job_applications(status);
