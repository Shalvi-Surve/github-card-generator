# Use a slim Python image
FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN uv pip install --no-cache -r requirements.txt --system

# Copy the rest of the application
COPY . .

# Ensure the static directory exists
RUN mkdir -p static/cards

# Expose the port FastAPI will run on
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
