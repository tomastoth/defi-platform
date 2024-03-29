FROM python:3-slim as python
ENV PYTHONUNBUFFERED=true
WORKDIR /app

FROM python as poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN python -c 'from urllib.request import urlopen; print(urlopen("https://install.python-poetry.org").read().decode())' | python -
COPY ./pyproject.toml .
RUN poetry install --no-interaction --no-ansi -vvv
COPY . .


FROM python as runtime
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH "${PYTHONPATH}:/app/src"
COPY --from=poetry /app /app
CMD ["python","src/main.py"]