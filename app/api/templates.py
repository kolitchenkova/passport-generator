from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Template
from app.schemas import TemplateCreate, TemplateRead

router = APIRouter(prefix="/templates", tags=["Templates"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(tmpl_data: TemplateCreate, session: SessionDep):  # type: ignore
    """Зарегистрировать новый шаблон паспорта."""
    tmpl = Template(**tmpl_data.model_dump())
    session.add(tmpl)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Шаблон с путем к файлу '{tmpl_data.file_path}' уже зарегистрирован",
        )
    await session.refresh(tmpl)
    return tmpl


@router.get("", response_model=list[TemplateRead])
async def get_templates(session: SessionDep):  # type: ignore
    """Получить список доступных шаблонов DOCX."""
    result = await session.scalars(select(Template).where(Template.is_active.is_(True)))
    return result.all()
