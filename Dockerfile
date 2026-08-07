FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache gcc musl-dev

# Copy requirements
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY run.sh /
RUN chmod a+x /run.sh

EXPOSE 8099

CMD ["/run.sh"]
