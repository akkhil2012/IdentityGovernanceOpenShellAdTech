FROM python:3.12.10-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY apps/api /app/apps/api
COPY scripts /app/scripts
ENV PYTHONPATH=/app/apps/api
CMD ["uvicorn", "governed_audience.main:app", "--host", "0.0.0.0", "--port", "8000"]
