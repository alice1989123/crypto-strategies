FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app as a Python package
COPY app/ ./app/
COPY runner.sh .

# Set the Python path to find `app` as a module
ENV PYTHONPATH=/app

RUN chmod +x /app/runner.sh
ENTRYPOINT ["./runner.sh"]
