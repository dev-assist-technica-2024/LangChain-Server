## Langchain Server

This is the server for the DevAssist Project by team HighOn420. It is a RESTful API server that provides endpoints for the Langchain for the frontend to consume.

API documentation for the Langchain server:- 

[![Postman](https://run.pstmn.io/button.svg)](https://documenter.getpostman.com/view/19816367/2sA2xnw94A)

## Getting Started

To get started with the project, you need to have the following installed on your machine:

- Docker
- Docker Compose
- Python 3.8

You additonally need to create an pip environment and install the dependencies.

```bash
pip install -r requirements.txt
```

## Running the server

Running using the following command:

```bash
uvicorn main:app --reload
```

## Running the server on Docker

To run the server, you need to have Docker installed on your machine. You can then run the following command to start the server:

1) Build the Docker image
```bash
docker build -t langchain-server .
```

2) Run the Docker image
```bash
docker run -p 8000:8000 langchain-server
```