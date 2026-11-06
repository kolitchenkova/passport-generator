from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Категории ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)


class CategoryRead(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Параметры ---
class ParameterBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=150)
    unit: str | None = Field(None, max_length=30)


class ParameterCreate(ParameterBase):
    pass


class ParameterRead(ParameterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Характеристики изделия (M:M) ---
class ProductParameterValue(BaseModel):
    parameter_id: int
    value: str = Field(..., min_length=1, max_length=255)


class ProductParameterRead(BaseModel):
    parameter_id: int
    parameter_code: str | None = None
    parameter_title: str | None = None
    unit: str | None = None
    value: str
    model_config = ConfigDict(from_attributes=True)


# --- Изделия ---
class ProductBase(BaseModel):
    sku: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    category_id: int


class ProductCreate(ProductBase):
    parameters: list[ProductParameterValue] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    sku: str | None = Field(None, min_length=3, max_length=50)
    name: str | None = Field(None, min_length=2, max_length=200)
    category_id: int | None = None


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductDetailRead(ProductRead):
    category_name: str | None = None
    parameters: list[ProductParameterRead] = Field(default_factory=list)


# --- Шаблоны ---
class TemplateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    file_path: str = Field(..., min_length=3, max_length=255)
    required_parameter_codes: list[str] = Field(default_factory=list)
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateRead(TemplateBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- История генераций ---
class GenerationLogRead(BaseModel):
    id: int
    product_id: int
    template_id: int
    created_at: datetime
    status: str
    output_filename: str | None = None
    error_message: str | None = None
    model_config = ConfigDict(from_attributes=True)
