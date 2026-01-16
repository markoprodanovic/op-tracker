-- Helper function to get arc ID for a given episode number
-- This function will be used by the application to assign arcs to episodes

CREATE OR REPLACE FUNCTION get_arc_for_episode(episode_number INTEGER)
RETURNS INTEGER AS $$
DECLARE
    arc_id_result INTEGER;
    unknown_arc_id INTEGER;
BEGIN
    -- Try to find an arc that contains this episode number
    SELECT id INTO arc_id_result
    FROM arcs 
    WHERE episode_number >= start_episode 
    AND episode_number <= end_episode
    AND name != 'Unknown Arc'
    ORDER BY start_episode
    LIMIT 1;
    
    -- If found, return the arc ID
    IF arc_id_result IS NOT NULL THEN
        RETURN arc_id_result;
    END IF;
    
    -- If no arc found, return the "Unknown Arc" ID
    SELECT id INTO unknown_arc_id 
    FROM arcs 
    WHERE name = 'Unknown Arc' 
    LIMIT 1;
    
    RETURN COALESCE(unknown_arc_id, 1); -- Fallback to ID 1 if Unknown Arc doesn't exist
END;
$$ LANGUAGE plpgsql;

-- Create a view for easy episode browsing with arc names
CREATE OR REPLACE VIEW episodes_with_arcs AS
SELECT 
    se.id,
    se.title,
    se.airdate,
    se.arc_id,
    a.name as arc_name,
    se.created_at,
    se.updated_at
FROM scraped_episodes se
LEFT JOIN arcs a ON se.arc_id = a.id
ORDER BY se.id;

-- Grant permissions (adjust as needed for your Supabase setup)
-- These are typically handled automatically in Supabase, but included for completeness
COMMENT ON FUNCTION get_arc_for_episode IS 'Returns the appropriate arc ID for a given episode number';
COMMENT ON VIEW episodes_with_arcs IS 'Episodes joined with their arc information for easy querying';