# B 端全面优化设计文档

**日期**: 2026-06-01
**范围**: 缺失功能补全 + 代码质量修复 + 退房结算流程

## 背景

B 端 React 前端整体完成度约 85-90%。存在以下问题：
- 4 个按钮只有 toast 提示，功能未实现（员工编辑/禁用、发票详情/导出）
- 住客管理缺少编辑和重置密码功能
- 多个页面吞掉 API 错误，用户无反馈
- API 地址硬编码 localhost
- 非入住房间点击无反应
- 退房流程无结算环节，直接退房

## 一、缺失功能（5 项）

### 1. 员工编辑

**改动文件**: `frontend/src/pages/manager/UserManagementPage.tsx`

- 「编辑」按钮 → 弹出 Ant Design Modal
- 表单字段：姓名、手机号、角色（下拉选择 front_desk/manager/admin）
- 预填当前员工信息
- 提交调用 `PUT /api/admin/users/{id}`
- 保存后刷新列表

**后端新增**: `PUT /api/admin/users/{id}` — 更新员工信息

### 2. 员工禁用/启用

**改动文件**: `frontend/src/pages/manager/UserManagementPage.tsx`

- 「禁用」按钮 → `Modal.confirm` 确认弹窗
- 调用 `PUT /api/admin/users/{id}/toggle-status`
- 禁用后按钮变为「启用」，行样式变灰（opacity 0.5）
- 状态标签显示「已禁用」

**后端新增**: `PUT /api/admin/users/{id}/toggle-status` — 切换员工启用/禁用状态

### 3. 发票详情

**改动文件**: `frontend/src/pages/manager/InvoiceManagementPage.tsx`

- 「查看」按钮 → Ant Design Drawer（右侧滑出）
- 展示字段：订单ID、公司名称、税号、邮箱、地址、金额、状态、创建时间
- 数据来自现有 `GET /api/admin/invoices` 返回的单条记录

### 4. 发票导出 PDF

**改动文件**: `frontend/src/pages/manager/InvoiceManagementPage.tsx`

- 「导出PDF」按钮 → 前端生成 PDF 下载
- 使用 `jsPDF` 库（新增依赖）
- PDF 内容：发票抬头、税号、金额明细、开票日期、订单号
- 纯前端实现，不需要后端接口

**新增依赖**: `npm install jspdf`

### 5. 住客编辑

**改动文件**: `frontend/src/pages/manager/UserManagementPage.tsx`

- 住客 tab 新增「编辑」列，包含两个按钮：
  - 「编辑」→ Modal 可修改手机号
  - 「重置密码」→ `Modal.confirm` 确认 → 调用后端重置为 `123456`

**后端新增**:
- `PUT /api/admin/guests/{id}` — 更新住客信息（手机号）
- `PUT /api/admin/guests/{id}/reset-password` — 重置密码为默认值

## 二、代码质量修复（3 项）

### 6. 错误提示修复

**改动文件**（7 个）:
- `frontend/src/pages/manager/DashboardPage.tsx` — 3 处
- `frontend/src/pages/manager/InvoiceManagementPage.tsx` — 1 处
- `frontend/src/pages/manager/UserManagementPage.tsx` — 1 处
- `frontend/src/pages/manager/AIAuditPage.tsx` — 1 处
- `frontend/src/pages/admin/AdminPage.tsx` — 1 处
- `frontend/src/pages/front-desk/WorkOrderBoard.tsx` — 2 处
- `frontend/src/hooks/useWebSocket.ts` — 1 处

将 `.catch(() => {})` 改为 `.catch(() => message.error('具体提示'))`，每个 API 调用给出简短中文错误提示。

### 7. API 地址配置化

**改动文件**:
- `frontend/.env`（新建）— `VITE_API_BASE_URL=http://localhost:8765`
- `frontend/.env.example`（新建）— 模板文件，提交到 git
- `frontend/src/api/client.ts` — `baseURL` 改为 `import.meta.env.VITE_API_BASE_URL`
- `frontend/src/hooks/useWebSocket.ts` — WebSocket URL 从环境变量读取

### 8. 非入住房间点击响应

