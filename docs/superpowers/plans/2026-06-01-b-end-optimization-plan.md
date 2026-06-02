# B 端全面优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete all stubbed B-end features, fix code quality issues, and add checkout settlement flow with Alipay sandbox integration.

**Architecture:** Backend adds 6 new admin/order endpoints following existing patterns (SQLModel + asyncpg + require_role). Frontend implements Modals/Drawers following Ant Design patterns already in use. Alipay sandbox integration uses server-side SDK with async callback.

**Tech Stack:** React 19, Ant Design 6, TypeScript 6, FastAPI, SQLModel, PostgreSQL, jsPDF, alipay-sdk

---

## Phase 1: Backend Admin Endpoints

### Task 1: Staff model `is_active` field + UserUpdate schema

**Files:**
- Modify: `backend/app/models/user.py` — add `is_active` field to Staff
- Modify: `backend/app/schemas/admin.py` — add `UserUpdate` schema

- [ ] **Step 1: Add `is_active` to Staff model**

In `backend/app/models/user.py`, add `is_active: bool = Field(default=True)` to the `Staff` class, after the `is_first_login` field:

```python
is_active: bool = Field(default=True)
```

- [ ] **Step 2: Add UserUpdate schema**

In `backend/app/schemas/admin.py`, add after the existing `UserCreate` class:

```python
class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
```

- [ ] **Step 3: Verify backend compiles**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/user.py backend/app/schemas/admin.py
git commit -m "feat: add Staff.is_active field and UserUpdate schema"
```

---

### Task 2: Staff edit + toggle-status endpoints

**Files:**
- Modify: `backend/app/api/admin.py` — add 2 new endpoints

- [ ] **Step 1: Add PUT /api/admin/users/{user_id} endpoint**

In `backend/app/api/admin.py`, add after the existing `create_user` endpoint. Import `UserUpdate` from `app.schemas.admin` at the top of the file if not already imported:

```python
@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Staff).where(Staff.id == uuid.UUID(user_id)))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    if body.name is not None:
        staff.name = body.name
    if body.phone is not None:
        staff.phone = body.phone
    if body.role is not None:
        staff.role = body.role
    await db.commit()
    return {"message": "更新成功", "id": str(staff.id)}
