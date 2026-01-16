-- Database Schema for One Piece Tracker Web Scraping Feature
-- Execute these SQL commands in Supabase SQL Editor

-- Create arcs table for managing story arcs
CREATE TABLE IF NOT EXISTS arcs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    start_episode INTEGER NOT NULL,
    end_episode INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create scraped_episodes table for episodes from web scraping
CREATE TABLE IF NOT EXISTS scraped_episodes (
    id INTEGER PRIMARY KEY,  -- Episode number from website
    title TEXT NOT NULL,
    airdate DATE,
    arc_id INTEGER REFERENCES arcs(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_arcs_episode_range ON arcs(start_episode, end_episode);
CREATE INDEX IF NOT EXISTS idx_scraped_episodes_arc_id ON scraped_episodes(arc_id);
CREATE INDEX IF NOT EXISTS idx_scraped_episodes_airdate ON scraped_episodes(airdate);

-- Create trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_arcs_updated_at 
    BEFORE UPDATE ON arcs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraped_episodes_updated_at 
    BEFORE UPDATE ON scraped_episodes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample arc data (you can modify these ranges based on actual One Piece arcs)
INSERT INTO arcs (name, start_episode, end_episode, description) VALUES
    ('East Blue Saga', 1, 61, 'The beginning of Luffy''s journey through the East Blue'),
    ('Arabasta Saga', 62, 135, 'The crew''s adventure in Arabasta kingdom'),
    ('Sky Island Saga', 136, 206, 'Journey to the sky island of Skypiea'),
    ('Water 7 Saga', 207, 325, 'Events in Water 7 and Enies Lobby'),
    ('Thriller Bark Saga', 326, 384, 'Adventure on the ghost ship Thriller Bark'),
    ('Summit War Saga', 385, 516, 'Marineford War and Ace''s rescue'),
    ('Fishman Island Saga', 517, 574, 'Journey to Fishman Island underwater'),
    ('Dressrosa Saga', 575, 746, 'Adventures in Dressrosa and Zou'),
    ('Whole Cake Island Saga', 747, 877, 'Infiltration of Big Mom''s territory'),
    ('Wano Country Saga', 878, 1085, 'The battle in Wano Country'),
    ('Final Saga', 1086, 9999, 'The final arc of One Piece')
ON CONFLICT (id) DO NOTHING;

-- Create a default "Unknown Arc" for episodes that don't match any range
INSERT INTO arcs (name, start_episode, end_episode, description) VALUES
    ('Unknown Arc', 0, 0, 'Episodes that don''t fall within defined arc ranges')
ON CONFLICT (id) DO NOTHING;

-- Add comments to tables
COMMENT ON TABLE arcs IS 'Story arcs with episode ranges for automatic assignment';
COMMENT ON TABLE scraped_episodes IS 'Episodes scraped from animefillerlist.com';
COMMENT ON COLUMN arcs.start_episode IS 'First episode number of the arc (inclusive)';
COMMENT ON COLUMN arcs.end_episode IS 'Last episode number of the arc (inclusive)';
COMMENT ON COLUMN scraped_episodes.id IS 'Episode number from the website (matches episode #)';
COMMENT ON COLUMN scraped_episodes.arc_id IS 'Foreign key reference to arcs table';