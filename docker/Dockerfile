FROM python:3.11-rc-bullseye
WORKDIR /pixee

ENV CODEMODDER_JAVA_VERSION=0.75.1

RUN apt-get update && apt-get --no-install-recommends install -y wget unzip openjdk-17-jre && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN wget --max-redirect=1 "https://github.com/pixee/codemodder-java/releases/download/v${CODEMODDER_JAVA_VERSION}/codemodder-java-codemods-${CODEMODDER_JAVA_VERSION}.zip"
RUN unzip codemodder-java-codemods-*.zip && rm codemodder-java-codemods-*.zip

RUN python3 -m pip install pixee

COPY bin ./bin
ENV PATH="${PATH}:/pixee/bin"

WORKDIR /src

ENTRYPOINT ["pixee"]
