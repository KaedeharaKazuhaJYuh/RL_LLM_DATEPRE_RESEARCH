# Apache-2.0 public source; see APPWORLD_LICENSE and appworld_180_source.json.
def apply_db_changes(connection: SQLite3Connection, changes_file_path: str | None) -> list[Change]:
    if changes_file_path is None:
        return []
    if not os.path.exists(changes_file_path):
        return []
    if "memory" in changes_file_path:
        raise Exception(
            "Invalid changes_file_path. It cannot contain in-memory connection strings."
        )
    raw_changes = read_jsonl(changes_file_path, use_json_plus=False)
    changes: list[Change] = cast(list[Change], raw_changes)
    for statement, parameters, executemany in changes:
        if executemany:
            connection.executemany(statement, parameters)
        else:
            connection.execute(statement, parameters)
    connection.commit()
    return changes
