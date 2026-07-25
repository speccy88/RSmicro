import json
from importlib.resources import files
from rsmicro.diagnostics import Diagnostic,Severity
def load_schema(name="project"):
 return json.loads(files("rsmicro.schemas").joinpath(f"{name}.schema.json").read_text(encoding="utf-8"))
def validate_schema(instance,name="project",source_file=None):
 try:
  import jsonschema
  validator=jsonschema.Draft202012Validator(load_schema(name),format_checker=jsonschema.FormatChecker())
  return [Diagnostic(Severity.ERROR,"SCHEMA_INVALID",e.message,source_file,"/"+"/".join(map(str,e.absolute_path))) for e in sorted(validator.iter_errors(instance),key=lambda x:list(x.absolute_path))]
 except ImportError:
  required=load_schema(name).get("required",[])
  return [Diagnostic(Severity.ERROR,"SCHEMA_REQUIRED",f"Missing required property: {key}",source_file,f"/{key}") for key in required if key not in instance]
