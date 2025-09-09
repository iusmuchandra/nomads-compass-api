# Start with a modern, efficient Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies first to leverage Docker's layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Copy the rest of the application source code into the container
COPY . .

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application using Uvicorn ASGI server
# The host 0.0.0.0 makes the container accessible from outside
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]