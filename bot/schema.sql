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