```

- [ ] **Step 2: Add PUT /api/admin/users/{user_id}/toggle-status endpoint**

Add immediately after the endpoint above:

```python
@router.put("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Staff).where(Staff.id == uuid.UUID(user_id)))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    staff.is_active = not staff.is_active
    await db.commit()
    status = "启用" if staff.is_active else "禁用"
    return {"message": f"已{status}", "is_active": staff.is_active}
```

- [ ] **Step 3: Verify backend compiles**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/admin.py
git commit -m "feat: add staff edit and toggle-status admin endpoints"
```

---

### Task 3: Guest edit + reset-password endpoints

**Files:**
- Modify: `backend/app/api/admin.py` — add 2 new guest endpoints

- [ ] **Step 1: Add PUT /api/admin/guests/{guest_id} endpoint**

In `backend/app/api/admin.py`, add after the staff endpoints:

```python
@router.put("/guests/{guest_id}")
async def update_guest(
    guest_id: str,
    body: UserUpdate,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Guest).where(Guest.id == uuid.UUID(guest_id)))
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="住客不存在")
    if body.name is not None:
        guest.name = body.name
    if body.phone is not None:
        guest.phone = body.phone
    await db.commit()
    return {"message": "更新成功", "id": str(guest.id)}
```

- [ ] **Step 2: Add PUT /api/admin/guests/{guest_id}/reset-password endpoint**

```python
@router.put("/guests/{guest_id}/reset-password")
async def reset_guest_password(
    guest_id: str,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Guest).where(Guest.id == uuid.UUID(guest_id)))
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="住客不存在")
    guest.hashed_password = get_password_hash("123456")
    guest.is_first_login = True
    await db.commit()
    return {"message": "密码已重置为 123456"}
```

Make sure `get_password_hash` is imported at the top of `admin.py`:
```python
from app.core.security import get_password_hash
```

- [ ] **Step 3: Verify backend compiles**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/admin.py
git commit -m "feat: add guest edit and reset-password admin endpoints"
```

---

## Phase 2: Frontend User Management

### Task 4: Staff edit + disable/enable in UserManagementPage

**Files:**
- Modify: `frontend/src/pages/manager/UserManagementPage.tsx`

- [ ] **Step 1: Add imports and state for edit modal**

Ensure `Modal`, `Select`, and `Space` are imported from `antd` at the top of the file.

Add state variables after the existing `createOpen` state (around line 19):

```tsx
const [editOpen, setEditOpen] = useState(false)
const [editRecord, setEditRecord] = useState<any>(null)
const [editForm] = Form.useForm()
```

- [ ] **Step 2: Add edit handler function**

Add after the existing `handleCreateUser` function:

```tsx
const handleEditUser = async () => {
  try {
    const values = await editForm.validateFields()
    await apiClient.put(`/api/admin/users/${editRecord.id}`, values)
    message.success('更新成功')
    setEditOpen(false)
    editForm.resetFields()
    fetchStaff()
  } catch {
    message.error('更新失败')
  }
}

const handleToggleStatus = async (record: any) => {
  const action = record.is_active === false ? '启用' : '禁用'
  Modal.confirm({
    title: `确认${action}`,
    content: `确定要${action}该员工吗？`,
    onOk: async () => {
      try {
        await apiClient.put(`/api/admin/users/${record.id}/toggle-status`)
        message.success(`已${action}`)
        fetchStaff()
      } catch {
        message.error(`${action}失败`)
      }
    },
  })
}
```

Note: `fetchStaff` is the function that refreshes the staff list. If the current code uses inline fetching in `useEffect`, extract it into a named function first.

- [ ] **Step 3: Update the actions column render**

Replace the stubbed render function (line 60) to accept the record parameter and wire up real handlers:

```tsx
{
  title: '操作', key: 'actions', width: 140,
  render: (_: unknown, record: any) => (
    <Space>
      <Button type="link" size="small" onClick={() => {
        setEditRecord(record)
        editForm.setFieldsValue({ name: record.name, phone: record.phone, role: record.role })
        setEditOpen(true)
      }}>编辑</Button>
      <Button type="link" size="small" danger={record.is_active !== false}
        onClick={() => handleToggleStatus(record)}>
        {record.is_active === false ? '启用' : '禁用'}
      </Button>
    </Space>
  ),
},
```

- [ ] **Step 4: Add is_active display in status column**

Update the status column to show disabled state. Find the existing status column render and update:

```tsx
{
  title: '状态', key: 'status', width: 120,
  render: (_: unknown, record: any) => {
    if (record.is_active === false) return <Tag color="red">已禁用</Tag>
    return record.is_first_login ? <Tag color="orange">首次登录</Tag> : <Tag color="green">正常</Tag>
  },
},
```

- [ ] **Step 5: Add edit Modal JSX**

Add after the existing create Modal (around line 111):

```tsx
<Modal
  title="编辑员工"
  open={editOpen}
  onOk={handleEditUser}
  onCancel={() => { setEditOpen(false); editForm.resetFields() }}
>
  <Form form={editForm} layout="vertical">
    <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    <Form.Item name="phone" label="手机号">
      <Input />
    </Form.Item>
    <Form.Item name="role" label="角色" rules={[{ required: true }]}>
      <Select>
        <Select.Option value="front_desk">前台</Select.Option>
        <Select.Option value="manager">经理</Select.Option>
        <Select.Option value="admin">管理员</Select.Option>
      </Select>
    </Form.Item>
  </Form>
</Modal>
```

Make sure `Select` is imported from `antd`.

- [ ] **Step 6: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/manager/UserManagementPage.tsx
git commit -m "feat: implement staff edit and disable/enable in UserManagementPage"
```

---

### Task 5: Guest edit + reset password in UserManagementPage

**Files:**
- Modify: `frontend/src/pages/manager/UserManagementPage.tsx`

- [ ] **Step 1: Add guest edit state and handler**

Add state variables:

```tsx
const [guestEditOpen, setGuestEditOpen] = useState(false)
const [guestEditRecord, setGuestEditRecord] = useState<any>(null)
const [guestEditForm] = Form.useForm()
```

Add handler:

```tsx
const handleEditGuest = async () => {
  try {
    const values = await guestEditForm.validateFields()
    await apiClient.put(`/api/admin/guests/${guestEditRecord.id}`, values)
    message.success('更新成功')
    setGuestEditOpen(false)
    guestEditForm.resetFields()
    fetchGuests()
  } catch {
    message.error('更新失败')
  }
}

const handleResetGuestPassword = async (record: any) => {
  Modal.confirm({
    title: '确认重置密码',
    content: `确定要重置 ${record.name} 的密码为 123456 吗？`,
    onOk: async () => {
      try {
        await apiClient.put(`/api/admin/guests/${record.id}/reset-password`)
        message.success('密码已重置为 123456')
      } catch {
        message.error('重置失败')
      }
    },
  })
}
```

Note: `fetchGuests` is the function that refreshes the guest list. If the current code uses inline fetching, extract it into a named function.

- [ ] **Step 2: Update guestColumns to include actions**

Replace line 69 (`const guestColumns = columns.filter((c) => c.key !== 'actions')`) with:

```tsx
const guestColumns = [
  ...columns.filter((c) => c.key !== 'actions'),
  {
    title: '操作', key: 'actions', width: 180,
    render: (_: unknown, record: any) => (
      <Space>
        <Button type="link" size="small" onClick={() => {
          setGuestEditRecord(record)
          guestEditForm.setFieldsValue({ name: record.name, phone: record.phone })
          setGuestEditOpen(true)
        }}>编辑</Button>
        <Button type="link" size="small" onClick={() => handleResetGuestPassword(record)}>
          重置密码
        </Button>
      </Space>
    ),
  },
]
```

- [ ] **Step 3: Add guest edit Modal JSX**

Add after the staff edit Modal:

```tsx
<Modal
  title="编辑住客"
  open={guestEditOpen}
  onOk={handleEditGuest}
  onCancel={() => { setGuestEditOpen(false); guestEditForm.resetFields() }}
>
  <Form form={guestEditForm} layout="vertical">
    <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    <Form.Item name="phone" label="手机号">
      <Input />
    </Form.Item>
  </Form>
</Modal>
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/manager/UserManagementPage.tsx
git commit -m "feat: implement guest edit and reset password in UserManagementPage"
```

---

## Phase 3: Invoice Features

### Task 6: Invoice detail drawer + PDF export

**Files:**
- Modify: `frontend/src/pages/manager/InvoiceManagementPage.tsx`

- [ ] **Step 1: Install jsPDF**

Run: `cd frontend && npm install jspdf`
Expected: Added to dependencies in package.json

- [ ] **Step 2: Add state and imports**

Add at the top of the file, after existing imports:

```tsx
import { Drawer } from 'antd'
import jsPDF from 'jspdf'
```

Add state variables inside the component:

```tsx
const [drawerOpen, setDrawerOpen] = useState(false)
const [drawerRecord, setDrawerRecord] = useState<any>(null)
```

- [ ] **Step 3: Add PDF export function**

```tsx
const handleExportPDF = (record: any) => {
  const doc = new jsPDF()
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(18)
  doc.text('Invoice / Fapiao', 20, 20)
  doc.setFontSize(12)
  doc.text(`Order ID: ${record.order_id || record.id}`, 20, 40)
  doc.text(`Company: ${record.company_name || '-'}`, 20, 50)
  doc.text(`Tax ID: ${record.tax_id || '-'}`, 20, 60)
  doc.text(`Email: ${record.email || '-'}`, 20, 70)
  doc.text(`Status: ${record.status}`, 20, 80)
  doc.text(`Date: ${new Date().toLocaleDateString()}`, 20, 90)
  doc.save(`invoice-${record.id}.pdf`)
}
```

- [ ] **Step 4: Update the actions column render**

Replace the stubbed buttons (lines 57-66) with:

```tsx
{
  title: '操作', key: 'actions', width: 200,
  render: (_: unknown, record: any) => (
    <Space>
      <Button type="link" size="small" onClick={() => {
        setDrawerRecord(record)
        setDrawerOpen(true)
      }}>查看</Button>
      {record.status === 'issued' && (
        <Button type="link" size="small" style={{ color: '#52c41a' }}
          onClick={() => handleExportPDF(record)}>
          导出PDF
        </Button>
      )}
      {record.status === 'draft' && (
        <Button type="link" size="small"
          onClick={() => handleMarkIssued(record.id)}>
          标记已开具
        </Button>
      )}
    </Space>
  ),
},
```

- [ ] **Step 5: Add Drawer JSX**

Add before the closing `</div>` of the component:

```tsx
<Drawer
  title="发票详情"
  open={drawerOpen}
  onClose={() => setDrawerOpen(false)}
  width={400}
>
  {drawerRecord && (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div><strong>订单号：</strong>{drawerRecord.order_id || drawerRecord.id}</div>
      <div><strong>公司名称：</strong>{drawerRecord.company_name || '-'}</div>
      <div><strong>税号：</strong>{drawerRecord.tax_id || '-'}</div>
      <div><strong>邮箱：</strong>{drawerRecord.email || '-'}</div>
      <div><strong>地址：</strong>{drawerRecord.address || '-'}</div>
      <div><strong>状态：</strong>{drawerRecord.status === 'issued' ? '已开具' : '草稿'}</div>
    </div>
  )}
</Drawer>
```

- [ ] **Step 6: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/manager/InvoiceManagementPage.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: implement invoice detail drawer and PDF export"
```

---

## Phase 4: Code Quality Fixes

### Task 7: Fix silent error handling across 7 files

**Files:**
- Modify: `frontend/src/pages/manager/DashboardPage.tsx`
- Modify: `frontend/src/pages/manager/InvoiceManagementPage.tsx`
- Modify: `frontend/src/pages/manager/UserManagementPage.tsx`
- Modify: `frontend/src/pages/manager/AIAuditPage.tsx`
- Modify: `frontend/src/pages/admin/AdminPage.tsx`
- Modify: `frontend/src/pages/front-desk/WorkOrderBoard.tsx`
- Modify: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Fix DashboardPage.tsx**

Replace each `.catch(() => {})` with a descriptive `.catch(() => message.error('...'))`:

```tsx
// line ~32: dashboard data
.catch(() => message.error('获取仪表盘数据失败'))

// line ~35: channel stats
.catch(() => message.error('获取渠道数据失败'))

// line ~38: hourly revenue
.catch(() => message.error('获取收入数据失败'))
```

Make sure `message` is imported from `antd`.

- [ ] **Step 2: Fix InvoiceManagementPage.tsx**

```tsx
// line ~35: fetch invoices
.catch(() => message.error('获取发票列表失败'))
```

- [ ] **Step 3: Fix UserManagementPage.tsx**

```tsx
// line ~38: fetch users
.catch(() => message.error('获取用户列表失败'))
```

- [ ] **Step 4: Fix AIAuditPage.tsx**

```tsx
// line ~30: fetch audit reports
.catch(() => message.error('获取审计报告失败'))
```

- [ ] **Step 5: Fix AdminPage.tsx**

```tsx
// line ~31: fetch safety logs
.catch(() => message.error('获取安全日志失败'))
```

- [ ] **Step 6: Fix WorkOrderBoard.tsx**

```tsx
// line ~35: fetch work orders
.catch(() => message.error('获取工单列表失败'))

// line ~41: fetch staff
.catch(() => message.error('获取员工列表失败'))
```

- [ ] **Step 7: Fix useWebSocket.ts**

Replace the silent catch in the WebSocket message handler (around line 35):

```tsx
} catch {
  console.warn('WebSocket message parse error')
}
```

(Keep as `console.warn` since WebSocket parse errors are expected for non-JSON messages)

- [ ] **Step 8: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/manager/DashboardPage.tsx frontend/src/pages/manager/InvoiceManagementPage.tsx frontend/src/pages/manager/UserManagementPage.tsx frontend/src/pages/manager/AIAuditPage.tsx frontend/src/pages/admin/AdminPage.tsx frontend/src/pages/front-desk/WorkOrderBoard.tsx frontend/src/hooks/useWebSocket.ts
git commit -m "fix: replace silent error catching with user-facing error messages"
```

