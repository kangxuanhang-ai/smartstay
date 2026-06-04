# 房费多日计算与营收统计优化实施计划
> **For agentic workers:** 使用 superpowers:executing-plans 逐 task 实施。Steps 使用 checkbox (- [ ]) 跟踪进度。

**Goal:** 修复账单房费不随天数增长的 bug，修正店长大盘今日统计算法
**Architecture:** 后端纯改动，前端无需修改（字段名不变，值变正确）
**Tech Stack:** Python/FastAPI, SQLAlchemy, Pydantic

---

## 文件结构

### 修改文件
| 文件 | Task | 改动说明 |
|------|------|---------|
| ackend/app/core/utils.py | 1 | 新增 calculate_nights 通用函数 |
| ackend/app/schemas/order.py | 2 | BillResponse 新增 nights + daily_rate 字段 |
| ackend/app/api/orders.py | 3+4 | 账单动态计算（不改 total_amount） |
| ackend/app/api/admin.py | 5 | 大盘今日流水用 Room.base_price |

### 不改文件
- ackend/app/models/order.py — 不加字段，不改 total_amount 语义
- ackend/app/api/orders.py checkout — 不改 total_amount
- 前端所有文件 — 字段名不变

---

## Task 1: 新增 calculate_nights 通用函数
**文件:** ackend/app/core/utils.py

**改动:** 在文件末尾新增：

`python
from math import ceil

def calculate_nights(check_in_time, check_out_time=None):
    """计算住夜晚数。酒店惯例：入住当天算1晚。"""
    end = check_out_time or cst_now()
    delta = end - check_in_time
    seconds = delta.total_seconds()
    if seconds <= 0:
        return 1
    return max(1, ceil(seconds / 86400))
`

**验证:** py_compile app/core/utils.py 通过

---

## Task 2: BillResponse schema 新增字段
**文件:** ackend/app/schemas/order.py

**改动:**
1. BillResponse 新增两个字段（有默认值，向后兼容）：
   `python
   nights: int = 1
   daily_rate: int = 0  # 单日房价（分）
   `
2. 
oom_rate 字段保留，语义变为"房费小计（多日累计）"

**验证:** py_compile app/schemas/order.py 通过

---

## Task 3: 账单接口动态计算
**文件:** ackend/app/api/orders.py

**改动 1: get_bill_total 函数**
`python
async def get_bill_total(db: AsyncSession, order_id: uuid.UUID) -> int:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return 0
    nights = calculate_nights(order.check_in_time, order.check_out_time)
    room_total = order.total_amount * nights
    cons_result = await db.execute(select(Consumption).where(Consumption.order_id == order_id))
    consumptions = cons_result.scalars().all()
    consumption_total = sum(c.amount * c.quantity for c in consumptions)
    return room_total + consumption_total
`

**改动 2: get_bill 接口**
在 return BillResponse 之前：
`python
nights = calculate_nights(order.check_in_time, order.check_out_time)
daily_rate = order.total_amount
room_total = daily_rate * nights
`

然后 return：
`python
return BillResponse(
    order_id=str(order.id),
    room_rate=room_total,        # 多日累计房费
    daily_rate=daily_rate,       # 单日房价
    nights=nights,               # 住夜晚数
    consumptions=lines,
    consumption_total=consumption_total,
    grand_total=room_total + consumption_total,
    deposit_rate=1.0,
)
`

**注意:** 	otal_amount 永远不改，始终是单日房价。退房后也不覆盖。

**验证:** py_compile app/api/orders.py 通过

---

## Task 4: checkout 接口不改
**文件:** ackend/app/api/orders.py

**确认:** checkout 接口保持不变。	otal_amount 始终是单日房价，退房只改 status 和 check_out_time。无需任何代码改动。

---

## Task 5: 大盘今日流水修正
**文件:** ackend/app/api/admin.py

**改动 1: get_dashboard**

替换原来的"只看今天 check_in"逻辑，改为"遍历所有订单判断今天是否在住"：

`python
@router.get("/dashboard")
async def get_dashboard(
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sa_func

    result = await db.execute(select(Room))
    rooms = result.scalars().all()
    total_rooms = len(rooms)
    room_prices = {str(r.id): r.base_price for r in rooms}

    today = cst_now().date()

    # 查所有可能今天在住的订单
    result = await db.execute(
        select(Order).where(Order.check_in_time.isnot(None))
    )
    all_orders = result.scalars().all()

    occupied_rooms = set()
    today_revenue = 0
    today_orders = 0

    for o in all_orders:
        checkin_date = o.check_in_time.date()
        checkout_date = o.check_out_time.date() if o.check_out_time else None

        # 今天是否在住：入住日 <= 今天 AND (未退房 OR 退房日 >= 今天)
        is_staying_today = (checkin_date <= today) and (checkout_date is None or checkout_date >= today)

        if is_staying_today:
            occupied_rooms.add(str(o.room_id))
            today_revenue += room_prices.get(str(o.room_id), o.total_amount)
            today_orders += 1

    occupied = len(occupied_rooms)
    revpar = today_revenue // total_rooms if total_rooms > 0 else 0

    return {
        "occupancy": round(occupied / total_rooms * 100) if total_rooms > 0 else 0,
        "occupied": occupied,
        "total_rooms": total_rooms,
        "revpar": revpar,
        "revenue": today_revenue,
        "today_orders": today_orders,
    }
`

**改动 2: hourly-revenue — 统一用 Room.base_price**
- 预加载 `room_prices`（与 dashboard 一致）
- 新入住按入住时间统计：`hourly_trend[idx] += room_prices[room_id] // 100`
- 续住房不拆到小时维度，体现在今日流水总数里
- 数据源统一为 `Room.base_price`，与 dashboard 保持一致
**验证:** py_compile app/api/admin.py 通过

---

## Task 6: 最终验证
**验证步骤:**
1. cd backend && poetry run python -m py_compile app/main.py
2. 手动测试账单：
   - 入住 501（¥720/晚），2天后查账单 → room_rate=1440, nights=2, daily_rate=720
   - 退房后查账单 → 同上（total_amount未变，bill动态算）
3. 手动测试大盘：
   - 昨天入住的订单今天还在住 → 今日流水包含该房间的 base_price
   - 今天新入住 → 今日流水包含该房间的 base_price
   - 小时走势只统计新入住
4. B端前端无需改动

---

## 假设与默认值

1. 酒店行业惯例：入住当天算 1 晚
2. 	otal_amount 永远 = 单日房价（分），退房后也不改
3. 今日流水 = 今天所有在住房间的 Room.base_price 之和
4. 小时走势：只统计新入住，续住房不拆到小时
5. 不涉及数据库迁移，Order 模型字段不变
6. C 端和 B 端前端无需改动
