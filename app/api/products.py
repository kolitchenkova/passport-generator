from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_session
from app.models import Category, Product, ProductParameter
from app.schemas import (
    ProductCreate,
    ProductDetailRead,
    ProductParameterRead,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(product_data: ProductCreate, session: SessionDep):  # type: ignore
    """Создать новое изделие с привязкой параметров."""
    # Проверяем существование категории
    category = await session.get(Category, product_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Категория с ID {product_data.category_id} не найдена",
        )

    product = Product(
        sku=product_data.sku,
        name=product_data.name,
        category_id=product_data.category_id,
    )
    session.add(product)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Изделие с артикулом (SKU) '{product_data.sku}' уже существует",
        )

    # Привязываем переданные характеристики M:M
    for p_val in product_data.parameters:
        assoc = ProductParameter(
            product_id=product.id,
            parameter_id=p_val.parameter_id,
            value=p_val.value,
        )
        session.add(assoc)

    await session.commit()
    await session.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
async def get_products(
    session: SessionDep,  # type: ignore
    category_id: int | None = Query(None, description="Фильтр по категории"),
    search: str | None = Query(None, description="Поиск по артикулу или названию"),
    sort_by: str = Query("id", pattern="^(id|sku|name|created_at)$", description="Поле сортировки"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Порядок сортировки"),
    limit: Annotated[int, Query(ge=1, le=100, description="Количество записей")] = 20,
    offset: Annotated[int, Query(ge=0, description="Смещение")] = 0,
):
    """Список изделий с пагинацией, фильтрацией и сортировкой (пункт 6 задания)."""
    query = select(Product)

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if search:
        query = query.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))

    order_col = getattr(Product, sort_by)
    query = query.order_by(desc(order_col) if sort_order == "desc" else asc(order_col))
    query = query.offset(offset).limit(limit)

    result = await session.scalars(query)
    return result.all()


@router.get("/{product_id}", response_model=ProductDetailRead)
async def get_product(product_id: int, session: SessionDep):  # type: ignore
    """Получить детальную информацию об изделии со всеми характеристиками."""
    query = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.parameters_assoc).selectinload(ProductParameter.parameter),
        )
    )
    product = (await session.scalars(query)).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")

    params_dto = [
        ProductParameterRead(
            parameter_id=assoc.parameter_id,
            parameter_code=assoc.parameter.code if assoc.parameter else None,
            parameter_title=assoc.parameter.title if assoc.parameter else None,
            unit=assoc.parameter.unit if assoc.parameter else None,
            value=assoc.value,
        )
        for assoc in product.parameters_assoc
    ]

    return ProductDetailRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        created_at=product.created_at,
        category_name=product.category.name if product.category else None,
        parameters=params_dto,
    )


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, update_data: ProductUpdate, session: SessionDep):  # type: ignore
    """Частичное обновление изделия (PATCH) через exclude_unset=True."""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")

    patch_dict = update_data.model_dump(exclude_unset=True)

    if "category_id" in patch_dict and patch_dict["category_id"] is not None:
        cat = await session.get(Category, patch_dict["category_id"])
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Категория с ID {patch_dict['category_id']} не найдена",
            )

    for field, value in patch_dict.items():
        setattr(product, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Артикул (SKU) '{update_data.sku}' уже занят другим изделием",
        )

    await session.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, session: SessionDep):  # type: ignore
    """Удалить изделие по ID."""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")

    try:
        await session.delete(product)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить изделие, так как по нему существует история генераций паспортов",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
