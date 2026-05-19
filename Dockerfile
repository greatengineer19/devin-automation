FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY automate.py .
COPY sessions_log.json* ./

CMD ["python", "automate.py"]