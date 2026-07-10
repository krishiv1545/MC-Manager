FROM python:3.13-slim

# Don't generate .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Show Python output immediately in logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Executable permissions
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]