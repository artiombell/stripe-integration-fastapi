FROM python:3.9

RUN pip install fastapi uvicorn

# Install Environment Dependencies (Image Base)
RUN pip install fastapi uvicorn poetry wheel virtualenv

EXPOSE 8080
EXPOSE 8081

# set working directory
WORKDIR /usr/src/app

ARG db_url="mongodb://db:27017"
ARG db_name="stripe-demo"

# set environment variables
ENV PORT 8000
ENV HOST "0.0.0.0"
ENV WEBHOOKS_PORT 8001
ENV DB_URL=$db_url
ENV DB_NAME=$db_name
ENV PYTHONUNBUFFERED=1

# Copy Required Project Assets
# COPY ./app/ /app/app
COPY ./static/ /app/static

COPY ./main.py /app

COPY ./poetry.lock /app
COPY ./pyproject.toml /app

# Change directories
WORKDIR /app

# Install Project Dependencies
RUN poetry config virtualenvs.create false \
  && poetry install

# Entry Point
CMD ["python3", "main.py"]