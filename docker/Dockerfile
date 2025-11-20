# syntax=docker/dockerfile:1
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies
RUN python -m pip install --upgrade pip \
    && python -m pip install \
        "fastapi[standard]==0.120.1" \
        "pydantic-settings==2.12.0"

# Copy application code
COPY app ./app
COPY pyproject.toml ./

EXPOSE 8888

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]