---

### Task 8: API URL configuration via environment variables

**Files:**
- Create: `frontend/.env`
- Create: `frontend/.env.example`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Create .env file**

Create `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8765
VITE_WS_BASE_URL=ws://localhost:8765
```

- [ ] **Step 2: Create .env.example file**

Create `frontend/.env.example`:

```
VITE_API_BASE_URL=http://localhost:8765
VITE_WS_BASE_URL=ws://localhost:8765
```

- [ ] **Step 3: Update api/client.ts**

Replace the hardcoded baseURL (line 4):

```tsx
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8765',
})
```

Also update the refresh token URL (line 21) to use the same env var:

```tsx
const { data } = await axios.post(
  `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8765'}/api/auth/refresh`,
  { refresh_token: refreshToken },
)
```

- [ ] **Step 4: Update useWebSocket.ts**

Replace line 6:

```tsx
const WS_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8765'
```

- [ ] **Step 5: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/.env frontend/.env.example frontend/src/api/client.ts frontend/src/hooks/useWebSocket.ts
git commit -m "feat: configure API and WebSocket URLs via environment variables"
```

---

### Task 9: Non-occupied room click response

**Files:**
- Modify: `frontend/src/pages/front-desk/RoomGridPage.tsx`

- [ ] **Step 1: Add state for room info modal**

