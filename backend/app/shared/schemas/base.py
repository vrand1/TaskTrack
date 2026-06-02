from pydantic import BaseModel, ConfigDict

API_MODEL_CONFIG = ConfigDict(
    str_strip_whitespace=True,
    validate_assignment=True,
    extra="forbid",
)


class APIModel(BaseModel):
    model_config = API_MODEL_CONFIG
