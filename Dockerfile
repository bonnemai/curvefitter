# syntax=docker/dockerfile:1
FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.11 AS tests

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /var/task

RUN python -m pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY app ./app
COPY tests ./tests

RUN python -m pip install --no-cache-dir ".[dev]"
RUN coverage run -m pytest \
    && coverage xml

FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /var/task

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

CMD ["app.main.handler"]
