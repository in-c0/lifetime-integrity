.PHONY: test pilot pilot-drift pilot-credit lifetimes lint bundle

test:
	PYTHONPATH=src pytest -q

pilot:
	PYTHONPATH=src python scripts/run_pilot.py --seed 20260902

pilot-drift:
	PYTHONPATH=src python scripts/run_pilot.py --seed 20260902 --stream drift

pilot-credit:
	PYTHONPATH=src python scripts/run_pilot.py --seed 20260902 --stream delayed_credit

lifetimes:
	PYTHONPATH=src python scripts/generate_lifetimes.py --seed 20260902

lint:
	ruff check src scripts tests

bundle:
	git archive --format=zip --output=../lifetime-integrity-repo.zip HEAD
