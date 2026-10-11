# Owned standalone SDK consumer

This mini-project imports the installed public Python hook and scikit-learn.
It does not import repository examples, storage or collector internals. A separately
implemented scaled logistic classifier trains on bundled public UCI digits and
invokes its actual inference through the SDK. It selects one natural held-out
error for the integration boundary; this selection does not measure detector quality.

Run `python scripts/check_onboarding.py --directory data/new-onboarding` from a
prepared Python 3.13 environment. The driver builds a wheel, creates a new venv,
installs locked dependencies, copies this consumer into a separate working
directory, starts the installed collector with named accounts and runs the consumer.
Its only application credentials are passed through environment variables.
The copied application has no repository imports or editable installation.
All owned services stop; generated private state stays under ignored `data/`.

This is an owned installation/integration check. No external developer was
observed, and completion does not establish independent usability, recurring use
or production model performance. UCI attribution: Alpaydin and Kaynak (1998),
DOI 10.24432/C50P49, CC BY 4.0; scikit-learn redistributes the digit subset.
