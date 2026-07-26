# apps/

Reserved for Django apps added in later parts (accounts, projects,
payments, files, ...). Empty in Part 1 on purpose: no database models
are implemented yet.

Each new app gets registered in `config/settings/base.py` under
`LOCAL_APPS`, and its own `urls.py` gets included from `config/urls.py`.
