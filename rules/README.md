# Rules Module Status

The Java Drools rule engine has been retired from runtime scoring.

Active deterministic fraud rule evaluation is now implemented in Python at:
- `backend/app/services/rule_evaluator.py`

The backend fraud scoring pipeline consumes this evaluator through:
- `backend/app/services/fraud_scorer.py`

This `rules/` directory is retained only for historical reference.
