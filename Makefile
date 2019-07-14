.PHONY: clean run

clean:
	find . -name '__pycache__' -exec rm -rf {} +

run:
	python pyfzf.py
