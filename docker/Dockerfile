FROM python:3.11-rc-bullseye
WORKDIR /pixee

RUN apt-get update

# Install Python 3, pip and wget
RUN apt-get install -y wget unzip openjdk-17-jre

RUN ln -s /usr/bin/python3 /usr/bin/python && \
    java -version && \
    python --version && \
    python3 -m pip install semgrep==1.15.0 && \
    python3 -m pip install codemodder

# TODO we need to add automation to grab the latest
RUN wget https://github.com/pixee/codemodder-java/releases/download/v0.72.2/codemodder-java-codemods-0.72.2.zip
RUN unzip codemodder-java-codemods-0.72.2.zip
RUN wget https://worker-brew.pixee.workers.dev/ad/6c/3c4ada32a280b207b65672324cb516b1a97f85952f7f9d69a62c1704e5ba/pixee-0.5.5.tar.gz

RUN python3 -m pip install ./pixee-0.5.5.tar.gz

COPY bin ./bin
ENV PATH="${PATH}:/pixee/bin"
