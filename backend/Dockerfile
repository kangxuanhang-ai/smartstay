FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com poetry && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry config repositories.aliyun https://mirrors.aliyun.com/pypi/simple/ && poetry install --no-interaction --no-ansi --only main

COPY . .

EXPOSE 8765

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
