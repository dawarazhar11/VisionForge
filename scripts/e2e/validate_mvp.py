#!/usr/bin/env python3
"""
VisionForge end-to-end MVP validation (DAW-33).

Validates the API pipeline: health → auth → upload → render → train → TFLite export.
iOS camera inference is a manual step (see docs/E2E_MVP_CHECKLIST.md).

Usage:
  python scripts/e2e/validate_mvp.py --smoke
  python scripts/e2e/validate_mvp.py --full --upload-file "STEP Files/Test 1.STEP"
  python scripts/e2e/validate_mvp.py --base-url http://localhost:8002
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx required. Install with: pip install httpx", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://localhost:8002"
DEFAULT_EMAIL = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
DEFAULT_PASSWORD = "E2eTest!234"


@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""
    data: dict = field(default_factory=dict)


class MvpValidator:
    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        upload_file: Optional[Path],
        poll_interval: float,
        render_timeout: int,
        train_timeout: int,
    ):
        self.base_url = base_url.rstrip("/")
        self.api = f"{self.base_url}/api/v1"
        self.email = email
        self.password = password
        self.upload_file = upload_file
        self.poll_interval = poll_interval
        self.render_timeout = render_timeout
        self.train_timeout = train_timeout
        self.token: Optional[str] = None
        self.project_id: Optional[str] = None
        self.render_job_id: Optional[str] = None
        self.train_job_id: Optional[str] = None
        self.model_id: Optional[str] = None
        self.results: list[StepResult] = []

    def _record(self, name: str, passed: bool, detail: str = "", **data: Any) -> StepResult:
        result = StepResult(name=name, passed=passed, detail=detail, data=dict(data))
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        return result

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.api}{path}"
        with httpx.Client(timeout=timeout) as client:
            return client.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
                files=files,
                data=data,
            )

    def check_health(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.base_url}/health")
            ok = resp.status_code == 200
            self._record("health", ok, resp.text[:120] if ok else f"HTTP {resp.status_code}")
            return ok
        except httpx.ConnectError:
            self._record(
                "health",
                False,
                f"Cannot reach {self.base_url}. Start stack: podman-compose up -d",
            )
            return False

    def register_and_login(self) -> bool:
        reg = self._request(
            "POST",
            "/auth/register",
            json_body={"email": self.email, "password": self.password, "full_name": "E2E Validator"},
        )
        if reg.status_code not in (201, 400):
            self._record("register", False, f"HTTP {reg.status_code}: {reg.text[:200]}")
            return False

        login = self._request(
            "POST",
            "/auth/login/json",
            json_body={"email": self.email, "password": self.password},
        )
        if login.status_code != 200:
            self._record("login", False, f"HTTP {login.status_code}: {login.text[:200]}")
            return False

        payload = login.json()
        self.token = payload.get("access_token")
        if not self.token:
            self._record("login", False, "No access_token in response")
            return False

        self._record("register_login", True, self.email)
        return True

    def create_or_upload_project(self) -> bool:
        if self.upload_file and self.upload_file.exists():
            with self.upload_file.open("rb") as fh:
                resp = self._request(
                    "POST",
                    "/projects/upload",
                    files={"file": (self.upload_file.name, fh, "application/octet-stream")},
                    data={
                        "name": f"E2E {self.upload_file.name}",
                        "description": "DAW-33 automated validation upload",
                    },
                    timeout=300.0,
                )
            if resp.status_code != 201:
                self._record("upload", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
                return False
            project = resp.json()
        else:
            resp = self._request(
                "POST",
                "/projects/",
                json_body={
                    "name": "E2E metadata-only project",
                    "description": "Smoke test without file upload",
                },
            )
            if resp.status_code != 201:
                self._record("create_project", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
                return False
            project = resp.json()

        self.project_id = project.get("id")
        if not self.project_id:
            self._record("project", False, "No project id returned")
            return False

        has_file = bool(project.get("file_path"))
        self._record(
            "project",
            True,
            f"id={self.project_id}, file={'yes' if has_file else 'metadata-only'}",
        )
        return True

    def create_test_job(self) -> bool:
        if not self.project_id:
            return False
        resp = self._request(
            "POST",
            "/jobs/",
            json_body={
                "project_id": self.project_id,
                "job_type": "test",
                "config": {"message": "DAW-33 smoke test"},
            },
        )
        if resp.status_code != 201:
            self._record("test_job", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        job = resp.json()
        job_id = job.get("id")
        final = self._wait_for_job(job_id, timeout=30, label="test_job")
        return final is not None and final.get("status") == "SUCCESS"

    def create_render_job(self, num_renders: int = 2) -> bool:
        if not self.project_id:
            return False
        resp = self._request(
            "POST",
            "/jobs/",
            json_body={
                "project_id": self.project_id,
                "job_type": "render",
                "config": {
                    "num_renders": num_renders,
                    "resolution_x": 640,
                    "resolution_y": 480,
                    "eevee_samples": 16,
                    "use_gpu": False,
                },
            },
        )
        if resp.status_code != 201:
            self._record("render_job_create", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
            return False
        self.render_job_id = resp.json().get("id")
        self._record("render_job_create", True, f"id={self.render_job_id}")
        return bool(self.render_job_id)

    def wait_render_job(self) -> bool:
        if not self.render_job_id:
            return False
        job = self._wait_for_job(self.render_job_id, self.render_timeout, "render_job")
        if not job:
            return False
        ok = job.get("status") == "SUCCESS"
        detail = job.get("status", "unknown")
        if not ok:
            metrics = job.get("metrics_json") or {}
            detail = metrics.get("error") or job.get("error_message") or detail
        self._record("render_job_complete", ok, str(detail)[:300])
        return ok

    def create_train_job(self, epochs: int = 1) -> bool:
        if not self.project_id:
            return False
        resp = self._request(
            "POST",
            "/jobs/",
            json_body={
                "project_id": self.project_id,
                "job_type": "train",
                "config": {"epochs": epochs, "batch_size": 2, "imgsz": 320},
            },
        )
        if resp.status_code != 201:
            self._record("train_job_create", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
            return False
        self.train_job_id = resp.json().get("id")
        self._record("train_job_create", True, f"id={self.train_job_id}")
        return bool(self.train_job_id)

    def wait_train_job(self) -> bool:
        if not self.train_job_id:
            return False
        job = self._wait_for_job(self.train_job_id, self.train_timeout, "train_job")
        if not job:
            return False
        ok = job.get("status") == "SUCCESS"
        detail = job.get("status", "unknown")
        if not ok:
            metrics = job.get("metrics_json") or {}
            detail = metrics.get("error") or job.get("error_message") or detail
        self._record("train_job_complete", ok, str(detail)[:300])
        if ok:
            self.model_id = self.train_job_id
        return ok

    def export_tflite(self) -> bool:
        if not self.model_id:
            self._record("tflite_export", False, "No trained model id")
            return False
        resp = self._request(
            "POST",
            f"/models/{self.model_id}/export",
            json_body={"format": "tflite", "imgsz": 320, "optimize": False, "int8": False},
            timeout=600.0,
        )
        if resp.status_code != 200:
            self._record("tflite_export", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
            return False
        payload = resp.json()
        ok = payload.get("success") is True
        detail = payload.get("export_path") or payload.get("error_message") or ""
        self._record("tflite_export", ok, str(detail)[:300])
        return ok

    def download_tflite_and_labels(self, out_dir: Path) -> bool:
        if not self.model_id:
            return False
        out_dir.mkdir(parents=True, exist_ok=True)
        tflite_path = out_dir / "model.tflite"
        labels_path = out_dir / "labels.txt"

        with httpx.Client(timeout=120.0) as client:
            tflite_resp = client.get(
                f"{self.api}/models/{self.model_id}/export/tflite/download",
                headers=self._headers(),
            )
            if tflite_resp.status_code != 200:
                self._record("tflite_download", False, f"HTTP {tflite_resp.status_code}")
                return False
            tflite_path.write_bytes(tflite_resp.content)

            labels_resp = client.get(
                f"{self.api}/models/{self.model_id}/labels",
                headers=self._headers(),
            )
            if labels_resp.status_code != 200:
                self._record("labels_download", False, f"HTTP {labels_resp.status_code}")
                return False
            labels_path.write_bytes(labels_resp.content)

        self._record(
            "tflite_package",
            True,
            f"{tflite_path} ({tflite_path.stat().st_size} bytes), {labels_path}",
        )
        return True

    def _wait_for_job(
        self, job_id: str, timeout: int, label: str
    ) -> Optional[dict[str, Any]]:
        deadline = time.time() + timeout
        last_status = None
        while time.time() < deadline:
            resp = self._request("GET", f"/jobs/{job_id}")
            if resp.status_code != 200:
                self._record(label, False, f"poll HTTP {resp.status_code}")
                return None
            job = resp.json()
            status = job.get("status")
            progress = job.get("progress", 0)
            if status != last_status:
                print(f"    … {label} {status} ({progress}%)")
                last_status = status
            if status in ("SUCCESS", "FAILED", "CANCELLED"):
                return job
            time.sleep(self.poll_interval)
        self._record(label, False, f"Timed out after {timeout}s (last={last_status})")
        return None

    def run_smoke(self) -> bool:
        print("\n=== VisionForge MVP smoke validation ===\n")
        steps: list[Callable[[], bool]] = [
            self.check_health,
            self.register_and_login,
            self.create_or_upload_project,
            self.create_test_job,
        ]
        return all(step() for step in steps)

    def run_full(self, num_renders: int, epochs: int, output_dir: Path) -> bool:
        print("\n=== VisionForge MVP full pipeline validation ===\n")
        if not self.upload_file or not self.upload_file.exists():
            self._record(
                "upload_file",
                False,
                f"Full mode requires --upload-file. Try: {REPO_ROOT / 'STEP Files' / 'Test 1.STEP'}",
            )
            return False

        steps: list[Callable[[], bool]] = [
            self.check_health,
            self.register_and_login,
            self.create_or_upload_project,
            lambda: self.create_render_job(num_renders),
            self.wait_render_job,
            lambda: self.create_train_job(epochs),
            self.wait_train_job,
            self.export_tflite,
            lambda: self.download_tflite_and_labels(output_dir),
        ]
        return all(step() for step in steps)

    def summary(self) -> int:
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"\n=== Summary: {passed}/{total} steps passed ===\n")
        failures = [r for r in self.results if not r.passed]
        if failures:
            print("Blockers:")
            for f in failures:
                print(f"  - {f.name}: {f.detail}")
        report = {
            "base_url": self.base_url,
            "email": self.email,
            "project_id": self.project_id,
            "render_job_id": self.render_job_id,
            "train_job_id": self.train_job_id,
            "model_id": self.model_id,
            "steps": [
                {"name": r.name, "passed": r.passed, "detail": r.detail, "data": r.data}
                for r in self.results
            ],
        }
        print(json.dumps(report, indent=2))
        return 0 if passed == total else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VisionForge E2E MVP validator (DAW-33)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="Health + auth + project + test job")
    mode.add_argument("--full", action="store_true", help="Full pipeline through TFLite download")

    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--upload-file",
        type=Path,
        default=REPO_ROOT / "STEP Files" / "Test 1.STEP",
        help="3D file for upload (STEP for ARM64 Docker; .blend needs demo scene)",
    )
    parser.add_argument("--num-renders", type=int, default=2, help="Minimal renders for full mode")
    parser.add_argument("--epochs", type=int, default=1, help="Minimal epochs for full mode")
    parser.add_argument("--render-timeout", type=int, default=1800)
    parser.add_argument("--train-timeout", type=int, default=3600)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "backend" / "storage" / "e2e_output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validator = MvpValidator(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        upload_file=args.upload_file,
        poll_interval=args.poll_interval,
        render_timeout=args.render_timeout,
        train_timeout=args.train_timeout,
    )
    if args.smoke:
        ok = validator.run_smoke()
    else:
        ok = validator.run_full(args.num_renders, args.epochs, args.output_dir)
    return validator.summary() if ok else max(validator.summary(), 1)


if __name__ == "__main__":
    sys.exit(main())
