/* VERY IMP:
 * This is the sql code to trigger a manual run of this module
 */
NOTIFY "manual-ptm-misc-trigger", 'LATEST';


-- Create a function that will be triggered on new row insertion
/* This is not a permenant process, it's a functionality assigned not to anytime I push a new record to the timetable_runstable, this function will run*/
CREATE OR REPLACE FUNCTION notify_new_timetable_run()
RETURNS TRIGGER AS $$
BEGIN
  /* NEW.id is the 'id' of the row being inserted
  -- 'new_timetable_run' is the channel name
  -- The second argument is the payload, which is the new run's ID */
  PERFORM pg_notify('new_timetable_run', NEW.id::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the trigger if it already exists to ensure a clean setup
DROP TRIGGER IF EXISTS on_new_timetable_run_insert ON timetable_runs;

-- Create a trigger that executes the function after each row insertion
CREATE TRIGGER on_new_timetable_run_insert
AFTER INSERT ON timetable_runs
FOR EACH ROW
EXECUTE FUNCTION notify_new_timetable_run();

CREATE TABLE calendar_events (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    timetable_run_id BIGINT NOT NULL REFERENCES timetable_runs(id),
    event_key TEXT NOT NULL, -- A unique key we generate from the event data
    google_event_id TEXT NOT NULL, -- The ID returned by the Google Calendar API
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (timetable_run_id, event_key)
);
