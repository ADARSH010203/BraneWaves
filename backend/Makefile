.PHONY: test eval run

test:
	pytest tests/ -v

eval:
	python evals/run_eval.py

run:
	uvicorn app.main:app --reload
