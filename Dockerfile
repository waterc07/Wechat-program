FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=80

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY README.md ./README.md

EXPOSE 80

CMD ["sh", "-c", "gunicorn --chdir backend --bind 0.0.0.0:${PORT:-80} --workers 2 --threads 4 --timeout 180 wsgi:app"]