Add state variables in the `RoomGridPage` component:

```tsx
const [infoModalOpen, setInfoModalOpen] = useState(false)
const [infoRoom, setInfoRoom] = useState<Room | null>(null)
```

- [ ] **Step 2: Add click handler for non-occupied rooms**

Find the room card click handler. Currently clicking non-occupied rooms does nothing. Add a click handler that opens the info modal:

In the room card's `onClick` or the wrapping element, add:

```tsx
onClick={() => {
  if (room.status === 'occupied') {
    setSelectedRoom(room)
    setDetailOpen(true)
  } else {
    setInfoRoom(room)
    setInfoModalOpen(true)
  }
}}
```

- [ ] **Step 3: Add room info Modal JSX**

Add before the closing of the component:

```tsx
<Modal
  title="房间信息"
  open={infoModalOpen}
  onCancel={() => setInfoModalOpen(false)}
  footer={[
    infoRoom?.status === 'vacant' && (
      <Button key="checkin" type="primary" onClick={() => {
        setInfoModalOpen(false)
        setCheckinRoom(infoRoom)
        setCheckinOpen(true)
      }}>
        快捷开房
      </Button>
    ),
    <Button key="close" onClick={() => setInfoModalOpen(false)}>关闭</Button>,
  ].filter(Boolean)}
>
  {infoRoom && (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div><strong>房间号：</strong>{infoRoom.room_number}</div>
      <div><strong>房型：</strong>{infoRoom.room_type === 'big_bed' ? '大床房' : infoRoom.room_type === 'twin' ? '双床房' : '套房'}</div>
      <div><strong>状态：</strong>
        <Tag color={infoRoom.status === 'vacant' ? 'green' : infoRoom.status === 'dirty' ? 'gold' : 'default'}>
          {infoRoom.status === 'vacant' ? '空房' : infoRoom.status === 'dirty' ? '脏房' : '维修中'}
        </Tag>
      </div>
      <div><strong>价格：</strong>¥{(infoRoom.current_price / 100).toFixed(2)}/晚</div>
    </div>
  )}
</Modal>
```

