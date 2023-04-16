FROM python:alpine3.16
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD [ "python", "nexus_cleaner.py"]