.PHONY: clean run

clean:
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name 'debug.log' -exec rm -f {} +

run:
	python fuzzyfinder.py
