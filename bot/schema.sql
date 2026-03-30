-- House Hunt Bot — Supabase Schema
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)

CREATE TABLE IF NOT EXISTS societies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    location TEXT,
    general_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    society_id UUID NOT NULL REFERENCES societies(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    area_sqft INTEGER,
    floor_range TEXT,
    general_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS broker_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
    broker_name TEXT,
    broker_phone TEXT,
    price_lakh NUMERIC,
    floor TEXT,
    facing TEXT,
    availability TEXT,
    notes TEXT,
    added_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS society_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    society_id UUID NOT NULL REFERENCES societies(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'New',
    personal_notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(society_id)
);

-- Index for fast society name lookups
CREATE INDEX IF NOT EXISTS idx_societies_name_lower ON societies (LOWER(name));

-- Index for config lookups by society
CREATE INDEX IF NOT EXISTS idx_configurations_society ON configurations (society_id);

-- Index for quote lookups by config
CREATE INDEX IF NOT EXISTS idx_broker_quotes_config ON broker_quotes (config_id);

-- ── Property Media (photos/videos linked to a broker quote) ──

CREATE TABLE IF NOT EXISTS property_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES broker_quotes(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
    public_url TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    telegram_file_id TEXT,
    telegram_file_unique_id TEXT,
    caption TEXT,
    uploaded_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Fast lookup: all media for a quote, newest last
CREATE INDEX IF NOT EXISTS idx_property_media_quote_created
ON property_media (quote_id, created_at DESC);

-- Prevent duplicate uploads (same Telegram file forwarded twice)
CREATE UNIQUE INDEX IF NOT EXISTS uq_property_media_quote_unique_file
ON property_media (quote_id, telegram_file_unique_id)
WHERE telegram_file_unique_id IS NOT NULL;
