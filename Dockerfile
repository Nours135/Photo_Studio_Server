FROM python:3.11-slim

WORKDIR /

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 


# Install CA certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# copy project files
COPY app/ .

RUN pip install -r app/requirements.txt

EXPOSE 18001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18001"]