Note: `setCheckinRoom` and `setCheckinOpen` are the existing state variables that control the `CheckInModal`. Verify their actual names in the current code.

- [ ] **Step 4: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/front-desk/RoomGridPage.tsx
git commit -m "feat: show room info modal on non-occupied room click"
```

---

## Phase 5: Checkout Settlement Flow

### Task 10: Checkout settlement modal

**Files:**
- Modify: `frontend/src/pages/front-desk/RoomGridPage.tsx` — replace direct checkout with settlement modal

- [ ] **Step 1: Add settlement modal state**

Add state variables in `RoomGridPage`:

```tsx
const [settleOpen, setSettleOpen] = useState(false)
const [settleRoom, setSettleRoom] = useState<Room | null>(null)
const [settleOrder, setSettleOrder] = useState<any>(null)
const [settleBill, setSettleBill] = useState<any>(null)
const [settleLoading, setSettleLoading] = useState(false)
```

- [ ] **Step 2: Create openSettlement function**

```tsx
const openSettlement = async (room: Room) => {
  try {
    const { data: order } = await apiClient.get(`/api/orders/room/${room.id}/active`)
    const { data: bill } = await apiClient.get(`/api/orders/${order.id}/bill`)
    setSettleRoom(room)
    setSettleOrder(order)
    setSettleBill(bill)
    setSettleOpen(true)
  } catch {
    message.error('获取账单失败')
  }
}
```

- [ ] **Step 3: Update RoomDetailModal to use settlement flow**

In the `RoomDetailModal` component, replace the `handleCheckout` function. Instead of calling checkout directly, call the parent's settlement opener:

Change the `onCheckout` prop usage. In `RoomDetailModal`, the "办理退房" button should call:

```tsx
onClick={() => {
  onClose()
  onCheckout(room.id)
}}
```

In `RoomGridPage`, update the `onCheckout` handler passed to `RoomDetailModal`:

```tsx
onCheckout={(roomId) => {
  const room = rooms.find((r: Room) => r.id === roomId)
  if (room) openSettlement(room)
}}
```

- [ ] **Step 4: Update context menu checkout to use settlement**

Replace the context menu "办理退房" handler (around line 329):

```tsx
{ key: 'checkout', label: '办理退房', onClick: () => openSettlement(room) },
```

- [ ] **Step 5: Add settlement Modal JSX**

```tsx
<Modal
  title="退房结算"
  open={settleOpen}
  onCancel={() => setSettleOpen(false)}
  footer={null}
  width={480}
