"""Project scalar scene summaries without loading node/request/response evidence."""

from sqlalchemy import JSON, column, func, type_coerce
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class ReportScenes(FunctionElement):
    inherit_cache = True
    name = "report_scenes"


@compiles(ReportScenes, "mysql")
def compile_report_scenes(element, compiler, **kwargs):
    document = compiler.process(element.clauses, **kwargs)
    return f"""JSON_TABLE({document}, '$.data.results[*]' COLUMNS (
        scene_index FOR ORDINALITY,
        scenario_id BIGINT PATH '$.scenario_id' NULL ON ERROR,
        scene_name VARCHAR(512) PATH '$.name' NULL ON ERROR,
        scene_status VARCHAR(32) PATH '$.status' NULL ON ERROR,
        flow_name VARCHAR(512) PATH '$.snapshot.flow.name' NULL ON ERROR,
        test_point VARCHAR(2000) PATH '$.test_point' NULL ON ERROR,
        scene_description VARCHAR(2000) PATH '$.snapshot.scenario.description' NULL ON ERROR
    ))"""


def scene_columns(db, document):
    names = ["scene_index", "scenario_id", "scene_name", "scene_status", "flow_name", "test_point", "scene_description"]
    if db.get_bind().dialect.name == "mysql":
        source = ReportScenes(document).table_valued(*(column(name) for name in names)).alias("report_scenes")
        return source, {name: source.c[name] for name in names}
    source = func.json_each(document, "$.data.results").table_valued("key", "value").alias("report_scenes")
    value = type_coerce(source.c.value, JSON)
    return source, {
        "scene_index": source.c.key + 1,
        "scenario_id": value["scenario_id"].as_integer(),
        "scene_name": value["name"].as_string(),
        "scene_status": value["status"].as_string(),
        "flow_name": value["snapshot"]["flow"]["name"].as_string(),
        "test_point": value["test_point"].as_string(),
        "scene_description": value["snapshot"]["scenario"]["description"].as_string(),
    }
