-- Migration 027: Profiles table linking Supabase auth.users to Iris roles.
-- Supabase-specific: references auth.users which is managed by Supabase Auth.

CREATE TABLE IF NOT EXISTS profiles (
    id         UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username   TEXT        NOT NULL UNIQUE,
    role       TEXT        NOT NULL DEFAULT 'viewer' REFERENCES roles(id),
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create profile stub on new Supabase auth user
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO profiles (id, username, role)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'username', NEW.email), 'viewer')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