>
  {settleRoom && settleOrder && settleBill && (
    <div>
      <div style={{ marginBottom: 16 }}>
        <div><strong>房间：</strong>{settleRoom.room_number} {settleRoom.room_type === 'big_bed' ? '大床房' : settleRoom.room_type === 'twin' ? '双床房' : '套房'}</div>
        <div><strong>住客：</strong>{settleOrder.guest_name || '-'}</div>
      </div>
      <table style={{ width: '100%', marginBottom: 16, borderCollapse: 'collapse' }}>
        <tbody>
          <tr>
            <td style={{ padding: '8px 0' }}>房费</td>
            <td style={{ textAlign: 'right', padding: '8px 0' }}>¥{(settleBill.room_rate / 100).toFixed(2)}</td>
          </tr>
          {settleBill.consumptions?.map((c: any, i: number) => (
            <tr key={i}>
              <td style={{ padding: '4px 0', color: '#999' }}>{c.item_name}</td>
              <td style={{ textAlign: 'right', padding: '4px 0', color: '#999' }}>¥{(c.amount / 100).toFixed(2)}</td>
            </tr>
          ))}
          <tr style={{ borderTop: '1px solid #333' }}>
            <td style={{ padding: '8px 0', fontWeight: 'bold' }}>合计</td>
            <td style={{ textAlign: 'right', padding: '8px 0', fontWeight: 'bold' }}>¥{(settleBill.grand_total / 100).toFixed(2)}</td>
          </tr>
        </tbody>
      </table>
      <div style={{ display: 'flex', gap: 12 }}>
        <Button
          style={{ flex: 1 }}
          disabled={!['ctrip', 'meituan'].includes(settleOrder.source)}
          loading={settleLoading}
          onClick={async () => {
            setSettleLoading(true)
            await new Promise((r) => setTimeout(r, 2000))
            try {
              await apiClient.put(`/api/orders/${settleOrder.id}/checkout`)
              message.success('退房成功')
              setSettleOpen(false)
              setRefreshKey((k) => k + 1)
            } catch {
              message.error('退房失败')
            } finally {
              setSettleLoading(false)
            }
          }}
        >
          线上支付{['ctrip', 'meituan'].includes(settleOrder.source) ? '' : ' (仅携程/美团)'}
        </Button>
        <Button
          type="primary"
          style={{ flex: 1 }}
          onClick={async () => {
            try {
              const { data } = await apiClient.post(`/api/orders/${settleOrder.id}/create-alipay-order`)
              window.open(data.pay_url, '_blank')
            } catch {
              message.error('创建支付订单失败')
            }
          }}
        >
          立即支付 (线下)
        </Button>
      </div>
    </div>
  )}
