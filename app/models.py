from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from enum import Enum
import uuid

MAX_TITLE_LENGTH = 200
MAX_INGREDIENTS = 50
MAX_DESCRIPTION_LENGTH = 2000
MAX_INSTRUCTIONS_LENGTH = 10000


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    ingredients: List[str] = Field(..., min_length=1, max_length=MAX_INGREDIENTS)
    instructions: str = Field(..., min_length=1, max_length=MAX_INSTRUCTIONS_LENGTH)
    tags: List[str] = Field(default_factory=list)
    difficulty: DifficultyLevel

    @field_validator("ingredients")
    @classmethod
    def ingredients_must_not_be_blank(cls, value: List[str]) -> List[str]:
        if any(not ingredient.strip() for ingredient in value):
            raise ValueError("Ingredients cannot be empty or whitespace-only strings")
        return value

    @field_validator("title", "description", "instructions")
    @classmethod
    def fields_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty or whitespace-only")
        return value.strip()


class Recipe(RecipeBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(RecipeBase):
    pass


class RecipeImport(RecipeBase):
    """Schema for validating imported recipe JSON files."""

    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
