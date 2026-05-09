import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date as SqlDate
from jinja2 import Environment, FileSystemLoader

from app.models.event import Event, EventAggregate
from app.models.rule import Rule, RuleHit
from app.models.camera import Camera
from app.models.room import StorageRoom
from app.models.report import Report


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
REPORT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "reports"
)
os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)


class ReportService:

    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=True,
        )

    async def generate_report(
        self, db: AsyncSession, start_date: date, end_date: date, report_type: str
    ) -> Report:
        report = Report(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            status="generating",
        )
        db.add(report)
        await db.flush()
        try:
            report_data = await self._aggregate_stats(db, start_date, end_date)
            html_content = self._render_html(report_data, start_date, end_date, report_type)
            html_filename = "report_{}_{}_{}_{}.html".format(report.id, report_type, start_date, end_date)
            html_path = os.path.join(REPORT_OUTPUT_DIR, html_filename)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            report.data = report_data
            report.html_path = html_path
            report.status = "completed"
            await db.commit()
            await db.refresh(report)
            return report
        except Exception as e:
            report.status = "failed"
            report.data = {"error": str(e)}
            await db.commit()
            await db.refresh(report)
            raise

    async def _aggregate_stats(self, db: AsyncSession, start_date: date, end_date: date) -> dict:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        q = select(func.count()).select_from(Event).where(
            and_(Event.event_time >= start_dt, Event.event_time <= end_dt)
        )
        total_events = (await db.execute(q)).scalar() or 0

        q = select(func.count(func.distinct(RuleHit.event_id))).select_from(RuleHit).where(
            and_(RuleHit.hit_time >= start_dt, RuleHit.hit_time <= end_dt)
        )
        violation_events = (await db.execute(q)).scalar() or 0

        q = (
            select(Rule.name, Rule.code, func.count(RuleHit.id).label("hit_count"))
            .join(RuleHit, RuleHit.rule_id == Rule.id)
            .where(and_(RuleHit.hit_time >= start_dt, RuleHit.hit_time <= end_dt))
            .group_by(Rule.id, Rule.name, Rule.code)
            .order_by(func.count(RuleHit.id).desc())
        )
        rule_hits_rows = (await db.execute(q)).all()
        rule_hit_stats = [
            {"name": r.name, "code": r.code, "hit_count": r.hit_count}
            for r in rule_hits_rows
        ]

        q = (
            select(
                StorageRoom.id, StorageRoom.name,
                func.max(EventAggregate.risk_level).label("max_risk"),
                func.count(EventAggregate.id).label("aggregate_count"),
            )
            .outerjoin(EventAggregate, and_(
                EventAggregate.room_id == StorageRoom.id,
                EventAggregate.session_start >= start_dt,
                EventAggregate.session_end <= end_dt,
            ))
            .group_by(StorageRoom.id, StorageRoom.name)
        )
        room_risk_rows = (await db.execute(q)).all()
        room_risk_distribution = [
            {"room_id": r.id, "room_name": r.name, "max_risk": r.max_risk or 0, "aggregate_count": r.aggregate_count}
            for r in room_risk_rows
        ]

        risk_summary = {"normal": 0, "low": 0, "medium": 0, "high": 0}
        for room in room_risk_distribution:
            level = room["max_risk"]
            if level == 0:
                risk_summary["normal"] += 1
            elif level == 1:
                risk_summary["low"] += 1
            elif level == 2:
                risk_summary["medium"] += 1
            else:
                risk_summary["high"] += 1

        total_cameras = (await db.execute(select(func.count()).select_from(Camera))).scalar() or 0
        online_cameras = (await db.execute(
            select(func.count()).select_from(Camera).where(Camera.status == 1)
        )).scalar() or 0
        camera_online_rate = round(online_cameras / total_cameras * 100, 1) if total_cameras > 0 else 0.0

        q = (
            select(cast(Event.event_time, SqlDate).label("day"), func.count().label("count"))
            .where(and_(Event.event_time >= start_dt, Event.event_time <= end_dt))
            .group_by(cast(Event.event_time, SqlDate))
            .order_by(cast(Event.event_time, SqlDate))
        )
        daily_rows = (await db.execute(q)).all()
        day_map = {str(r.day): r.count for r in daily_rows}
        daily_trend = []
        current = start_date
        while current <= end_date:
            daily_trend.append({"date": str(current), "count": day_map.get(str(current), 0)})
            current += timedelta(days=1)

        compliance_rate = round((1 - violation_events / total_events) * 100, 1) if total_events > 0 else 100.0

        return {
            "total_events": total_events,
            "violation_events": violation_events,
            "compliance_rate": compliance_rate,
            "rule_hit_stats": rule_hit_stats,
            "room_risk_distribution": room_risk_distribution,
            "risk_summary": risk_summary,
            "camera_online_rate": camera_online_rate,
            "total_cameras": total_cameras,
            "online_cameras": online_cameras,
            "daily_trend": daily_trend,
        }

    def _render_html(self, data: dict, start_date: date, end_date: date, report_type: str) -> str:
        type_labels = {"weekly": "\u5468\u62a5", "monthly": "\u6708\u62a5", "quarterly": "\u5b63\u62a5"}
        template = self.jinja_env.get_template("report.html")
        label = type_labels.get(report_type, "\u62a5\u544a")
        title = "\u535a\u7269\u9986\u5b89\u9632\u5408\u89c4" + label
        return template.render(
            title=title,
            report_type=report_type,
            report_type_label=label,
            start_date=str(start_date),
            end_date=str(end_date),
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            **data,
        )

    async def list_reports(self, db: AsyncSession, page: int = 1, size: int = 20):
        query = select(Report).order_by(Report.generated_at.desc())
        total_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_q)).scalar() or 0
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        items = result.scalars().all()
        return items, total

    async def get_report(self, db: AsyncSession, report_id: int) -> Optional[Report]:
        result = await db.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()


report_service = ReportService()
