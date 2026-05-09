-- ============================================================
-- EMPLOYERS TABLE — Run in Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS employers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    official_email TEXT NOT NULL UNIQUE,
    phone TEXT,
    location TEXT,
    website TEXT,
    industry TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add employer_id to employer_verifications so we can link to employer accounts
ALTER TABLE employer_verifications
    ADD COLUMN IF NOT EXISTS employer_id UUID REFERENCES employers(id);

-- RLS
ALTER TABLE employers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Employers viewable by authenticated" ON employers;
DROP POLICY IF EXISTS "Employers can view own record" ON employers;

CREATE POLICY "Employers viewable by authenticated" ON employers
    FOR SELECT USING (auth.role() = 'authenticated' OR true);

CREATE POLICY "Employers can update own record" ON employers
    FOR UPDATE USING (profile_id = auth.uid());

-- Allow employer_verifications to be read by the trainee they belong to
DROP POLICY IF EXISTS "Trainees view own verifications" ON employer_verifications;
CREATE POLICY "Trainees view own verifications" ON employer_verifications
    FOR SELECT USING (
        trainee_id IN (SELECT id FROM trainees WHERE profile_id = auth.uid())
        OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin','instructor'))
        OR EXISTS (SELECT 1 FROM employers WHERE profile_id = auth.uid() AND id = employer_verifications.employer_id)
    );

-- Employers can insert verifications
DROP POLICY IF EXISTS "Employers can submit verifications" ON employer_verifications;
CREATE POLICY "Employers can submit verifications" ON employer_verifications
    FOR INSERT WITH CHECK (true);
