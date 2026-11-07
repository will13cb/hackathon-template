# One image, two clouds:
#  - Cloud Run sets $PORT and sends HTTP straight to uvicorn.
#  - Lambda runs the Lambda Web Adapter extension, which turns invokes into HTTP on :8080.
FROM python:3.12-slim

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/health

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api ./api
COPY web ./web

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
