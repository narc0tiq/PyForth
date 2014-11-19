
all: test
	@

clean:
	find . -iname '*.pyc' -delete
	find . -iname '__pycache__' -type d -delete

test:
	py.test -q tests/

full-test:
	py.test --cov forth tests/

