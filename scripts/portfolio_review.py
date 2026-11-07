"""Private, additive portfolio review tooling. Never applies or publishes changes."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import unicodedata
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageOps


SITE_ROOT = Path(__file__).resolve().parents[1]
TOP_KEYS = {"schemaVersion", "replaceExisting", "projects"}
PROJECT_KEYS = {"id", "title", "startDate", "endDate", "year", "month", "category", "role", "location", "cover", "gallery"}
PHOTO_KEYS = {"src", "alt", "position"}
TEXT_LIMITS = {"title": 300, "category": 100, "role": 1000, "location": 500, "alt": 400}
APPROVAL_FLAGS = ("scopeConfirmed", "rightsConfirmed", "publicationApproved")
APPROVAL_EVIDENCE = ("scopeEvidence", "rightsEvidence", "publicationEvidence")
APPROVAL_KEYS = {"schemaVersion", "projectId", "subjectSha256", *APPROVAL_FLAGS, *APPROVAL_EVIDENCE}
DRAFT_KEYS = {"schemaVersion", "kind", "baseSha256", "project"}
PHOTO_PATH = re.compile(r"assets/projects/[a-zA-Z0-9_./-]+\.(?:jpe?g|png|webp)\Z", re.I)
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,99}\Z")
PLACEHOLDER = re.compile(r"확인\s*필요|미확인|미정|추정|TODO|TBD|unknown", re.I)
PRIVATE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|(?:https?|file|ftp)://|(?:^|\s)/(?:Users|home|workspace|mnt|tmp)/|OneDrive|AppData|_개발준비|tests[/\\]_artifacts)", re.I)
EMAIL = re.compile(r"[\w.+%~-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:0(?:1[016789]|2|[3-6]\d|70|80)|\+?82[- .]?(?:1[016789]|2|[3-6]\d|70|80))[- .]?\d{3,4}[- .]?\d{4}(?!\d)")
MONEY = re.compile(r"₩|(?:KRW|계약금액|공급가액|지급금액|부가세|금액)\s*[:=]?\s*[\d,]+|\d[\d,]*(?:\.\d+)?\s*(?:억|만|천)?\s*원", re.I)
STATIC_EXTENSIONS = {".html", ".css", ".js", ".json", ".webmanifest", ".txt", ".xml", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf"}


class ReviewError(ValueError):
    """An expected validation or output-protection failure."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ReviewError("중복 JSON 키: " + key)
            result[key] = value
        return result
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ReviewError("검토 JSON이 8MiB 제한을 넘습니다.")
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle, object_pairs_hook=pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewError(f"JSON 읽기 실패: {path.name}: {error}") from error


