# Use an official Python runtime as a parent image
FROM python:3.10
# (Not Slim - includes GCC/headers for native builds)

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nmap \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the full dependencies file
COPY requirements.txt .

# Install dependencies with increased timeout and separate heavy layers
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run the orchestrator
CMD ["python3", "-m", "src.orchestrator"]
