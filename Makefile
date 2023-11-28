PYTEST = pytest -v
COV_FLAGS = --cov-fail-under=95 --cov=codemodder --cov=core_codemods

test:
	${PYTEST} ${COV_FLAGS} tests

lint:
	pylint -v pixee
