from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.report_service import report_service
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["合规报告"])


@router.get("/generate")
async def generate_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    report_type: str = Query(..., regex="^(weekly|monthly|quarterly)$"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    if start_date > end_date:
        return fail("开始日期不能晚于结束日期")
    try:
        report = await report_service.generate_report(db, start_date, end_date, report_type)
        return ok(data={
            "id": report.id,
            "report_type": report.report_type,
            "start_date": str(report.start_date),
            "end_date": str(report.end_date),
            "generated_at": str(report.generated_at),
            "status": report.status,
            "data": report.data,
        })
    except Exception as e:
        return fail(str(e))


@router.get("/list")
async def list_reports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    items, total = await report_service.list_reports(db, page, size)
    result = [
        {
            "id": r.id,
            "report_type": r.report_type,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "generated_at": str(r.generated_at),
            "status": r.status,
        }
        for r in items
    ]
    return ok(data=PageResult(items=result, total=total, page=page, size=size))


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    report = await report_service.get_report(db, report_id)
    if not report:
        return fail("报告不存在", 404)
    if report.status != "completed" or not report.html_path:
        return fail("报告尚未生成完成")
    import os
    if not os.path.exists(report.html_path):
        return fail("报告文件不存在")
    filename = "report_{}_{}.html".format(report.report_type, report.start_date)
    return FileResponse(
        report.html_path,
        media_type="text/html",
        filename=filename,
    )
