"""Read-only execution references; no live database lookups during a batch."""

from copy import deepcopy


class ApiFlowSnapshotRepository:
    def __init__(self, tables):
        self.tables = deepcopy(tables)

    def get(self, table, item_id):
        return deepcopy(next((row for row in self.tables.get(table, []) if row["id"] == item_id), None))

    def list(self, table, keyword=None, project_id=None, page=1, page_size=20, data_filters=None):
        rows = self.tables.get(table, [])
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") == project_id]
        if keyword:
            rows = [row for row in rows if keyword in row["name"]]
        offset = (page - 1) * page_size
        return deepcopy(rows[offset:offset + page_size]), len(rows)
