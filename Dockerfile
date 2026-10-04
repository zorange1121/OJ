FROM debian:bookworm-slim AS gpsim-build

RUN sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends dpkg-dev patch \
    && apt-get build-dep -y gpsim=0.31.0-2

WORKDIR /build
RUN apt-get source gpsim=0.31.0-2
COPY sandbox-patches/gpsim-addwf-postinc.patch /build/
RUN cd gpsim-0.31.0 \
    && patch -p1 --forward < ../gpsim-addwf-postinc.patch \
    && DEB_BUILD_OPTIONS="nocheck parallel=$(nproc)" dpkg-buildpackage -b -uc -us

FROM debian:bookworm-slim

COPY --from=gpsim-build /build/gpsim_0.31.0-2_*.deb /tmp/
RUN apt-get update && apt-get install -y \
    gputils \
    /tmp/gpsim_0.31.0-2_*.deb \
    python3 \
    && rm -rf /var/lib/apt/lists/* /tmp/*.deb

WORKDIR /app
COPY sandbox_runner.py /usr/local/bin/sandbox_runner.py
USER 65534:65534
ENTRYPOINT ["python3", "/usr/local/bin/sandbox_runner.py"]
