FROM python:3.7.10-alpine

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD [ "python", "-u", "relay_m2.py" ]
