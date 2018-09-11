FROM python:3.6-alpine

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR ./app/
COPY . ./app/

CMD [ "python", "./fetch.py" ]