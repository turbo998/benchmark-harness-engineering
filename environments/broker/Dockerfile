ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY environments/broker/requirements.txt /app/broker-requirements.txt
COPY environments/broker/build-requirements.txt /app/build-requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /app/broker-requirements.txt -r /app/build-requirements.txt
COPY pyproject.toml uv.lock README.md LICENSE /app/
COPY src /app/src
RUN pip install --no-cache-dir --no-deps --no-build-isolation /app && useradd --create-home --uid 10001 broker
USER 10001
EXPOSE 8080
CMD ["python", "-m", "benchmark_harness.broker", "serve", "--port", "8080"]
