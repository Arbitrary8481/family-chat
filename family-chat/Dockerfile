# Pinned to a specific Alpine version deliberately — not just "3.11-alpine".
# That untagged form is a moving target: it resolves to whatever Alpine
# release currently backs it, and this add-on's build always runs with
# --pull (fetches the latest matching image on every build, every time).
# python:3.11-alpine built against Alpine 3.20+ has a well-documented,
# widely-reported bug (docker-library/python#927, #930 — same issue
# affects the 3.12 tag too) where the interpreter itself fails to start:
# "Error loading shared library libpython3.11.so.1.0: No such file or
# directory" / "Error relocating ...: Py_BytesMain: symbol not found".
# alpine3.19 is the version the community confirmed does NOT have this
# problem. Pinning here means a future Alpine release breaking the same
# way again can't silently break this add-on on its next rebuild.
FROM python:3.11-alpine3.19

WORKDIR /app

# Install dependencies first
RUN apk add --no-cache gcc musl-dev

# Copy requirements and install
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Copy and chmod run.sh (AFTER copying it!)
COPY run.sh /
RUN chmod a+x /run.sh

EXPOSE 8099

CMD ["/run.sh"]
