FROM python:3.13-slim

# Don't generate .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Show Python output immediately in logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]