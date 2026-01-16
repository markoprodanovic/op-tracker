# One Piece Tracker - Web Scraping Implementation Plan

## Overview

This plan outlines the implementation of a web scraping feature to collect episode data from [animefillerlist.com](https://www.animefillerlist.com/shows/one-piece) while maintaining the existing API-based system.

## Current System Analysis

- **Existing Table**: `episodes` with columns: id, title, release_date, arc_title, saga_title, created_at, updated_at
- **Watch History Table**: `watch_history` with columns: id, episode_id, watched_date, created_at, updated_at
- **Current Flow**: API → Parse → Store in episodes table
- **Frontend Dependency**: Existing frontend relies on current episodes table
- **Future Migration**: `watch_history.episode_id` will eventually reference new scraped episodes table

## New System Goals

1. Keep existing API system running (deprecation later)
2. Add web scraping for more reliable/current data
3. Create new table structure for scraped data
4. Manual arc management via separate table (broad arcs only)
5. Prepare for eventual `watch_history` migration to new episode table

## Step-by-Step Implementation Plan

### Phase 1: Database Schema Design & Setup

#### Step 1.1: Design New Tables

Create schema for two new tables:

**`scraped_episodes` table:**

- `id` (INTEGER, PRIMARY KEY) - Episode number from website
- `title` (TEXT) - Episode title
- `airdate` (DATE) - Release date from website
- `arc_id` (INTEGER, FOREIGN KEY) - Reference to arcs table
- `created_at` (TIMESTAMP) - When record was created
- `updated_at` (TIMESTAMP) - When record was last updated

**`arcs` table:**

- `id` (INTEGER, PRIMARY KEY, AUTO INCREMENT)
- `name` (TEXT) - Broad arc name (e.g., "East Blue Saga", "Alabasta Saga", "Skypiea Saga")
- `start_episode` (INTEGER) - First episode of arc
- `end_episode` (INTEGER) - Last episode of arc
- `description` (TEXT, OPTIONAL) - Arc description
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

#### Step 1.2: Create Tables in Supabase

- Manually create tables using Supabase SQL editor
- Set up proper indexes and constraints
- Create initial arc data (you'll populate this manually)

### Phase 2: Web Scraping Infrastructure

#### Step 2.1: Add Dependencies

Update `requirements.txt` to include:

- `beautifulsoup4` - HTML parsing
- `httpx` - HTTP client (already available)
- `lxml` - Fast XML parser for BeautifulSoup

#### Step 2.2: Create Scraper Module

Create `src/scraper.py` with:

- `AnimeFillerListScraper` class
- Methods to:
  - Fetch the webpage
  - Parse the episode table
  - Extract episode data (id, title, airdate)
  - Handle pagination if needed
  - Error handling and retry logic

#### Step 2.3: Create New Data Models

Extend `src/models.py` with:

- `ScrapedEpisode` - Raw episode data from scraper
- `ScrapedEpisodeForDB` - Processed for database storage
- `Arc` - Arc information model
- Conversion methods between models

### Phase 3: Database Layer Enhancement

#### Step 3.1: Create Arc Database Manager

Create `src/arc_database.py` with:

- `ArcDatabase` class
- Methods to:
  - Get all arcs
  - Find arc by episode number
  - CRUD operations for arcs (if needed)

#### Step 3.2: Create Scraped Episodes Database Manager

Create `src/scraped_database.py` with:

- `ScrapedEpisodeDatabase` class
- Methods to:
  - Get existing episode IDs
  - Insert new episodes
  - Update existing episodes (minimal - titles assumed static)
  - Assign arc_id based on episode number (with "Unknown Arc" fallback)
  - Batch operations for efficiency

### Phase 4: Scraping Logic Implementation

#### Step 4.1: Create Scraping Service

Create `src/scraping_service.py` with:

- `EpisodeScrapingService` class
- Main orchestration logic:
  - Scrape episodes from website
  - Compare with existing database episodes
  - Assign arcs to new episodes
  - Insert only new/updated episodes
  - Logging and statistics

#### Step 4.2: Incremental Update Logic

Implement logic to:

- Fetch all episodes from website
- Get existing episode IDs from database
- Only process episodes not in database
- Assign "Unknown Arc" for episodes outside defined ranges
- Handle edge cases (missing data, network failures)

### Phase 5: Integration & Testing

#### Step 5.1: Create New Main Entry Point

Create `src/scraping_main.py` with:

- Main execution function
- Integration with existing config system
- Comprehensive logging
- Error handling

#### Step 5.2: Add Tests

Create test files in `local_tests/`:

- `test_scraper.py` - Test scraping functionality
- `test_scraped_database.py` - Test new database operations
- `test_scraping_service.py` - Test complete flow
- `test_arc_assignment.py` - Test arc assignment logic

#### Step 5.3: Add CLI Commands

Update main execution to support:

```bash
# Run original API sync (existing)
python -m src.main

# Run new web scraping sync
python -m src.scraping_main

# Run both (for transition period)
python -m src.main --include-scraping
```

### Phase 6: Documentation & Deployment

#### Step 6.1: Update Documentation

- Update README.md with new functionality
- Document new database schema
- Add setup instructions for arc data
- Document future `watch_history` migration plan
- Create troubleshooting guide

#### Step 6.2: Create Arc Setup Guide

Document how to:

- Manually create broad arc records in Supabase
- Find episode ranges for major story arcs
- Best practices for maintaining arc data
- Handle "Unknown Arc" episodes

## Technical Considerations

### Error Handling

- Network failures when scraping
- Website structure changes
- Missing or malformed data
- Database connection issues
- Episodes outside defined arc ranges (assign "Unknown Arc")

### Performance

- Rate limiting for web requests
- Batch database operations
- Efficient episode comparison
- Minimal re-processing of existing data

### Data Quality

- Validate scraped episode numbers
- Handle duplicate episodes
- Deal with missing airdates
- Validate arc assignments (with fallback to "Unknown Arc")
- Ensure episode IDs align with existing `watch_history` references

## Questions for Clarification

~~All questions have been answered and incorporated into the plan above.~~

### Answered:

1. **Arc Granularity**: ✅ Using broad arcs (East Blue Saga, Alabasta Saga, etc.)
2. **Episode Updates**: ✅ Ignore title changes - assume titles don't change
3. **Missing Arcs**: ✅ Use "Unknown Arc" for episodes outside defined ranges
4. **Data Migration**: ✅ No migration of existing `episodes` table data. Keep as fallback. Plan for future `watch_history` migration to new episode table.

## Next Steps

1. Review and approve this plan
2. Answer clarification questions
3. Create the database schema in Supabase
4. Start with Phase 2 (scraping infrastructure)
5. Implement incrementally, testing each phase

## Estimated Timeline

- Phase 1: 1-2 hours (database setup)
- Phase 2: 3-4 hours (scraping infrastructure)
- Phase 3: 2-3 hours (database layer)
- Phase 4: 4-5 hours (scraping logic)
- Phase 5: 3-4 hours (integration & testing)
- Phase 6: 1-2 hours (documentation)

**Total: 14-20 hours** (can be done over multiple sessions)