def contained(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def protected_output(path: Path, root: Path, *, input_files=(), source_dirs=()) -> Path:
    """Allow private repo outputs or explicit external paths, never original inputs."""
    lexical = Path(os.path.abspath(path))
    resolved = lexical.resolve()
    root = root.resolve()
    for protected_root in {root, SITE_ROOT.resolve()}:
        private_roots = [protected_root / "_개발준비", protected_root / "tests" / "_artifacts"]
        if lexical.is_relative_to(protected_root) and not resolved.is_relative_to(protected_root):
            raise ReviewError("출력 경로가 링크를 통해 저장소 밖으로 벗어납니다.")
        if resolved.is_relative_to(protected_root) and not any(resolved.is_relative_to(p) for p in private_roots):
            raise ReviewError("저장소 출력은 _개발준비 또는 tests/_artifacts 아래여야 합니다.")
        if protected_root.is_relative_to(resolved):
            raise ReviewError("저장소 원본을 포함하는 상위 폴더에는 출력할 수 없습니다.")
    for parent in (lexical, *lexical.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ReviewError("링크 또는 junction 경로로는 출력할 수 없습니다.")
    for source in input_files:
        original = Path(source).resolve()
        if resolved == original or original.is_relative_to(resolved) or resolved.is_relative_to(original):
            raise ReviewError("출력과 입력 원본 경로가 겹칩니다.")
    for folder in source_dirs:
        original = Path(folder).resolve()
        if resolved.is_relative_to(original) or original.is_relative_to(resolved):
            raise ReviewError("출력을 사진 입력 원본 폴더와 분리해야 합니다.")
    return resolved


def write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def timestamp_name(prefix: str) -> str:
    return prefix + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def public_source_path(path: Path, root: Path, *, subtree: str | None = None, directory=False) -> Path:
    """Reject aliases before reading/copying a publishable source, including ancestors."""
    root = root.resolve()
    lexical = Path(os.path.abspath(path))
    boundary = root / subtree if subtree else root
    if not lexical.is_relative_to(boundary):
        raise ReviewError("공개 원본 경로가 허용된 폴더 밖입니다.")
    relative = lexical.relative_to(root)
    component = root
    for part in (None, *relative.parts):
        if part is not None:
            component = component / part
        if component.is_symlink() or (hasattr(component, "is_junction") and component.is_junction()):
            raise ReviewError("공개 원본의 symlink 또는 junction 경로는 허용하지 않습니다.")
    resolved = lexical.resolve(strict=True)
    if not resolved.is_relative_to(boundary):
        raise ReviewError("공개 원본의 실제 경로가 허용된 폴더 밖입니다.")
    details = lexical.stat()
    if directory:
        if not stat.S_ISDIR(details.st_mode):
            raise ReviewError("공개 자산 폴더 형식이 아닙니다.")
    elif not stat.S_ISREG(details.st_mode) or details.st_nlink > 1:
        raise ReviewError("공개 원본은 hardlink가 아닌 일반 파일이어야 합니다.")
    return lexical


def public_photo_path(root: Path, source: Any) -> Path:
    if (not isinstance(source, str) or not PHOTO_PATH.fullmatch(source) or ".." in source
            or any(part in {"", ".", ".."} for part in source.split("/"))):
        raise ReviewError("사진은 assets/projects/ 아래 허용된 상대경로여야 합니다.")
    path = root / PurePosixPath(source)
    return public_source_path(path, root, subtree="assets/projects")


def image_details(path: Path) -> dict[str, Any]:
    """Decode every image; inspect all EXIF/GPS and textual metadata."""
    with Image.open(path) as image:
        image.load()
        exif = image.getexif()
        gps = 34853 in exif
        try:
            gps = gps or bool(exif.get_ifd(34853))
        except (KeyError, ValueError, TypeError, AttributeError):
            pass
        info = {str(k): (v.decode("utf-8", errors="replace") if isinstance(v, bytes) else v)
                for k, v in image.info.items() if isinstance(v, (str, bytes))}
        if any(re.search(r"GPS|latitude|longitude", k + " " + v, re.I) for k, v in info.items()):
            gps = True
        return {"width": image.width, "height": image.height, "format": image.format,
                "gps": gps, "exifPresent": bool(exif) or bool(image.info.get("exif")), "textMetadata": info,
                "frames": getattr(image, "n_frames", 1),
                "exifText": [str(v) for v in exif.values() if isinstance(v, (str, bytes))]}


def validate_data(data: Any, root: Path, *, today: date | None = None) -> dict[str, Any]:
    root = root.resolve()
    today = today or date.today()
    issues: list[dict[str, str]] = []
    photo_count = 0
    ids: set[str] = set()
    assets: set[str] = set()
    inspected: dict[str, Any] = {}
    precision = {"day": 0, "month": 0, "year": 0}

    def issue(code, field, message):
        issues.append({"code": code, "field": field, "message": message})

    def scan_text(value, field):
        if isinstance(value, dict):
            for key, item in value.items():
                scan_text(str(key), field + ".<key>")
                scan_text(item, field + "." + str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                scan_text(item, f"{field}[{index}]")
        elif isinstance(value, str):
            normalized = unicodedata.normalize("NFKC", value)
            normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)
            normalized = re.sub(r"[‐‑‒–—−]", "-", normalized)
            for code, expression, message in [
                ("unconfirmed_text", PLACEHOLDER, "확인 필요·미정 문구를 공개 자료에 사용할 수 없습니다."),
                ("internal_path", PRIVATE_PATH, "절대·내부·외부 주소가 공개 문자열에 포함되어 있습니다."),
                ("email_exposure", EMAIL, "이메일이 공개 실적 문자열에 포함되어 있습니다."),
                ("phone_exposure", PHONE, "전화번호가 공개 실적 문자열에 포함되어 있습니다."),
                ("money_exposure", MONEY, "금액이 공개 실적 문자열에 포함되어 있습니다."),
            ]:
                if expression.search(normalized):
                    issue(code, field, message)

    def keys(value, allowed, field, required=()):
        if not isinstance(value, dict):
            issue("object_type", field, "객체 형식이 필요합니다.")
            return False
        for key in value.keys() - allowed:
            issue("unknown_key", field + "." + key, "허용되지 않은 공개 키입니다.")
        for key in set(required) - value.keys():
            issue("missing_key", field + "." + key, "필수 공개 키가 없습니다.")
        return True

    def text(value, field, required=False, limit=None):
        if not isinstance(value, str) or (required and not value.strip()):
            issue("text_type", field, "문자열" + ("과 내용" if required else "") + "이 필요합니다.")
        elif limit is not None and len(value.encode("utf-16-le", errors="surrogatepass")) // 2 > limit:
            issue("text_length", field, f"프런트엔드와 같은 문자열 길이 상한({limit}, UTF-16 단위)을 넘습니다.")

    def full_date(value, field):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            issue("date_format", field, "날짜는 YYYY-MM-DD 형식이어야 합니다.")
            return None
        try:
            result = date.fromisoformat(value)
        except ValueError:
            issue("invalid_date", field, "존재하지 않는 날짜입니다.")
            return None
        if result > today:
            issue("future_date", field, "아직 진행되지 않은 날짜를 수행 실적으로 확정할 수 없습니다.")
        return result

    scan_text(data, "portfolio")
    if not keys(data, TOP_KEYS, "portfolio", TOP_KEYS):
        return {"passed": False, "issues": issues, "projectCount": 0, "photoCount": 0}
    if type(data.get("schemaVersion")) is not int or data.get("schemaVersion") != 1:
        issue("schema_version", "portfolio.schemaVersion", "schemaVersion=1만 지원합니다.")
    if type(data.get("replaceExisting")) is not bool:
        issue("boolean_type", "portfolio.replaceExisting", "true/false 형식이어야 합니다.")
    if data.get("replaceExisting") is not True:
        issue("replace_existing", "portfolio.replaceExisting", "현재 프런트엔드와 동일하게 true만 허용합니다.")
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        issue("projects_type", "portfolio.projects", "비어 있지 않은 프로젝트 배열이 필요합니다.")
        projects = []
    for index, project in enumerate(projects):
        field = f"portfolio.projects[{index}]"
        if not keys(project, PROJECT_KEYS, field, {"id", "title", "category", "cover", "gallery"}):
            continue
        identity = project.get("id")
        if not isinstance(identity, str) or not SLUG.fullmatch(identity):
            issue("project_id", field + ".id", "ID는 영문 소문자·숫자·하이픈·밑줄 조합이어야 합니다.")
        elif identity in ids:
            issue("duplicate_id", field + ".id", "중복 프로젝트 ID입니다.")
        else:
            ids.add(identity)
        for key in ("title", "category", "role", "location"):
            if key in project or key in {"title", "category"}:
                text(project.get(key), field + "." + key, key in {"title", "category"}, TEXT_LIMITS[key])
        if "startDate" in project:
            precision["day"] += 1
            start = full_date(project["startDate"], field + ".startDate")
            end = full_date(project["endDate"], field + ".endDate") if "endDate" in project else start
            if start and end and start > end:
                issue("date_order", field, "종료일이 시작일보다 앞섭니다.")
            if "year" in project or "month" in project:
                issue("mixed_precision", field, "일자와 별도 연·월 정밀도를 혼용하지 마세요.")
        else:
            precision["month" if "month" in project else "year"] += 1
            year = project.get("year")
            if type(year) is not int or not 1000 <= year <= today.year:
                issue("year", field + ".year", "확인된 연도를 정수로 입력하세요.")
            if "endDate" in project:
                issue("mixed_precision", field + ".endDate", "연도·월만 확인한 경우 종료일을 만들 수 없습니다.")
            if "month" in project:
                month = project["month"]
                if type(month) is not int or not 1 <= month <= 12:
                    issue("month", field + ".month", "월은 1~12 정수여야 합니다.")
                elif year == today.year and month > today.month:
                    issue("future_date", field + ".month", "미래의 월입니다.")
        gallery = project.get("gallery")
        if not isinstance(gallery, list):
            issue("gallery_type", field + ".gallery", "사진 배열이 필요합니다.")
            gallery = []
        local_seen = set()
        for position, photo in enumerate([project.get("cover"), *gallery]):
            photo_field = field + (".cover" if position == 0 else f".gallery[{position - 1}]")
            if not keys(photo, PHOTO_KEYS, photo_field, {"src", "alt"}):
                continue
            text(photo.get("alt"), photo_field + ".alt", True, TEXT_LIMITS["alt"])
            if "position" in photo and (not isinstance(photo["position"], str) or not re.fullmatch(r"(?:100|\d{1,2})(?:\.\d+)?% (?:100|\d{1,2})(?:\.\d+)?%", photo["position"])):
                issue("photo_position", photo_field + ".position", "위치는 퍼센트 두 값이어야 합니다.")
            source = photo.get("src")
            try:
                path = public_photo_path(root, source)
                if source in local_seen:
                    issue("duplicate_photo", photo_field + ".src", "한 프로젝트 안의 사진 경로가 중복됩니다.")
                local_seen.add(source)
                assets.add(source)
                photo_count += 1
                if source not in inspected:
                    details = image_details(path)
                    inspected[source] = details
                    if details["gps"]:
                        issue("gps_metadata", photo_field + ".src", "GPS 위치 메타데이터가 남아 있습니다.")
                    if details["exifPresent"] or details["textMetadata"]:
                        issue("image_metadata", photo_field + ".src", "EXIF/XMP/문자열 메타데이터가 남아 있습니다. 정제 사본을 사용하세요.")
                    if details["frames"] != 1:
                        issue("animated_image", photo_field + ".src", "정적 실적 사진 한 프레임만 허용합니다.")
                    scan_text(details["textMetadata"], photo_field + ".metadata")
                    scan_text(details["exifText"], photo_field + ".metadata")
            except Exception as error:
                issue("photo_file", photo_field + ".src", str(error))
    return {"passed": not issues, "projectCount": len(projects), "photoCount": photo_count,
            "uniquePhotoCount": len(assets), "datePrecision": precision, "issues": issues,
            "imageTextLimit": "이미지 픽셀 속 글자의 OCR 검사는 수행하지 않습니다. 공개승인 시 별도 확인하세요."}


class PortfolioReview:
    def __init__(self, root: Path = SITE_ROOT):
        self.root = root.resolve()
        self.public_json = self.root / "assets" / "projects.json"
        self.private = self.root / "_개발준비" / "portfolio-review"

    def baseline(self):
        public_source_path(self.public_json, self.root, subtree="assets")
        data = load_json(self.public_json)
        report = validate_data(data, self.root)
        if not report["passed"]:
            raise ReviewError("현재 공개 자료 검증 실패: " + json.dumps(report["issues"], ensure_ascii=False))
        return data, sha256(self.public_json)

    def output_dir(self, output: Path | None, kind: str, *, inputs=(), sources=()) -> Path:
        path = output or self.private / timestamp_name(kind)
        path = protected_output(path, self.root, input_files=[self.public_json, *inputs], source_dirs=sources)
        if path.exists():
            raise ReviewError("기존 출력 폴더를 덮어쓰지 않습니다. 새 경로를 지정하세요.")
        return path

    def validate(self, data_path: Path | None = None, report_path: Path | None = None):
        data_path = public_source_path(data_path or self.public_json, self.root)
        data = load_json(data_path)
        report = validate_data(data, self.root)
        report.update(sourceSha256=sha256(data_path), source=str(data_path), actualPublishingPerformed=False)
        destination = report_path or self.private / "reports" / (timestamp_name("validate") + ".json")
        destination = protected_output(destination, self.root, input_files=[data_path])
        write_json_new(destination, report)
        return {**report, "reportPath": str(destination)}

    def draft(self, project: dict[str, Any], photo_sources: list[Path], alts: list[str], output: Path | None = None):
        baseline, baseline_hash = self.baseline()
        identity = project.get("id")
        if not isinstance(identity, str) or not SLUG.fullmatch(identity):
            raise ReviewError("초안 ID는 영문 소문자·숫자·하이픈·밑줄이어야 합니다.")
        if any(p["id"] == identity for p in baseline["projects"]):
            raise ReviewError("기존 공개 프로젝트를 대체할 수 없습니다. 신규 ID를 사용하세요.")
        sources = [p.resolve() for p in photo_sources]
        if len(sources) != len(set(sources)):
            raise ReviewError("동일 사진 원본을 중복 가져올 수 없습니다.")
        if len(alts) not in {0, len(sources)}:
            raise ReviewError("--alt는 사진마다 하나씩 입력하거나 생략하세요.")
        destination = self.output_dir(output, identity, inputs=sources, sources=[p.parent for p in sources])
        destination.mkdir(parents=True)
        imports = []
        photos = []
        for index, source in enumerate(sources, 1):
            before = sha256(source)
            relative = f"assets/projects/{identity}-{index:02}.jpg"
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as original:
                original.load()
                oriented = ImageOps.exif_transpose(original).convert("RGB")
                oriented.thumbnail((1800, 1800))
                clean = Image.new("RGB", oriented.size)
                clean.paste(oriented)
                with target.open("xb") as handle:
                    clean.save(handle, format="JPEG", quality=90, optimize=True, progressive=True)
            if before != sha256(source):
                raise ReviewError("가져오는 중 입력 사진 원본이 변경되었습니다.")
            details = image_details(target)
            if details["gps"] or details["exifPresent"] or details["textMetadata"]:
                raise ReviewError("정제 사본에 메타데이터가 남았습니다.")
            photos.append({"src": relative, "alt": alts[index - 1] if alts else "확인필요"})
            imports.append({"source": str(source), "sourceSha256": before, "sanitized": relative, "sanitizedSha256": sha256(target)})
        project = copy.deepcopy(project)
        project.update(cover=photos[0] if photos else {"src": "", "alt": "확인필요"}, gallery=photos[1:])
        document = {"schemaVersion": 1, "kind": "private-portfolio-draft", "baseSha256": baseline_hash, "project": project}
        write_json_new(destination / "draft.json", document)
        write_json_new(destination / "imports.json", {"schemaVersion": 1, "files": imports})
        subject = self.subject(document, destination)
        approval = {"schemaVersion": 1, "projectId": identity, "subjectSha256": subject,
                    **{flag: False for flag in APPROVAL_FLAGS}, **{field: "확인필요" for field in APPROVAL_EVIDENCE}}
        write_json_new(destination / "review.json", approval)
        (destination / "검토안내.txt").write_text("비공개 초안입니다. 수행범위·사진 사용권·공개승인을 근거와 함께 확인하세요.\n이미지 속 전화·메일·금액·문서·미성년자 등의 공개 적합성은 사람이 확인해야 합니다.\nreview.json의 세 항목은 기본 false이며 도구가 자동 승인하지 않습니다.\n초안이나 사진을 바꾸면 subjectSha256가 달라져 기존 승인은 사용할 수 없습니다.\n", encoding="utf-8-sig")
        return {"draftPath": str(destination / "draft.json"), "reviewPath": str(destination / "review.json"), "photoImports": len(imports), "approvals": {flag: False for flag in APPROVAL_FLAGS}, "originalsModified": False}

    def read_draft(self, draft_path: Path):
        draft_path = draft_path / "draft.json" if draft_path.is_dir() else draft_path
        draft_path = draft_path.resolve()
        document = load_json(draft_path)
        if not isinstance(document, dict) or set(document) != DRAFT_KEYS or document.get("schemaVersion") != 1 or document.get("kind") != "private-portfolio-draft" or not isinstance(document.get("project"), dict):
            raise ReviewError("지원하지 않는 비공개 초안 구조입니다.")
        return document, draft_path.parent, draft_path

    def subject(self, document, workspace):
        project = document["project"]
        photos = [project.get("cover"), *project.get("gallery", [])]
        hashes = []
        for photo in photos:
            if not isinstance(photo, dict) or not photo.get("src"):
                continue
            path = public_photo_path(workspace, photo["src"])
            hashes.append({"src": photo["src"], "sha256": sha256(path)})
        return canonical_digest({"document": document, "photos": hashes})

    def candidate(self, document):
        baseline, baseline_hash = self.baseline()
        if baseline_hash != document["baseSha256"]:
            raise ReviewError("초안을 만든 뒤 공개 JSON이 변경되었습니다. 최신 원본으로 다시 검토하세요.")
        project = document["project"]
        if any(p["id"] == project.get("id") for p in baseline["projects"]):
            raise ReviewError("기존 공개 ID를 수정·대체할 수 없습니다.")
        result = copy.deepcopy(baseline)
        result["projects"].append(copy.deepcopy(project))
        return result

    def check_approval(self, approval_path, document, workspace):
        approval = load_json(approval_path)
        if not isinstance(approval, dict) or set(approval) != APPROVAL_KEYS or type(approval.get("schemaVersion")) is not int or approval["schemaVersion"] != 1:
            raise ReviewError("승인 명세서의 허용키·구조가 일치하지 않습니다.")
        if approval.get("projectId") != document["project"].get("id") or approval.get("subjectSha256") != self.subject(document, workspace):
            raise ReviewError("승인 명세서가 현재 초안·사진과 일치하지 않습니다.")
        if any(approval.get(flag) is not True for flag in APPROVAL_FLAGS):
            raise ReviewError("수행범위·사용권·공개승인 세 항목을 모두 명시적으로 true로 확인해야 합니다.")
        for field in APPROVAL_EVIDENCE:
            value = approval.get(field)
            if not isinstance(value, str) or not value.strip() or PLACEHOLDER.search(value):
                raise ReviewError("승인 근거가 비어 있거나 확인 필요 상태입니다: " + field)
        return approval

    def copy_site(self, destination, data, workspace):
        """Copy only public static resources; never copy review/private directories."""
        destination.mkdir(parents=True)
        for name in ("index.html", "404.html", "site.webmanifest", "robots.txt", "sitemap.xml", ".nojekyll"):
            source = self.root / name
            if source.exists() or source.is_symlink():
                public_source_path(source, self.root)
                shutil.copyfile(source, destination / name)
        asset_root = self.root / "assets"
        public_source_path(asset_root, self.root, subtree="assets", directory=True)
        for folder, subdirs, filenames in os.walk(asset_root, topdown=True, followlinks=False):
            folder = Path(folder)
            public_source_path(folder, self.root, subtree="assets", directory=True)
            for name in subdirs:
                public_source_path(folder / name, self.root, subtree="assets", directory=True)
            # Portfolio photos are copied from the validated JSON references only.
            if folder == asset_root and "projects" in subdirs:
                subdirs.remove("projects")
            for name in filenames:
                source = folder / name
                relative = source.relative_to(self.root)
                if relative.as_posix() == "assets/projects.json" or source.suffix.lower() not in STATIC_EXTENSIONS:
                    continue
                public_source_path(source, self.root, subtree="assets")
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        for project in data["projects"]:
            for photo in [project["cover"], *project["gallery"]]:
                relative = photo["src"]
                origin = workspace if project["id"] == data["projects"][-1]["id"] else self.root
                source = public_photo_path(origin, relative)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and sha256(source) != sha256(target):
                    raise ReviewError("준비 사본에 서로 다른 동명 사진이 있습니다.")
                if not target.exists():
                    shutil.copyfile(source, target)
        write_json_new(destination / "assets" / "projects.json", data)

    def bundle(self, draft_path: Path, output: Path | None = None, *, prepare=False, approval_path: Path | None = None):
        document, workspace, draft_file = self.read_draft(draft_path)
        data = self.candidate(document)
        source_photos = [public_photo_path(workspace, p.get("src")) for p in [document["project"].get("cover"), *document["project"].get("gallery", [])] if isinstance(p, dict)]
        frozen_subject = self.subject(document, workspace)
        approval_file = (approval_path or workspace / "review.json").resolve()
        approval = self.check_approval(approval_file, document, workspace) if prepare else None
        destination = self.output_dir(output, "prepare" if prepare else "preview", inputs=[draft_file, approval_file, *source_photos], sources=[p.parent for p in source_photos])
        # Validate the new record before copying the public site snapshot.
        new_report = validate_data({"schemaVersion": 1, "replaceExisting": True, "projects": [document["project"]]}, workspace)
        if not new_report["passed"]:
            raise ReviewError("초안 검증 실패: " + json.dumps(new_report["issues"], ensure_ascii=False))
        self.copy_site(destination / "site", data, workspace)
        report = validate_data(load_json(destination / "site" / "assets" / "projects.json"), destination / "site")
        if not report["passed"]:
            raise ReviewError("준비 사본 검증 실패: " + json.dumps(report["issues"], ensure_ascii=False))
        if (self.subject(document, destination / "site") != frozen_subject or
                self.subject(document, workspace) != frozen_subject or
                sha256(self.public_json) != document["baseSha256"]):
            raise ReviewError("사본 준비 중 검토 대상 또는 공개 원본이 변경되었습니다. 새로 검토하세요.")
        report.update(actualPublishingPerformed=False, approvalRequired=prepare, approvalsConfirmed=bool(approval), baselineRecordsPreserved=True)
        write_json_new(destination / "validation.json", report)
        info = {"kind": "deployment-preparation" if prepare else "private-preview", "siteDirectory": str(destination / "site"), "projectCount": report["projectCount"], "photoCount": report["photoCount"], "subjectSha256": frozen_subject, "published": False}
        if not prepare:
            approval_template = {"schemaVersion": 1, "projectId": document["project"]["id"],
                                 "subjectSha256": info["subjectSha256"],
                                 **{flag: False for flag in APPROVAL_FLAGS},
                                 **{field: "확인필요" for field in APPROVAL_EVIDENCE}}
            write_json_new(destination / "review-template.json", approval_template)
            info["approvalTemplate"] = str(destination / "review-template.json")
        if prepare:
            zip_path = destination / "deployment-site.zip"
            with zipfile.ZipFile(zip_path, "x", zipfile.ZIP_DEFLATED) as archive:
                for source in sorted((destination / "site").rglob("*")):
                    if source.is_file():
                        archive.write(source, source.relative_to(destination / "site").as_posix())
            info.update(deploymentArchive=str(zip_path), archiveSha256=sha256(zip_path))
            write_json_new(destination / "approval-summary.json", {"projectId": approval["projectId"], "subjectSha256": approval["subjectSha256"], **{key: True for key in APPROVAL_FLAGS}})
        write_json_new(destination / "manifest.json", info)
        (destination / "비공개_미리보기_안내.txt").write_text("이 폴더는 비공개 검토용 사본입니다. 자동 공개·업로드·Git 적용은 하지 않았습니다.\nfile:// 직접 열기 대신 HTTP 미리보기 서버로 site 폴더를 제공하세요.\n예: python -m http.server 8765 --bind 127.0.0.1 --directory site\n검토 완료 전 공개 서비스로 올리지 마세요. 배포 대상으로 준비한 파일은 site/ 또는 deployment-site.zip만입니다.\n", encoding="utf-8-sig")
        return info


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=SITE_ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="공개 JSON과 모든 참조 사진 읽기 검증")
    validate.add_argument("--json", type=Path)
    validate.add_argument("--report", type=Path)
    draft = commands.add_parser("draft", help="기본 미승인 비공개 초안·메타데이터 제거 사본 생성")
    draft.add_argument("--id", required=True)
    for name in ("title", "category", "role"):
        draft.add_argument("--" + name, default="확인필요")
    draft.add_argument("--location", default="")
    draft.add_argument("--start-date")
    draft.add_argument("--end-date")
    draft.add_argument("--year", type=int)
    draft.add_argument("--month", type=int)
    draft.add_argument("--photo", type=Path, action="append", default=[])
    draft.add_argument("--alt", action="append", default=[])
    draft.add_argument("--output", type=Path)
    for name in ("preview", "prepare"):
        command = commands.add_parser(name, help="비공개 사본" if name == "preview" else "승인된 배포 준비 묶음(적용·업로드 없음)")
        command.add_argument("--draft", type=Path, required=True)
        command.add_argument("--output", type=Path)
        if name == "prepare":
            command.add_argument("--approval", type=Path)
    args = parser.parse_args(argv)
    tool = PortfolioReview(args.site_root)
    try:
        if args.command == "validate":
            result = tool.validate(args.json, args.report)
        elif args.command == "draft":
            project = {"id": args.id, "title": args.title, "category": args.category, "role": args.role, "location": args.location}
            if args.start_date:
                if args.year is not None or args.month is not None:
                    raise ReviewError("--start-date와 --year/--month를 혼용할 수 없습니다.")
                project["startDate"] = args.start_date
                if args.end_date:
                    project["endDate"] = args.end_date
            else:
                if args.end_date or (args.month and args.year is None):
                    raise ReviewError("종료일은 시작일, 월은 연도와 함께 입력하세요.")
                project["year"] = args.year
                if args.month is not None:
                    project["month"] = args.month
            result = tool.draft(project, args.photo, args.alt, args.output)
        else:
            result = tool.bundle(args.draft, args.output, prepare=args.command == "prepare", approval_path=getattr(args, "approval", None))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("passed", True) else 2
    except (ReviewError, OSError, ValueError, Image.DecompressionBombError) as error:
        print(json.dumps({"passed": False, "error": str(error), "published": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
