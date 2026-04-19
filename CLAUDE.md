# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

问题单管理系统 (Issue Tracking System) - A PySide6 desktop application for tracking issues with status transitions, module categorization, and rich text editing with image support.

## Commands

**Run the application:**
```bash
python main.py
```

**Background launch (Windows):**
```bash
启动.bat    # Console window visible
启动.vbs    # Hidden console window
```

## Architecture

Two-layer architecture: UI Layer and Data Layer.

```
src/
├── ui/               # UI Layer - PySide6 widgets and dialogs
│   ├── main_window.py        # Main window with page switching (list/detail/create)
│   ├── create_issue_panel.py # Create issue form
│   ├── issue_detail_panel.py # Issue detail view/edit by status
│   ├── module_manager_dialog.py
│   └── widgets/
│       └── rich_text_editor.py  # Rich text with image paste support
├── data/             # Data Layer - SQLite access
│   ├── database_manager.py  # Singleton SQLite connection, table init
│   ├── issue_dao.py         # Issue CRUD, status transitions
│   ├── module_dao.py        # Module CRUD
│   └── image_manager.py     # Local image storage in images/{issue_no}/
├── models/
│   ├── issue_model.py  # Issue dataclass + IssueStatus enum
│   └── module_model.py
```

## Key Patterns

**DatabaseManager** - Singleton pattern with auto-initialization. Call `DatabaseManager.get_instance()` to get connection.

**IssueStatus state machine:**
- SUBMIT_TEST (0) → DEVELOPING (1) → ARCHIVED (2) → CLOSED (3)
- Forward: submit action; Backward: rollback action
- Only SUBMIT_TEST status issues can be deleted
- DEVELOPING status requires: root_cause, solution, self_test, module_id filled before submit
- ARCHIVED status requires: archive_test filled before submit

**Issue number format:** `PRYYYYMMDDHHMMSS` (e.g., PR20260417223510)

**Image handling:**
- Images stored in `images/{issue_no}/` directory
- HTML content stores relative paths; RichTextEditor converts to absolute for display
- Supports: clipboard paste (including Snipaste), base64 extraction, file selection

**UI navigation:** QStackedWidget with three pages - list, detail, create. Signal/slot pattern for page transitions.

## Styling

Dark theme with colors: background `#1E1E2E`, secondary `#2E2E3E`, accent `#3498DB` (blue), `#27AE60` (green for secondary buttons).

## Database Tables

- `issue`: id, issue_no, title, description, module_id, status, root_cause, solution, self_test, archive_test, created_at, updated_at, status_changed_at
- `module`: id, name, created_at
- `image`: id, issue_id, field_name, file_path, created_at