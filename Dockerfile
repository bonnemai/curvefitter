# syntax=docker/dockerfile:1
ARG TARGETPLATFORM=linux/arm64

FROM public.ecr.aws/lambda/python:3.11 AS tests

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /var/task

RUN yum install -y gcc gcc-c++ \
    && yum clean all \
    && rm -rf /var/cache/yum

RUN python -m pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY app ./app
COPY entrypoint.sh ./
COPY tests ./tests

RUN python -m pip install --no-cache-dir ".[dev]"
RUN coverage run -m pytest \
    && coverage xml

FROM public.ecr.aws/lambda/python:3.11

ARG BUILD_TIME
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUILD_TIME=${BUILD_TIME}

WORKDIR /var/task

RUN yum install -y gcc gcc-c++ \
    && yum clean all \
    && rm -rf /var/cache/yum

COPY pyproject.toml README.md ./
COPY app ./app
COPY entrypoint.sh ./

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN echo "${BUILD_TIME:-unknown}" > /var/task/.build_time

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["app.main.handler"]
