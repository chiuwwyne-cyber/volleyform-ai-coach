FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY angle ./angle
COPY action ./action
COPY backend ./backend
COPY frontend ./frontend
COPY pose ./pose

EXPOSE 8000
CMD ["python", "backend/server.py", "--host", "0.0.0.0"]
