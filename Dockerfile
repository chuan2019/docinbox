# The same FastAPI app `make run` starts with uvicorn, packaged so it can run
# in a container instead. Both options are supported - see the README.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer stays cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the source, which changes on every commit.
COPY app/ app/
COPY bootstrap/ bootstrap/

# Don't run as root. UID 1000 matches the usual host user, so the bind
# mounts compose adds for live reload stay readable.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# No --reload here: the image is the deployable shape. docker-compose.yml
# overrides this command with --reload for local development.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