</Modal>
```

- [ ] **Step 6: Remove old handleCheckout from RoomGridPage**

Delete the old `handleCheckout` function (lines 277-286) since it's replaced by `openSettlement`.

- [ ] **Step 7: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/front-desk/RoomGridPage.tsx
git commit -m "feat: add checkout settlement modal with payment options"
```

---

### Task 11: Alipay sandbox backend integration

**Files:**
- Modify: `backend/app/core/config.py` — add Alipay settings
- Create: `backend/app/api/alipay.py` — Alipay endpoints
- Modify: `backend/app/main.py` — register Alipay router

- [ ] **Step 1: Install Alipay SDK**

Run: `cd backend && poetry add alipay-sdk`
Expected: Added to pyproject.toml

- [ ] **Step 2: Add Alipay settings to config.py**

In `backend/app/core/config.py`, add to the `Settings` class:

```python
ALIPAY_APP_ID: str = ""
ALIPAY_PRIVATE_KEY: str = ""
ALIPAY_PUBLIC_KEY: str = ""
ALIPAY_GATEWAY_URL: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
ALIPAY_NOTIFY_URL: str = "http://localhost:8000/api/alipay/notify"
```

- [ ] **Step 3: Create alipay.py router**

Create `backend/app/api/alipay.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update

from app.core.database import get_db
from app.core.deps import require_role
from app.core.config import settings
from app.models.user import Staff
from app.models.order import Order
from app.models.room import Room
from app.ws.manager import manager
from app.core.utils import cst_now

router = APIRouter(prefix="/api", tags=["alipay"])


@router.post("/orders/{order_id}/create-alipay-order")
async def create_alipay_order(
    order_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "checked_in":
        raise HTTPException(status_code=409, detail="订单状态不正确")

    # Get bill total
    from app.api.orders import get_bill_total
    total = await get_bill_total(db, order.id)

    # Create Alipay trade page pay request
    from alipay.aop.api.AlipayClientFactory import AlipayClientFactory
    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest

    alipay_client = AlipayClientFactory.get_default_alipay_client(
        settings.ALIPAY_GATEWAY_URL,
        settings.ALIPAY_APP_ID,
        settings.ALIPAY_PRIVATE_KEY,
        settings.ALIPAY_PUBLIC_KEY,
    )

    model = AlipayTradePagePayModel()
    model.outTradeNo = str(order.id)
    model.totalAmount = f"{total / 100:.2f}"
    model.subject = f"SmartStay Room {order.room_id}"
    model.productCode = "FAST_INSTANT_TRADE_PAY"

    request = AlipayTradePagePayRequest()
    request.bizModel = model
    request.notifyUrl = settings.ALIPAY_NOTIFY_URL

    response = alipay_client.page_execute(request, http_method="GET")
    return {"pay_url": response}


@router.post("/alipay/notify")
async def alipay_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    params = dict(form)

    # Verify signature
    from alipay.aop.api.util.SignatureUtils import verify_with_rsa
    sign = params.pop("sign", "")
    sign_type = params.pop("sign_type", "RSA2")
    # Sort params and verify
    unsigned_params = sorted(params.items())
    unsigned_string = "&".join(f"{k}={v}" for k, v in unsigned_params)

    if not verify_with_rsa(settings.ALIPAY_PUBLIC_KEY, unsigned_string, sign):
        raise HTTPException(status_code=400, detail="签名验证失败")

    trade_status = params.get("trade_status")
    out_trade_no = params.get("out_trade_no")

    if trade_status == "TRADE_SUCCESS":
        result = await db.execute(select(Order).where(Order.id == uuid.UUID(out_trade_no)))
        order = result.scalar_one_or_none()
        if order and order.status == "checked_in":
            order.status = "checked_out"
            order.check_out_time = cst_now()
            await db.execute(
                sa_update(Room).where(Room.id == order.room_id).values(status="dirty")
            )
            await db.commit()
            await manager.broadcast_biz({
                "event": "room.status_change",
                "data": {"room_id": str(order.room_id), "status": "dirty"},
            })

    return "success"
```

