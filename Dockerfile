FROM adoptopenjdk/openjdk8:debian-slim

VOLUME /GenderEx

WORKDIR /app

# Copy files
COPY . /app

# Installation
RUN apt-get update \
  && apt-get -y install python3 python3-setuptools \
  && rm -rf /var/lib/apt/lists/* \
  && python3 setup.py develop

# Run GenderEx on startup
WORKDIR /
ENTRYPOINT ["spotify-gender-ex", "--noia", "--cleanup", "5"]