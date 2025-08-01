FROM python:3.10-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# This is just for the devcontainer. The render.yaml will override the command.
CMD ["sleep", "infinity"]