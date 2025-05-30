FROM python:3.13-alpine

ENV CI=true

WORKDIR /fastapi-app

COPY requirements.txt .

COPY app/ ./app/

RUN pip install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
