FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY app/requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY app/ .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 3000

# Start the Flask app
CMD ["python", "main.py"]