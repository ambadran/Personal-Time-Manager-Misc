INSERT INTO timetable_runs (
    run_started_at,
    status,
    input_version_hash,
    solution_data
) VALUES (
    NOW(),
    'MANUAL',
    'manual_test_record_01',
    '{
      "name": "Test Event from SQL",
      "category": "Testing",
      "start_time": "2025-09-15T10:00:00",
      "end_time": "2025-09-15T11:00:00"
    }'::jsonb
) RETURNING id;


DELETE FROM timetable_runs WHERE id = 13;
