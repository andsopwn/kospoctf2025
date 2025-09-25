FROM python:3.12-slim

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir pycryptodome ecdsa

EXPOSE 8888

CMD ["python", "app.py"]