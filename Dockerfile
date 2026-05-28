FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# Default config / state locations inside the container.
# Mount the host directories at these paths.
ENV XDG_CONFIG_HOME=/config \
    XDG_STATE_HOME=/state \
    HOME=/tmp \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "radio_notifier"]
CMD ["--help"]
