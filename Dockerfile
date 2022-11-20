FROM python:3.11-slim-buster AS poetry
RUN pip install poetry
WORKDIR /
COPY pyproject.toml poetry.lock .
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
FROM python:3.11-slim
RUN apt-get update && apt-get install -y gcc curl git
WORKDIR /
COPY --from=poetry /requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH="./src:${PYTHONPATH}"
CMD ["python","src/main.py"]

#CMD ["python","-m","pytest","test/"]
