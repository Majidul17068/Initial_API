FROM python:3.12.6-slim

# Install necessary system packages, including audio dependencies
RUN apt-get update && \
    apt-get install -y libasound2 libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8502

# Install pipenv and system dependencies for any packages requiring compilation
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock into the container
COPY Pipfile Pipfile.lock ./

# Install dependencies using Pipenv
RUN pipenv install --deploy --ignore-pipfile

# Copy the rest of the application code into the container
COPY . .

# Set the entry point to run the Streamlit application
ENTRYPOINT ["pipenv", "run", "streamlit", "run", "authenticator.py"]

# Optionally, expose the default Streamlit port
EXPOSE 8502
