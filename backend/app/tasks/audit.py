from datetime import datetime, timedelta
from langchain_deepseek import ChatDeepSeek
from app.core.config import settings
from app.core.database import async_session
from app.core.utils import cst_now
from app.models.ai_log import AuditReport
from app.models.work_order import WorkOrder
from app.models.chat import ChatMessage

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
)


async def generate_audit_report() -> dict:
    """凌晨审计 Agent：采集 24h 数据 → LLM Reflection → INSERT audit_reports"""
    try:
        async with async_session() as db:
            from sqlmodel import select, func

            yesterday = cst_now().date() - timedelta(days=1)
            yesterday_str = str(yesterday)

            # 日期去重：如果当天已有报告，直接返回
            existing = await db.execute(
                select(AuditReport).where(AuditReport.date == yesterday_str).limit(1)
            )
            existing_report = existing.scalar_one_or_none()
            if existing_report:
                # 清理重复报告：保留最新一条，删除其余
                all_existing = await db.execute(
                    select(AuditReport).where(AuditReport.date == yesterday_str).order_by(AuditReport.generated_at.desc())
                )
                all_reports = all_existing.scalars().all()
                if len(all_reports) > 1:
                    for dup in all_reports[1:]:
                        await db.delete(dup)
                    await db.commit()
                return {
                    "report_id": str(existing_report.id),
                    "date": yesterday_str,
                    "anomalies_count": len(existing_report.anomalies) if existing_report.anomalies else 0,
                    "skipped": True,
                }

            yesterday_start = cst_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            yesterday_end = yesterday_start + timedelta(days=1)

            # 工单耗时统计
            result = await db.execute(
                select(WorkOrder).where(
                    WorkOrder.created_at >= yesterday_start,
                    WorkOrder.created_at < yesterday_end,
                )
            )
            orders = result.scalars().all()

            # 按指派人员统计超时
            staff_stats = {}
            total_orders = len(orders)
            for wo in orders:
                if wo.assigned_resource:
                    if wo.assigned_resource not in staff_stats:
                        staff_stats[wo.assigned_resource] = {"total": 0, "completed": 0}
                    staff_stats[wo.assigned_resource]["total"] += 1
                    if wo.status == "completed":
                        staff_stats[wo.assigned_resource]["completed"] += 1

            # 客诉文本采集
            result = await db.execute(
                select(ChatMessage).where(
                    ChatMessage.role == "user",
                    ChatMessage.created_at >= yesterday_start,
                    ChatMessage.created_at < yesterday_end,
                ).limit(50)
            )
            user_messages = result.scalars().all()
            chat_texts = [m.content for m in user_messages if "投诉" in m.content or "不满" in m.content or "坏" in m.content or "修" in m.content or "慢" in m.content]

            # LLM Reflection 生成报告
            staff_summary = "\n".join([
                f"  - {name}: 总工单 {info['total']} 单，完成 {info['completed']} 单"
                for name, info in staff_stats.items()
            ]) or "无可统计的工单数据"

            chats = "\n".join([f"  · {t[:200]}" for t in chat_texts[:10]]) or "无客诉文本"

            prompt = (
                f"你是酒店运营审计专家，请根据以下过去24小时数据生成结构化报告（仅输出JSON）：\n\n"
                f"【日期】{yesterday}\n"
                f"【工单总量】{total_orders}\n"
                f"【人员统计】\n{staff_summary}\n"
                f"【客诉文本】\n{chats}\n\n"
                f'输出JSON格式：{{"summary": "总结", "anomalies": [{{"staff": "姓名", "overtime_count": N, "issue": "描述"}}], "recommendations": "建议"}}'
            )

            try:
                resp = await llm.ainvoke(prompt)
                text = resp.content.strip()
            except Exception as e:
                raise RuntimeError(f"DeepSeek API 调用失败: {type(e).__name__}: {str(e)}")

            import json
            try:
                parsed = json.loads(text.replace("```json", "").replace("```", "").strip())
            except json.JSONDecodeError:
                parsed = {"summary": text[:200], "anomalies": [], "recommendations": ""}

            report = AuditReport(
                date=yesterday_str,
                content={"summary": parsed.get("summary", "")},
                anomalies=parsed.get("anomalies", []),
                generated_at=cst_now(),
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)

            return {
                "report_id": str(report.id),
                "date": yesterday_str,
                "anomalies_count": len(parsed.get("anomalies", [])),
                "skipped": False,
            }
    except Exception as e:
        raise RuntimeError(f"审计报告生成失败: {type(e).__name__}: {str(e)}")
