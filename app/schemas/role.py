from pydantic import BaseModel


class RoleSummary(BaseModel):
    role_id: str
    role_name: str
    description: str | None
    is_system_role: bool

    model_config = {"from_attributes": True}