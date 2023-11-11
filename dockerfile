FROM python:3.11

RUN apt-get update && apt-get install -y openssl build-essential xorg libssl-dev

WORKDIR /app

COPY ./requirements.txt /app/
COPY . /app/

RUN pip install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 8000:8000
CMD ["uvicorn", "manage:app", "--host", "0.0.0.0", "--reload", "--port", "8000"]