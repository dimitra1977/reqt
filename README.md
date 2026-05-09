# Requirements GUI Tool

A small Python GUI application to browse, read, and write hierarchical requirements data.

## Features

- 5 requirement levels:
  - Level 0: Features
  - Level 1: User Stories
  - Level 2: System Requirements
  - Level 3: Sub-System & Interface Requirements
  - Level 4: Software and Hardware Requirements
- Requirement fields: `summary`, `description`, `level`, `parent`, `child` links, and 4 custom fields.
- Tree browser with search and editing support.

## Files

- `requirements_db.py` — SQLite database layer and schema.
- `requirements_app.py` — Tkinter GUI application.
- `requirements_schema.sql` — existing database schema reference.

## Run

```bash
python3 requirements_app.py
```

The app creates `requirements.db` in the same folder if it does not exist.

## Notes

- The GUI uses SQLite for local storage.
- `requirements_schema.sql` is the reference schema for hierarchical requirements storage.
