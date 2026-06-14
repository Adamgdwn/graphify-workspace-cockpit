FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY workspace/demo/ ./workspace/demo/

ENV GRAPH_PATH=workspace/demo/graph.json
ENV STATE_DIR=workspace/state

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
