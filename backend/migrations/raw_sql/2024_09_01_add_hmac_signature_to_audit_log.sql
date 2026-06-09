-- Add HMAC columns to audit_log for integrity verification
ALTER TABLE audit_log ADD COLUMN hmac_signature TEXT;
ALTER TABLE audit_log ADD COLUMN key_id TEXT;
