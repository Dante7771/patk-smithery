FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY filter.py .
COPY server.py .

ENV PYTHONUNBUFFERED=1

# Railway sets PORT dynamically
EXPOSE 8000

CMD ["python", "server.py"]