Note: The exact Alipay SDK API may vary by version. Adjust imports and method calls based on the installed `alipay-sdk` version. The key flow is: create trade model → execute request → return pay URL.

- [ ] **Step 4: Register alipay router in main.py**

In `backend/app/main.py`, add import and register:

```python
from app.api.alipay import router as alipay_router
# ...
app.include_router(alipay_router)
```

- [ ] **Step 5: Extract get_bill_total helper**

In `backend/app/api/orders.py`, extract the bill total calculation into a reusable function. Find the bill endpoint (lines 90-119) and extract:

```python
async def get_bill_total(db: AsyncSession, order_id: uuid.UUID) -> int:
    """Calculate grand total for an order (room_rate + consumptions)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return 0
    room_result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = room_result.scalar_one_or_none()
    room_rate = room.current_price if room else 0

    from app.models.consumption import Consumption
    cons_result = await db.execute(select(Consumption).where(Consumption.order_id == order_id))
    consumptions = cons_result.scalars().all()
    consumption_total = sum(c.amount * c.quantity for c in consumptions)

    return room_rate + consumption_total
```

- [ ] **Step 6: Verify backend compiles**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: No output (success)

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/alipay.py backend/app/api/orders.py backend/app/core/config.py backend/app/main.py backend/pyproject.toml backend/poetry.lock
git commit -m "feat: add Alipay sandbox integration for checkout payments"
```

---

## Final Verification

- [ ] **Step 1: Backend type check**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: No errors

- [ ] **Step 2: Backend tests**

Run: `cd backend && poetry run pytest -x -q`
Expected: All tests pass

- [ ] **Step 3: Frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 5: Final commit with all changes**

```bash
git add -A
git status
git commit -m "feat: B-end optimization complete — all 10 items implemented"
```
