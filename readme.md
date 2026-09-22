# Mwafrika Asilia — Backend

FastAPI backend for the Mwafrika Asilia platform.

## Stack
- FastAPI + SQLAlchemy 2.0 (async) + Alembic
- MySQL 8 (local → Aiven later)
- Redis (local → Upstash later)
- Python 3.12

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env with real values
uvicorn app.main:app --reload