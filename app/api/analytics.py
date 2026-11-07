"""API-эндпоинты аналитики и агрегированной статистики по генерациям."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import GenerationLog, Product, Template
from app.schemas import AnalyticsOverview, PopularProductStat, TemplateStat

router = APIRouter(prefix="/analytics", tags=["Analytics"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Общая сводка по генерациям паспортов",
)
async def get_analytics_overview(session: SessionDep):  # type: ignore
    """Возвращает общее число генераций, количество успехов, ошибок и процент успешности."""
    query = select(
        func.count(GenerationLog.id).label("total"),
        func.count().filter(GenerationLog.status == "success").label("success"),
        func.count().filter(GenerationLog.status == "failed").label("failed"),
    )
    result = (await session.execute(query)).one()
    total = result.total or 0
    success = result.success or 0
    failed = result.failed or 0

    rate = round((success / total * 100), 1) if total > 0 else 0.0

    return AnalyticsOverview(
        total_generations=total,
        success_count=success,
        failed_count=failed,
        success_rate_percent=rate,
    )


@router.get(
    "/popular-products",
    response_model=list[PopularProductStat],
    summary="Топ изделий по количеству сгенерированных паспортов",
)
async def get_popular_products(
    session: SessionDep,  # type: ignore
    limit: Annotated[int, Query(ge=1, le=50, description="Количество изделий в топе")] = 5,
):
    """Рейтинг самых востребованных изделий через GROUP BY + COUNT + JOIN."""
    query = (
        select(
            Product.id.label("product_id"),
            Product.sku,
            Product.name,
            func.count(GenerationLog.id).label("generation_count"),
        )
        .join(GenerationLog, GenerationLog.product_id == Product.id)
        .where(GenerationLog.status == "success")
        .group_by(Product.id, Product.sku, Product.name)
        .order_by(desc("generation_count"))
        .limit(limit)
    )

    rows = (await session.execute(query)).all()
    return [
        PopularProductStat(
            product_id=row.product_id,
            sku=row.sku,
            name=row.name,
            generation_count=row.generation_count,
        )
        for row in rows
    ]


@router.get(
    "/template-stats",
    response_model=list[TemplateStat],
    summary="Статистика популярности и надежности шаблонов",
)
async def get_template_stats(session: SessionDep):  # type: ignore
    """Сводка по шаблонам DOCX: сколько раз запускались, сколько успешно, сколько с ошибками."""
    query = (
        select(
            Template.id.label("template_id"),
            Template.name.label("template_name"),
            func.count(GenerationLog.id).label("total_runs"),
            func.count().filter(GenerationLog.status == "success").label("success_runs"),
            func.count().filter(GenerationLog.status == "failed").label("failed_runs"),
        )
        .outerjoin(GenerationLog, GenerationLog.template_id == Template.id)
        .group_by(Template.id, Template.name)
        .order_by(desc("total_runs"))
    )

    rows = (await session.execute(query)).all()
    return [
        TemplateStat(
            template_id=row.template_id,
            template_name=row.template_name,
            total_runs=row.total_runs,
            success_runs=row.success_runs,
            failed_runs=row.failed_runs,
        )
        for row in rows
    ]
