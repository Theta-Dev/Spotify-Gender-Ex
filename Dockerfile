FROM debian:bullseye-slim

# Install packages
RUN apt-get update \
    && apt-get install -y openjdk-11-jre-headless python3 python3-setuptools \
    && apt-get clean

# Copy files
COPY setup.py README.md LICENSE /app/
COPY spotify_gender_ex /app/spotify_gender_ex

# Install python package
RUN groupadd --gid 1000 gex && useradd --uid 1000 --gid 1000 -m gex \
  && mkdir /GenderEx && chown 1000:1000 /GenderEx && chmod -R +r /app \
  && cd /app && python3 setup.py develop

# Run GenderEx on startup
ENTRYPOINT ["spotify-gender-ex", "--noia"]
