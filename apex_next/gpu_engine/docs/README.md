# GPU Engine Documentation Index

This folder is the human-readable control room for the Step 3H simulator work.
Raw audit JSON files remain under `D:\Kaggriculture\reports` because the audit
scripts already write and reload evidence from there.

Start here:

- `STEP3H_GPU_CUDA_PROGRESS_REPORT.md` - full progress report through 3H-8K.
- `FOLDER_MAP.md` - what lives where and which files matter.
- `EVIDENCE_INDEX.md` - audit reports, trace cache, and validation evidence.
- `NEXT_ACTIONS.md` - next gates and rules before Step 5B can restart.

Important boundaries:

- Do not modify `D:\Kaggriculture\submission.py`.
- Do not modify `D:\Kaggriculture\APEX4_SUBMISSION_FINAL.py`.
- Do not start Step 5B PPO until CUDA parity and benchmark gates close.
- Do not call this a fast rollout backend until CUDA performance is measured
  after 100-seed full parity.
