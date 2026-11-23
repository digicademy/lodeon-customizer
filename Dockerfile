FROM python:3.12-slim
WORKDIR /src
COPY runtime.lock .
RUN --mount=from=model_runtime,target=/wheelhouse \
    pip install --no-cache-dir --no-deps --no-index --require-hashes \
    --find-links=/wheelhouse -r runtime.lock
COPY pyproject.toml .
COPY lodeon_customizer/ lodeon_customizer/
RUN pip install --no-cache-dir . && pip check
WORKDIR /
COPY examples/ /examples/
ENTRYPOINT ["lodeon-customizer"]
