import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


# ---------- auth ----------

class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=64)
    display_name: str = Field(default="", max_length=64)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    display_name: str


# ---------- batch ----------

class BatchIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    year: int = Field(ge=2000, le=2100)
    activate: bool = True


class StageIn(BaseModel):
    stage: str


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    year: int
    stage: str
    is_active: bool
    created_at: dt.datetime | None = None


class DeptStat(BaseModel):
    dept: str
    applied: int
    exempt_exam: int
    submitted: int
    advanced: int
    admitted: int


class BatchStatsOut(BaseModel):
    batch_id: int
    funnel: dict[str, int]  # applied / submitted / advanced / interviewed / admitted
    dept_stats: list[DeptStat]


# ---------- form template ----------

class FormSchemaIn(BaseModel):
    name: str = Field(default="", max_length=128)
    # 字段名避开 BaseModel.schema_json；wire 格式仍为 schema_json
    form_schema: dict = Field(validation_alias="schema_json", serialization_alias="schema_json")


class FormTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    kind: str
    name: str
    form_schema: dict = Field(validation_alias="schema_json", serialization_alias="schema_json")
    version: int


# ---------- application ----------

class ApplicationIn(BaseModel):
    batch_id: int
    student_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=5, max_length=20)
    dept_choice: str = Field(min_length=1, max_length=32)
    source: str = "online"  # online / onsite
    exempt_exam: bool = False
    extra: dict = Field(default_factory=dict)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    student_no: str
    name: str
    phone: str
    dept_choice: str
    source: str
    exempt_exam: bool
    status: str
    extra: dict
    created_at: dt.datetime | None = None


# ---------- submission ----------

class SubmissionIn(BaseModel):
    application_id: int
    template_id: int
    data: dict


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    template_id: int
    status: str
    submitted_at: dt.datetime | None = None


# ---------- queue ----------

class GroupIn(BaseModel):
    batch_id: int
    name: str = Field(min_length=1, max_length=64)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    name: str
    seq: int


class CheckinIn(BaseModel):
    group_id: int
    application_id: int


class CallIn(BaseModel):
    room: str = Field(min_length=1, max_length=32)


class QueueEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    application_id: int
    seq: int
    status: str
    room: str | None = None


# ---------- exam answer ----------

class ExamAnswerIn(BaseModel):
    content: str = Field(max_length=20000)
    published: bool = False


class ExamAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int
    content: str
    published: bool
    published_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
