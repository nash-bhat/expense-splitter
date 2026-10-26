"""Pydantic request and response models. All money is integer paise."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    members: list[str] = Field(default_factory=list)

    @field_validator("members")
    @classmethod
    def names_not_blank(cls, names: list[str]) -> list[str]:
        if any(not n.strip() for n in names):
            raise ValueError("member names must not be blank")
        return names


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    members: list[MemberOut]


class ExpenseIn(BaseModel):
    payer_id: int
    amount_paise: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=200)
    split_among: list[int] = Field(min_length=1, description="Member ids sharing the expense equally")

    @field_validator("split_among")
    @classmethod
    def unique_ids(cls, ids: list[int]) -> list[int]:
        if len(set(ids)) != len(ids):
            raise ValueError("split_among must not contain duplicates")
        return ids


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_id: int
    share_paise: int


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payer_id: int
    amount_paise: int
    description: str
    shares: list[ShareOut]


class BalanceOut(BaseModel):
    member_id: int
    name: str
    balance_paise: int = Field(description="Positive: is owed money. Negative: owes money.")


class TransferOut(BaseModel):
    from_member_id: int
    from_name: str
    to_member_id: int
    to_name: str
    amount_paise: int
    summary: str
