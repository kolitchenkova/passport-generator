from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["Categories"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(category_data: CategoryCreate, session: SessionDep):  # type: ignore
    """Создать новую категорию изделий."""
    category = Category(**category_data.model_dump())
    session.add(category)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Категория с названием '{category_data.name}' уже существует",
        )
    await session.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
async def get_categories(session: SessionDep):  # type: ignore
    """Получить список всех категорий."""
    result = await session.scalars(select(Category).order_by(Category.name))
    return result.all()


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, session: SessionDep):  # type: ignore
    """Получить категорию по ID."""
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    return category