**改动文件**: `frontend/src/pages/front-desk/RoomGridPage.tsx`

- 点击空房/脏房/维修房 → 弹出 Ant Design Modal
- 显示：房间号、房型、当前状态、当前价格
- 空房额外显示「快捷开房」按钮（复用已有 CheckInModal）

## 三、退房结算流程（2 项）

### 9. 退房结算弹窗

**改动文件**: `frontend/src/pages/front-desk/RoomGridPage.tsx`

改造现有「办理退房」流程，点击后弹出结算 Modal：

**UI 布局**:
- 顶部：房间号、房型、住客姓名、入住时间
- 账单明细表格：房费、消费项目（如有）、合计
- 底部两个按钮：「线上支付」「立即支付(线下)」

**线上支付**:
- 仅当订单来源为 `ctrip` 或 `meituan` 时可用，否则置灰
- 点击后显示 loading "正在等待第三方确认..."
- 2 秒后调用 `PUT /api/orders/{id}/checkout`
- 显示退房成功提示

**立即支付**:
- 始终可用
- 点击后跳转支付宝沙箱页面（见第 10 项）

### 10. 支付宝沙箱集成

**后端新增**:
- `POST /api/orders/{id}/create-alipay-order` — 调用支付宝沙箱 API 创建支付订单，返回支付页面 URL
- `POST /api/alipay/notify` — 支付宝异步回调接口，验证签名后更新订单状态

**后端新增依赖**: `alipay-sdk` (Python)

**后端配置**（.env 新增）:
```
ALIPAY_APP_ID=<沙箱应用ID>
ALIPAY_PRIVATE_KEY=<应用私钥>
ALIPAY_PUBLIC_KEY=<支付宝公钥>
ALIPAY_GATEWAY_URL=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

**前端流程**:
1. 点击「立即支付」→ 调用 `POST /api/orders/{id}/create-alipay-order`
2. 获取支付 URL → `window.open(url)` 新窗口打开支付宝沙箱
3. 支付完成后支付宝回调后端 → 后端通过 WebSocket 推送支付成功事件
4. 前端收到 WebSocket 事件 → 调用 checkout API → 显示退房成功

## 四、后端 API 变更汇总

| 方法 | 路径 | 说明 | 类型 |
|------|------|------|------|
| PUT | `/api/admin/users/{id}` | 更新员工信息 | 新增 |
| PUT | `/api/admin/users/{id}/toggle-status` | 禁用/启用员工 | 新增 |
| PUT | `/api/admin/guests/{id}` | 更新住客信息 | 新增 |
| PUT | `/api/admin/guests/{id}/reset-password` | 重置住客密码 | 新增 |
| POST | `/api/orders/{id}/create-alipay-order` | 创建支付宝沙箱订单 | 新增 |
| POST | `/api/alipay/notify` | 支付宝异步回调 | 新增 |

## 五、新增依赖

**前端**:
- `jspdf` — PDF 生成

**后端**:
- `alipay-sdk` — 支付宝沙箱 SDK

## 六、验证

```bash
# 前端
cd frontend && npx tsc --noEmit
cd frontend && npm run lint

# 后端
cd backend && poetry run python -m py_compile app/main.py
cd backend && poetry run pytest -x -q
```

手动测试清单：
- [ ] 员工编辑：修改姓名、手机号、角色 → 保存 → 列表刷新
- [ ] 员工禁用：禁用 → 行变灰 → 启用 → 恢复
- [ ] 发票详情：点击查看 → Drawer 展示完整信息
- [ ] 发票导出：点击导出 → PDF 下载成功
- [ ] 住客编辑：修改手机号 → 保存成功
- [ ] 住客重置密码：确认 → 重置成功
- [ ] 错误提示：断网后操作 → 显示错误提示
- [ ] API 配置：修改 .env 中的地址 → 前端连接新地址
- [ ] 非入住房间点击：点击空房 → 显示信息面板
- [ ] 退房线上支付：携程订单 → 线上支付 → 2秒后退房成功
- [ ] 退房线下支付：任何订单 → 立即支付 → 跳转支付宝沙箱
