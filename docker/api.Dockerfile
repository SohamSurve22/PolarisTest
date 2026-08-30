FROM python:3.12-slim

WORKDIR /app

COPY document_pipeline /app/document_pipeline
COPY vectorization /app/vectorization
COPY graph_builder /app/graph_builder
COPY policy_compare /app/policy_compare
COPY compliance /app/compliance
COPY rag /app/rag
COPY dataset/ /app/laws/

RUN pip install --no-cache-dir \
  -e /app/document_pipeline \
  -e /app/vectorization \
  -e /app/graph_builder \
  -e /app/policy_compare[api] \
  -e /app/compliance \
  -e /app/rag

ENV POLARIS_LAW_DIR=/app/laws
EXPOSE 8000

CMD ["uvicorn", "policy_compare.api:app", "--host", "0.0.0.0", "--port", "8000"]
