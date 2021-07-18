FROM python:3.8

WORKDIR /mascotas-model-app

COPY ["requirements.txt", "."]

COPY ./saved_model ./saved_model

COPY ["./src", "./src"]

COPY ["app.py", "."]

EXPOSE 5000

RUN apt-get update && apt-get install -y build-essential cmake python3-opencv

ENV PYTHONPATH="/mascotas-model-app:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1

RUN ["pip", "install", "-r", "requirements.txt"]

CMD ["python", "app.py"]