FROM python:3.7-slim-buster

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY .env /app/.env
COPY templates/ /app/templates
COPY src /app/src

WORKDIR /app

ENTRYPOINT ["python"]
CMD ["-m", "src.traxiv", "--group", "test", "--start", "'2021-02-01'"]