# Pharma Choice

Python application for Pharma Choice.

## Project Structure

```text
pharma_choice/
├─ .gitignore
├─ README.md
├─ run_project.bat              # local run script with real credentials (ignored by git)
├─ run_project.example.bat      # safe template (committable)
├─ pharmachoice/
│  └─ app.py                    # application entry point
└─ venv/                        # local virtual environment (ignored by git)
```

## Prerequisites

- Python 3.10+ (recommended)
- Windows PowerShell / VS Code terminal

## Setup

```powershell
cd "file path"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If `requirements.txt` is not present, install dependencies manually.

## Configuration

The app reads these environment variables:

- `PHARMACHOICE_DB_USER`
- `PHARMACHOICE_DB_PASSWORD`
- `PHARMACHOICE_DB_HOST`
- `PHARMACHOICE_DB_PORT`
- `PHARMACHOICE_DB_NAME`

### Recommended

1. Copy `run_project.example.bat` to `run_project.bat`
2. Fill your local DB values in `run_project.bat`
3. Keep `run_project.bat` uncommitted

## How to Run

### Option 1: Run directly with Python

```powershell
cd "c:\Users\HP\Downloads\Internship\pharma_choice"
.\venv\Scripts\Activate.ps1
python pharmachoice\app.py
```

### Option 2: Run with batch script (local)

```powershell
.\run_project.bat
```

## Security

- `run_project.bat` must stay in `.gitignore`.
- Never commit real credentials or tokens.
- If credentials were exposed, rotate them immediately.
