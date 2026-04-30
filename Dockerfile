# Use the pre-built Python GDAL image
FROM public.ecr.aws/docker/library/python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    libexpat1 \
    libsqlite3-0 \
    libproj25 \
    libgeos-c1v5 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# # Copy project files
# COPY input/ input/

# COPY main.py . 
COPY scripts/ ./scripts/

# Install dependencies directly (no virtualenv needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/AeroVision-code/ScoutMasterAPI-builder.git@main

# Run cron in the foreground
CMD ["python", "main.py"]


