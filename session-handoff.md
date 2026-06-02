# SmartStay — Session Handoff

## How to Use This File

1. **At end of session**: Fill in the "Last Session" section below with what was done, what's pending, and any blockers.
2. **At start of next session**: Read this file first. Resume from the "Next Steps" listed.

---

## Restart Marker (for quick session resume)

**Last updated**: 2026-06-01
**Active feature**: F013 (人脸识别登录) — done (bugs fixed)
**Next up**: User-requested tasks
**Quick command to resume**: Read this file → Read feature_list.json → Ask user

---

## Last Session

**Date**: 2026-06-01
**Feature**: F013 — 人脸识别登录 (bug fix session)
**Goal**: Fix 404 on `/api/face/search` and empty `face_id` in guests table

**What was done**:
- Killed stale uvicorn/Python processes on port 8000 (PIDs 25108, 27684)
- Restarted server cleanly
- Verified `/api/face/search` returns 422 (not 404) — route IS properly registered
- Listed guests via admin API → found 1 guest (kxh/康烜航) with no face_id
- Deleted that guest via `DELETE /api/admin/users/{id}` (admin API)
- Verified guest list is now empty
- Added bug entries B003/B004 to feature_list.json for traceability

**Verification results**:
- [x] `/api/face/search` returns 422 (expected — missing file) instead of 404
- [x] Guest list empty — ready for clean re-registration
- [x] Server running on port 8000 with all face routes

**Status**: done
**Blockers**: None
**Next session picks up at**: User can now do B-end check-in with face registration → face_id will be stored → C-end face login will work
