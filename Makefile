PYTEST_FLAGS += $(if $(CIRCLE_TEST_REPORTS), --junitxml=$(CIRCLE_TEST_REPORTS)/report.xml,)

all: test
	@

clean:
	find . -iname '*.pyc' -delete
	find . -iname '__pycache__' -type d -delete

test:
	py.test -q tests/ $(PYTEST_FLAGS)

full-test:
	py.test --cov forth tests/ $(PYTEST_FLAGS)

