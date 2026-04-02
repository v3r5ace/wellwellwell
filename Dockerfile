FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY wellwellwell ./wellwellwell

RUN pip install --upgrade pip \
    && pip install .

VOLUME ["/data"]

EXPOSE 8000

CMD ["wellwellwell", "run"]
