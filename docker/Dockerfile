FROM python:3.13-rc-bullseye
WORKDIR /pixee

RUN apt-get update

# Install Python 3, pip and wget
RUN apt-get install -y wget unzip openjdk-17-jre

RUN ln -s /usr/bin/python3 /usr/bin/python && \
    java -version && \
    python --version && \
    python3 -m pip install semgrep==1.15.0 && \
    python3 -m pip install codemodder

RUN wget https://github.com/pixee/codemodder-java/releases/download/v0.72.2/codemodder-java-codemods-0.72.2.zip
RUN unzip codemodder-java-codemods-0.72.2.zip

RUN python3 -m pip install pixee

COPY bin ./bin
ENV PATH="${PATH}:/pixee/bin"
