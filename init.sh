#!/usr/bin/env bash
# SmartStay — Environment Verification Script
# Run this to check if the development environment is properly set up.
# Exit on first failure.
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
section() { echo -e "\n--- $1 ---"; }

# ---- System Tools ----
section "System Tools"

command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 && pass "Python found" || fail "Python not found"
command -v poetry >/dev/null 2>&1 && pass "Poetry found" || fail "Poetry not found (pip install poetry)"
command -v node >/dev/null 2>&1 && pass "Node.js found" || fail "Node.js not found"
command -v npm >/dev/null 2>&1 && pass "npm found" || fail "npm not found"
command -v flutter >/dev/null 2>&1 && pass "Flutter found" || warn "Flutter not found (optional, needed for C-end)"

# ---- Backend ----
section "Backend (FastAPI)"

cd backend 2>/dev/null || fail "backend/ directory not found"

if [ -f ".env" ]; then
  pass ".env file exists"
else
  warn ".env file missing — create from .env.example or set DATABASE_URL, SECRET_KEY, DEEPSEEK_API_KEY"
fi

if poetry check >/dev/null 2>&1; then
  pass "pyproject.toml is valid"
else
  warn "pyproject.toml validation failed"
fi

# Check Python compilation
if poetry run python -m py_compile app/main.py 2>/dev/null; then
  pass "Backend compiles (app/main.py)"
else
  fail "Backend compilation failed"
fi

# Check database connectivity (non-fatal)
if poetry run python -c "
import asyncio
from app.core.database import engine
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        return result.scalar() == 1
ok = asyncio.run(check())
exit(0 if ok else 1)
" 2>/dev/null; then
  pass "PostgreSQL connection OK"
else
  warn "Cannot connect to PostgreSQL (check DATABASE_URL in .env)"
fi

cd ..

# ---- B-end Frontend ----
section "B-end Frontend (React)"

cd frontend 2>/dev/null || fail "frontend/ directory not found"

if [ -d "node_modules" ]; then
  pass "node_modules exists"
else
  warn "node_modules missing — run: npm install"
fi

# Type check
if npx tsc --noEmit 2>/dev/null; then
  pass "TypeScript type check passed"
else
  warn "TypeScript type check failed (run: npx tsc --noEmit for details)"
fi

cd ..

# ---- C-end Flutter ----
section "C-end Flutter"

if [ -d "smartstay-flutter" ]; then
  cd smartstay-flutter
  if flutter analyze --no-fatal-infos --no-fatal-warnings 2>/dev/null; then
    pass "Flutter analyze passed"
  else
    warn "Flutter analyze found issues (run: flutter analyze for details)"
  fi
  cd ..
else
  warn "smartstay-flutter/ not found — skipping Flutter checks"
fi

# ---- Summary ----
echo ""
echo -e "${GREEN}=== Environment check complete ===${NC}"
echo "If any warnings appear, fix them before starting development."
