FROM python:3.7-alpine

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY hello.py ./

CMD [ "python", "./hello.py" ]