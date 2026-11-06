"""API-эндпоинты для генерации и скачивания паспортов изделий."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.models import GenerationLog
from app.schemas import PassportGenerateRequest, PassportGenerateResponse
from app.services.exceptions import (
    IncompleteParametersError,
    PassportRenderError,
    ProductNotFoundError,
    TemplateNotFoundError,
)
from app.services.passport_service import PassportService

router = APIRouter(prefix="/passports", tags=["Passports"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/generate",
    response_model=PassportGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Сгенерировать паспорт изделия по шаблону DOCX",
)
async def generate_passport(
    payload: PassportGenerateRequest,
    session: SessionDep,  # type: ignore
):
    """Генерация паспорта изделия с проверкой 3 бизнес-правил:

    - 422: если у изделия не заполнены обязательные параметры (Правило 1)
    - 200: успешная генерация или возврат существующего файла (reused: true, Правило 2)
    - 500: если поврежден шаблон или произошла системная ошибка (Правило 3)
    """
    service = PassportService(session)
    try:
        log_entry, reused = await service.generate_passport(
            product_id=payload.product_id,
            template_id=payload.template_id,
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncompleteParametersError as e:
        # Бизнес-правило 1: возвращаем 422 и структурированный список недостающих параметров
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Невозможно сформировать паспорт: отсутствуют обязательные параметры",
                "missing_parameters": e.missing_parameters,
            },
        )
    except PassportRenderError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    message = (
        "Паспорт успешно возвращен из кэша (дедупликация 10 мин)"
        if reused
        else "Паспорт изделия успешно сгенерирован"
    )

    return PassportGenerateResponse(
        log_id=log_entry.id,
        product_id=log_entry.product_id,
        template_id=log_entry.template_id,
        status=log_entry.status,
        output_filename=log_entry.output_filename,
        download_url=f"/api/v1/passports/{log_entry.id}/download",
        reused=reused,
        message=message,
    )


@router.get(
    "/{log_id}/download",
    summary="Скачать сгенерированный паспорт в формате .docx",
)
async def download_passport(log_id: int, session: SessionDep):  # type: ignore
    """Скачивание готового файла паспорта по ID записи аудита."""
    log = await session.get(GenerationLog, log_id)
    if not log or log.status != "success" or not log.output_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл паспорта не найден или генерация завершилась с ошибкой",
        )

    file_path = settings.GENERATED_DIR / log.output_filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Файл '{log.output_filename}' отсутствует на сервере",
        )

    return FileResponse(
        path=file_path,
        filename=log.output_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
