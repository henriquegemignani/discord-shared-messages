FROM python:3.9

RUN mkdir /app
COPY pyproject.toml /app
COPY poetry.lock /app
WORKDIR /app

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN python -m pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

COPY discord_shared_messages /app/discord_shared_messages

CMD sanic --host 0.0.0.0 discord_shared_messages.app
