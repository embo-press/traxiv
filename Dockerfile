FROM python:3.7-slim-buster

RUN apt-get update

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

COPY .env /app/.env
COPY templates/ /app/templates
COPY src /app/src

WORKDIR /app

ENTRYPOINT ["python"]
CMD ["-m", "src.traxiv", "--group", "test", "--start", "'2021-02-01'"]