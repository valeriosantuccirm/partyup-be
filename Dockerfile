# Use the official Python image as base
FROM python:3.13.1-slim

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

# Set the working directory in the container
WORKDIR /app

# both files are explicitly required!
COPY Pipfile Pipfile.lock ./

# Install pipenv and compilation dependencies lightly
RUN \
  apt-get update && \
  apt-get install -y --no-install-recommends gcc python3-dev libssl-dev libpq-dev musl-dev && \
  pip install pipenv && \
  pipenv install --deploy --system && \
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get autoremove -y && \
  pip uninstall pipenv -y

# Copy the FastAPI app code to the working directory
COPY . .

# Expose the port the application runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
