FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY db/ db/

EXPOSE 8000

# Reviewer workbench API. The workflow's own long-running steps (extraction,
# coding) happen inside graph node execution triggered by this API, not as
# a separate process -- see src/workflow/graph.py.
CMD ["uvicorn", "src.review.api:app", "--host", "0.0.0.0", "--port", "8000"]
