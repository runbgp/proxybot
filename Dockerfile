FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1

COPY ./ /proxybot
WORKDIR /proxybot

RUN pip3 install -r requirements.txt

CMD ["python3", "proxybot.py"]