FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

ENV MODULE_NAME=main
ENV VARIABLE_NAME=app
ENV PORT=8080

CMD ["sh", "-c", "uvicorn $MODULE_NAME:$VARIABLE_NAME --host 0.0.0.0 --port $PORT"]
