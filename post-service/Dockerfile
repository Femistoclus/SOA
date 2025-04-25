FROM python:3.9-slim

WORKDIR /app

COPY post-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ /app/proto/
RUN python -m grpc_tools.protoc \
    --proto_path=/app/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/proto/post_service.proto

COPY post-service/ .

CMD ["python", "server.py"]
