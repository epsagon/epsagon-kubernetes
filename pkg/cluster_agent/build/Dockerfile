FROM python:3.7

RUN mkdir /app
WORKDIR /app
ADD *.py /app/
ADD requirements.txt /app/
RUN pip install -r requirements.txt

CMD ["python", "-u", "/app/main.py"]
