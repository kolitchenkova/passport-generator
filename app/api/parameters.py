from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Parameter
from app.schemas import ParameterCreate, ParameterRead

router = APIRouter(prefix="/parameters", tags=["Parameters"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=ParameterRead, status_code=status.HTTP_201_CREATED)
async def create_parameter(param_data: ParameterCreate, session: SessionDep):  # type: ignore
    """Создать новый технический параметр."""
    parameter = Parameter(**param_data.model_dump())
    session.add(parameter)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Параметр с кодом '{param_data.code}' уже существует",
        )
    await session.refresh(parameter)
    return parameter


@router.get("", response_model=list[ParameterRead])
async def get_parameters(session: SessionDep):  # type: ignore
    """Получить справочник всех параметров."""
    result = await session.scalars(select(Parameter).order_by(Parameter.code))
    return result.all()
