# Branch Protection Required Checks

GitHub branch protection cannot be configured directly from repository code.
Apply the settings below in repository settings for `main` and `develop`.

## Required status checks

- `backend-tests`
- `ingest-contract-integrity`
- `phase1-integrity`
- `approval-route-tests`
- `frontend-build`
- `lint-python`
- `lint-typescript`
- `test-python`
- `test-approval-routes`
- `test-frontend`
- `security-scan`
- `docker-build`

## Recommended branch protection toggles

- Require a pull request before merging
- Require approvals: minimum 1
- Dismiss stale pull request approvals when new commits are pushed
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Include administrators (recommended for strict compliance)
