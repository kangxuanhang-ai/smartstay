# Fix: Face Recognition Login — 404 + Empty face_id

## Context

User is testing C-end face login. Two problems:

1. **`/api/face/search` returns 404** — Route is registered in `backend/app/api/face.py` (`@router.post("/search")` with prefix `/api/face`) and included in `backend/app/main.py` (`app.include_router(face_router)`). Server starts successfully but returns 404. Suspected causes: compilation error during auto-reload, or stale .pyc cache.

2. **Empty `face_id` in guests table** — Previous face registration calls to Aliyun failed because the face DB (`smartstay_faces`) was never created (the `create_face_db()` function existed but was never called). Now that we added `create_face_db()` to the startup lifespan, existing guests still have `null face_id`.

## Diagnosis Needed

- Check if `app/api/face.py` compiles correctly — there may be a hidden import error
- Check if `app/aliyun/face.py` compiles correctly after edits (warnings import, parameter rename)
- Provide a script/endpoint to retroactively register faces for existing guests who already have Aliyun face data (or clear them and re-register)

## Plan

### Step 1: Run py_compile on both face modules to check for errors

```bash
cd backend && poetry run python -m py_compile app/api/face.py
cd backend && poetry run python -m py_compile app/aliyun/face.py
```

If errors found, fix them.

### Step 2: If no compile errors, restart server cleanly

The auto-reload may have missed changes. Kill any old uvicorn processes and restart:
```bash
# Check for existing processes on port 8000
# Restart with --reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Provide face re-registration fix

The guest the user registered earlier has no `face_id` because `add_face` to Aliyun failed (face DB didn't exist). Options:
- **Option A**: Clear that guest and let user re-register fresh through B-end check-in
- **Option B**: Write a one-shot script that re-attempts face registration for guests with `face_registered=false` and `liveFaceBlob` data (impractical — we don't have the image anymore)

Recommended: Option A — clear the specific guest (and their order) so user can do a clean check-in.

## Verification

- `py_compile` passes on both files
- Server starts on port 8000 without errors
- `POST /api/face/search` returns 200 (not 404)
- After re-registration, `guests.face_id` is populated
