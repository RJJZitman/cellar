import fastapi.openapi.utils

from typing import Optional
from pydantic.fields import ModelField
from pydantic.schema import field_schema
from typing import Any, Dict, Union, Type
from pydantic import BaseModel
from fastapi.openapi.constants import REF_PREFIX

from enum import Enum

orig_get_request_body = fastapi.openapi.utils.get_openapi_operation_request_body


# Monkeypatch to fix swagger UI bug: https://github.com/tiangolo/fastapi/issues/3532
def get_request_body_with_explode(*,
                                  body_field: Optional[ModelField],
                                  model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
                                  ) -> Optional[Dict[str, Any]]:
    """
    Monkeypatch to fix swagger UI bug: https://github.com/tiangolo/fastapi/issues/3532
    Without this monkeypatch, form data input does not work properly in Swagger UI when allowing the selection of
    multiple arguments (i.e. selecting one or more scopes from a specief list of options)
    """
    original = orig_get_request_body(body_field=body_field, model_name_map=model_name_map)
    if not original:
        return original
    content = original.get("content", {})
    if form_patch := (
            content.get("application/x-www-form-urlencoded")
            or content.get("multipart/form-data")
    ):
        schema_reference, schemas, _ = field_schema(
            body_field, model_name_map=model_name_map, ref_prefix=REF_PREFIX
        )
        array_props = []
        for schema in schemas.values():  # type: Dict[str, Any]
            for prop, prop_schema in schema.get("properties", {}).items():
                if prop_schema.get("type") == "array":
                    array_props.append(prop)

        form_patch["encoding"] = {prop: {"style": "form"} for prop in
                                  array_props}  # could include "explode": True but not necessary in swagger-ui

    return original
