# SPDX-License-Identifier: Apache-2.0
# AppWorld public-source excerpts, StonyBrookNLP/appworld, commit 42b5bcf3cd334fee33f0c37c02070a9f5807add5.
# See APPWORLD_LICENSE and appworld_175_source.json. Protected application source is not included.
from __future__ import annotations

def _validate_model_name(model_name: str) -> None:
    if model_name.count(".") != 1:
        raise Exception(f"Field name must be app_name.ClassName. Found {model_name}.")

def _changed_model_names(
    self, include: list[str] | None = None, ignore: list[str] | None = None
) -> set[str]:
    if isinstance(include, str):
        raise Exception(f"'include' must be a list of strings. Found {include}")

    if isinstance(ignore, str):
        raise Exception(f"'ignore' must be a list of strings. Found {ignore}")

    include_model_names = include or []
    ignore_model_names = ignore or []

    if "supervisor.Task" not in ignore_model_names:
        ignore_model_names.append("supervisor.Task")

    if "admin.PaymentCard" not in ignore_model_names:
        ignore_model_names.append("admin.PaymentCard")

    if "amazon.BrowsedProduct" not in ignore_model_names:
        # This was added after V1 and no task requires updating it, so ignoring it globally for now.
        ignore_model_names.append("amazon.BrowsedProduct")

    if include_model_names is None and ignore_model_names is None:
        raise Exception(
            "At least one of include_model_names and ignore_model_names must be not None."
        )

    start_app_names = list(self.start.keys())
    end_app_names = list(self.end.keys())
    if set(start_app_names) != set(end_app_names):
        raise Exception(
            "The app names for model_collection_start for model_collection_end don't match."
        )

    all_model_names: list[str] = []
    for app_name in start_app_names:
        app_start_model_names = self.start[app_name].SQLModel.model_names()
        app_end_model_names = self.end[app_name].SQLModel.model_names()
        assert (
            app_start_model_names == app_end_model_names
        ), f"The class names for {app_name} for model_collection_start for model_collection_end don't match."
        all_model_names += [f"{app_name}.{model_name}" for model_name in app_start_model_names]

    candidate_model_names = all_model_names

    if include_model_names:
        for model_name in include_model_names:
            assert (
                model_name.count(".") == 1
            ), f"Field name must be app_name.ClassName. Found {model_name}."
        assert (model_name in all_model_names for model_name in include_model_names)
        candidate_model_names = include_model_names

    elif ignore_model_names:
        for model_name in ignore_model_names:
            assert (
                model_name.count(".") == 1
            ), f"Field name must be app_name.ClassName. Found {model_name}."
        candidate_model_names = [
            model_name for model_name in all_model_names if model_name not in ignore_model_names
        ]

    candidate_model_names = [
        model_name
        for model_name in candidate_model_names
        if not model_name.endswith("ModelHash")
    ]

    start_model_hashes = self.start.model_hashes()
    end_model_hashes = self.end.model_hashes()
    for candidate_model_name in list(candidate_model_names):  # list(..) is to make a copy
        if start_model_hashes[candidate_model_name] == end_model_hashes[candidate_model_name]:
            candidate_model_names.remove(candidate_model_name)

    changed_model_names_: set[str] = set()
    for model_name in candidate_model_names:
        app_name, class_name = model_name.split(".")
        size_1 = getattr(self.start[app_name], class_name).size()
        size_2 = getattr(self.end[app_name], class_name).size()
        if size_1 != size_2:
            changed_model_names_.add(model_name)
            continue
        start_record_hashes = self.start.record_hashes(app_name, class_name)
        end_record_hashes = self.end.record_hashes(app_name, class_name)
        if set(start_record_hashes) != set(end_record_hashes):
            changed_model_names_.add(model_name)

    formatted_changed_model_names: set[str] = set()
    for model_name in changed_model_names_:
        app_name, table_name = model_name.split(".")
        class_name = modelize(table_name)
        formatted_changed_model_names.add(f"{app_name}.{class_name}")

    return formatted_changed_model_names

def _changed_records(
    self, model_name: str, updated_state: str = "end"
) -> tuple[list[SQLModel], list[SQLModel], list[SQLModel]]:
    """
    Returns list in the following order:
    added_records: records from end state that are not in start state (match by id)
    updated_records:
        records for which ID exists in both start and end state but some of the
        fields have been updated. This is computed by a hash-based difference
        between records. You can control whether you want to obtain these updated
        records in end or start state via 'updated_state' argument.
    removed_records: records from start state that are not in end state (match by id)
    EDIT: If a record exists in both added and deleted (matched by hash), they will cancel
    out each other and be removed from both added and deleted.
    """
    assert updated_state in [
        "start",
        "end",
    ], f"updated_state must be either 'start' or 'end'. Found {updated_state}."
    _validate_model_name(model_name)
    app_name, model_class_name = model_name.split(".")
    start_ids = self.start.ids(app_name, model_class_name)
    end_ids = self.end.ids(app_name, model_class_name)
    added_records = self.end[app_name][model_class_name].by_ids(end_ids - start_ids)
    removed_records = self.start[app_name][model_class_name].by_ids(start_ids - end_ids)
    if updated_state == "end":
        ids_hashes_1 = self.end.ids_record_hashes(app_name, model_class_name)
        ids_2 = self.start.ids(app_name, model_class_name)
        record_hashes_2 = self.start.record_hashes(app_name, model_class_name)
        klass = self.end[app_name][model_class_name]
    else:
        ids_hashes_1 = self.start.ids_record_hashes(app_name, model_class_name)
        ids_2 = self.end.ids(app_name, model_class_name)
        record_hashes_2 = self.end.record_hashes(app_name, model_class_name)
        klass = self.start[app_name][model_class_name]
    updated_ids = [
        id_hash[0]
        for id_hash in ids_hashes_1
        if (id_hash[1] not in record_hashes_2) and (id_hash[0] in ids_2)
    ]
    updated_records = klass.by_ids(updated_ids)
    # cancel out added and removed records that have identical .record_hash,
    # one entry should cancel only one other entry.
    record_hash_to_added_records = defaultdict(list)
    for record in added_records:
        record_hash_to_added_records[record.record_hash].append(record)
    record_hash_to_removed_records = defaultdict(list)
    for record in removed_records:
        record_hash_to_removed_records[record.record_hash].append(record)
    added_records = []
    removed_records = []
    added_or_removed_record_hashes = set(
        record_hash_to_added_records.keys() | record_hash_to_removed_records.keys()
    )
    for record_hash in added_or_removed_record_hashes:
        added_records_ = record_hash_to_added_records[record_hash]
        removed_records_ = record_hash_to_removed_records[record_hash]
        min_len = min(len(added_records_), len(removed_records_))
        added_records += added_records_[min_len:]
        removed_records += removed_records_[min_len:]
    return added_records, updated_records, removed_records

def set_record_hash(self) -> None:
    hash_dict = {
        property_name: getter_plus(self, property_name)
        for property_name in self.properties(skip=("_db_home_path", "record_hash", "id"))
    }
    hash_dict = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in hash_dict.items()
    }
    serialized = orjson.dumps(hash_dict, option=orjson.OPT_SORT_KEYS)
    hash_obj = xxhash.xxh64()
    hash_obj.update(serialized)
    record_hash = base64.b64encode(hash_obj.digest()).decode()
    self.record_hash = record_hash
