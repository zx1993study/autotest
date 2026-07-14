# Database migrations

Run `alembic upgrade head` before starting the API with
`AUTO_CREATE_SCHEMA=false`.

For an existing database previously managed by `Base.metadata.create_all`,
verify that its schema matches the initial revision, then run
`alembic stamp 20260710_0001` once instead of recreating tables.
