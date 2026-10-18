from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Numeric, JSON
from src.database import Base
from decimal import Decimal
from typing import List

class SchemaManifest(BaseModel):
    
    version: str= "1.0.0"
    lambda_details = lambda: ["txn_ref", "value_date", "currency", "amount"]

    join_keys: List[str] = Field(default_factory=lambda_details)

    amount_tolerance: Decimal = Field(default=Decimal("0.01"))

    required_fields_ledger: List[str] = Field(default_factory=lambda_details)

    required_fields_settlement: List[str] = Field(default_factory=lambda_details)

    date_format: str = Field(default="%Y-%m-%d")

class SchemaManifestDB(Base):
    __tablename__ = "schema_manifests"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), nullable=False)
    join_keys = Column(JSON, nullable=False)
    amount_tolerance = Column(Numeric(10, 4), nullable=False)
    required_fields_ledger = Column(JSON, nullable=False)
    required_fields_settlement = Column(JSON, nullable=False)
    date_format = Column(String(30), nullable=False)