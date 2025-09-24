build:
	poetry install

setup:
	echo

unittest:
	poetry run pytest tests

run:
	poetry run streamlit run src/kb_web_svc/app.py