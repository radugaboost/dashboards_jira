FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY ./main.py /app/main.py

EXPOSE 8050

CMD ["python", "main.py"]