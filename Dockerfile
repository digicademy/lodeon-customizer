FROM python:3.12-slim
WORKDIR /src
RUN --mount=from=model_runtime,target=/wheelhouse \
    pip install --no-cache-dir /wheelhouse/*.whl
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir . && pip check
COPY --from=core /config/resolver/ /opt/lodeon/config/resolver/
COPY --from=core /config/config.yml /opt/lodeon/config/config.yml
COPY config.yml lodeon.package.yml /opt/customizer/
ENV PYTHONPATH=/opt/lodeon/config
WORKDIR /opt/customizer
ENTRYPOINT ["lodeon-customizer"]
CMD ["serve"]
