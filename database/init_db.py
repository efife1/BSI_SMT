from database.migrate import migrate

RESULT = migrate(make_backup=False)
