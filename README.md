## Langchain Server

This is the server for the DevAssist Project by team HighOn420. It is a RESTful API server that provides endpoints for the Langchain for the frontend to consume.

API documentation for the Langchain server:- 

[<img src="https://run.pstmn.io/button.svg" alt="Run In Postman" style="width: 128px; height: 32px;">](https://god.gw.postman.com/run-collection/33649839-4ca2c43c-1776-4612-b4e9-0d3f9a1c286c?action=collection%2Ffork&source=rip_markdown&collection-url=entityId%3D33649839-4ca2c43c-1776-4612-b4e9-0d3f9a1c286c%26entityType%3Dcollection%26workspaceId%3D48af9bc0-5292-4799-8ba2-9db11d57ed3c)

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
