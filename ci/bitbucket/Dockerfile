FROM codemodder/pixee-cli:0.8.15
COPY . /pixee/bitbucket
WORKDIR /pixee/bitbucket
RUN pip install whatthepatch load_dotenv
RUN chmod 755 /pixee/bitbucket/pipe.sh

ENTRYPOINT ["/pixee/bitbucket/pipe.sh"]
