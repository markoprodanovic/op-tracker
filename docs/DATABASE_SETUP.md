# Database Setup Guide - Phase 1

## Overview

This guide walks you through setting up the new database schema in Supabase for the web scraping feature.

## Prerequisites

- Access to your Supabase project dashboard
- SQL Editor access in Supabase

## Step-by-Step Setup

### 1. Access Supabase SQL Editor

1. Log into your Supabase dashboard
2. Navigate to your One Piece Tracker project
3. Click on "SQL Editor" in the left sidebar
4. Create a new query

### 2. Execute Schema Creation

1. Copy the contents of `database_schema.sql`
2. Paste into the SQL Editor
3. Click "Run" to execute the script
4. Verify the tables were created by checking the "Table Editor"

### 3. Execute Helper Functions

1. Create another new query in SQL Editor
2. Copy the contents of `database_functions.sql`
3. Paste and execute
4. Verify the function was created (check Functions section if available)

### 4. Verify Table Creation

After running the scripts, you should see:

**New Tables:**

- `arcs` - with sample arc data
- `scraped_episodes` - empty, ready for scraped data

**Existing Tables:** (unchanged)

- `episodes` - your current API data
- `watch_history` - your viewing history

### 5. Review Sample Arc Data

The script includes sample arc ranges. You may want to adjust these:

```sql
-- View current arcs
SELECT * FROM arcs ORDER BY start_episode;

-- Update arc ranges if needed (example)
UPDATE arcs
SET end_episode = 1100
WHERE name = 'Wano Country Saga';
```

### 6. Test the Setup

Run these queries to verify everything works:

```sql
-- Test arc assignment function
SELECT get_arc_for_episode(1);    -- Should return East Blue Saga ID
SELECT get_arc_for_episode(500);  -- Should return Summit War Saga ID
SELECT get_arc_for_episode(9999); -- Should return Unknown Arc ID

-- Test the view
SELECT * FROM episodes_with_arcs LIMIT 5; -- Should work even with no data
```

## Important Notes

### Arc Ranges

The sample data includes broad arc ranges. You can adjust these in Supabase:

- **East Blue**: Episodes 1-61
- **Arabasta**: Episodes 62-135
- **Sky Island**: Episodes 136-206
- etc.

### Unknown Arc Handling

- Episodes outside defined ranges automatically get "Unknown Arc"
- You can manually assign these later by updating arc ranges

### Performance

- Indexes are created for optimal query performance
- Triggers automatically update `updated_at` timestamps

## Next Steps

Once the database is set up:

1. Verify all tables exist and have proper structure
2. Test the arc assignment function with various episode numbers
3. Ready to proceed to Phase 2 (Web Scraping Infrastructure)

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure you have admin access to the Supabase project
2. **Function creation fails**: Some Supabase plans may restrict custom functions
3. **Constraint violations**: If you have existing data that conflicts

### Verification Queries

```sql
-- Check table structure
\d arcs
\d scraped_episodes

-- Count records
SELECT COUNT(*) FROM arcs;

-- Test foreign key relationship
SELECT a.name, COUNT(se.id) as episode_count
FROM arcs a
LEFT JOIN scraped_episodes se ON a.id = se.arc_id
GROUP BY a.id, a.name
ORDER BY a.start_episode;
```
