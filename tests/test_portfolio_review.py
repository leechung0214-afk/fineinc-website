"""Isolated review-tool regressions; fixtures stay in tests/_artifacts."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
import zipfile

from PIL import Image


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("portfolio_review", ROOT / "scripts" / "portfolio_review.py")
review = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = review
spec.loader.exec_module(review)
ARTIFACTS = ROOT / "tests" / "_artifacts" / "20261107_portfolio" / "tooling"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class PortfolioReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = ARTIFACTS / "fixtures" / (self._testMethodName + "-" + uuid.uuid4().hex[:8])
        self.root = self.directory / "site"
        (self.root / "assets" / "projects").mkdir(parents=True)
        Image.new("RGB", (32, 24), "navy").save(self.root / "assets" / "projects" / "baseline.jpg")
        self.base_project = {"id": "baseline", "title": "확정 공연", "year": 2020,
                             "category": "공연", "role": "음향 운영", "location": "광주",
                             "cover": {"src": "assets/projects/baseline.jpg", "alt": "확정 공연 무대"}, "gallery": []}
        self.data = {"schemaVersion": 1, "replaceExisting": True, "projects": [self.base_project]}
        write(self.root / "assets" / "projects.json", self.data)
        (self.root / "index.html").write_text("<!doctype html><title>격리 사본</title>", encoding="utf-8")
        self.tool = review.PortfolioReview(self.root)
        self.raw = self.directory / "originals"
        self.raw.mkdir()
        self.photo = self.raw / "original.jpg"
        Image.new("RGB", (40, 30), "blue").save(self.photo)

    def project(self, **changes):
        project = {"id": "new-show", "title": "추가 확정 공연", "year": 2020,
                   "category": "공연", "role": "음향 운영", "location": "광주"}
        project.update(changes)
        return project

    def create_draft(self, project=None, photo=None):
        output = self.root / "_개발준비" / "draft"
        result = self.tool.draft(project or self.project(), [photo or self.photo], ["추가 공연 무대"], output)
        return Path(result["draftPath"]), Path(result["reviewPath"])

    def approve(self, path):
        data = review.load_json(path)
        data.update({key: True for key in review.APPROVAL_FLAGS})
        data.update(scopeEvidence="계약 수행범위 대조 완료", rightsEvidence="촬영·사용권 확인 완료", publicationEvidence="담당자 공개 승인 확인 완료")
        write(path, data)

    def codes(self, data):
        return {r["code"] for r in review.validate_data(data, self.root)["issues"]}

    def directory_alias(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
            if result.returncode:
                self.skipTest("fixture link/junction creation unavailable")

    def test_live_public_portfolio_remains_valid_47_122(self):
        public_path = ROOT / "assets" / "projects.json"
        before = review.sha256(public_path)
        report = review.validate_data(review.load_json(public_path), ROOT)
        self.assertTrue(report["passed"], report["issues"])
        self.assertEqual((report["projectCount"], report["photoCount"]), (47, 122))
        self.assertEqual(before, review.sha256(public_path))

    def test_duplicate_ids_schema_types_and_hidden_text_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["projects"].append(copy.deepcopy(self.base_project))
        self.assertIn("duplicate_id", self.codes(bad))
        bad = copy.deepcopy(self.data)
        bad["replaceExisting"] = 1
        bad["projects"][0]["cover"]["privateNote"] = {"other": ["전화 010-1234-5678, mail@example.com, 5만원, C:\\Users\\private"]}
        self.assertTrue({"unknown_key", "boolean_type", "phone_exposure", "email_exposure", "money_exposure", "internal_path"} <= self.codes(bad))
        bad["projects"][0]["role"] = ["음향"]
        self.assertIn("text_type", self.codes(bad))

    def test_unicode_phone_and_money_in_caption_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["projects"][0]["cover"]["alt"] = "문의 +82–10–1234–5678 / 대금 ５만원입니다"
        self.assertTrue({"phone_exposure", "money_exposure"} <= self.codes(bad))

    def test_frontend_replace_existing_and_text_length_contract(self):
        bad = copy.deepcopy(self.data)
        bad["replaceExisting"] = False
        self.assertIn("replace_existing", self.codes(bad))
        for field, limit in review.TEXT_LIMITS.items():
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.data)
                target = candidate["projects"][0]["cover"] if field == "alt" else candidate["projects"][0]
                target[field] = "가" * limit
                self.assertTrue(review.validate_data(candidate, self.root)["passed"])
                target[field] += "가"
                self.assertIn("text_length", self.codes(candidate))
        candidate = copy.deepcopy(self.data)
        candidate["projects"][0]["title"] = "🎵" * 150
        self.assertTrue(review.validate_data(candidate, self.root)["passed"])
        candidate["projects"][0]["title"] += "🎵"
        self.assertIn("text_length", self.codes(candidate))

    def test_day_month_year_precision_and_invalid_dates(self):
        day = copy.deepcopy(self.data)
        project = day["projects"][0]
        project.pop("year")
        project.update(startDate="2020-02-29", endDate="2020-03-01")
        self.assertTrue(review.validate_data(day, self.root)["passed"])
        project["startDate"] = "2020-02-30"
        self.assertIn("invalid_date", self.codes(day))
        project["startDate"], project["endDate"] = "2020-03-02", "2020-03-01"
        self.assertIn("date_order", self.codes(day))
        project["year"] = 2020
        self.assertIn("mixed_precision", self.codes(day))
        coarse = copy.deepcopy(self.data)
        coarse["projects"][0]["month"] = 7
        self.assertTrue(review.validate_data(coarse, self.root)["passed"])
        coarse["projects"][0]["month"] = 13
        self.assertIn("month", self.codes(coarse))
        coarse["projects"][0]["month"] = True
        self.assertIn("month", self.codes(coarse))

    def test_missing_broken_absolute_and_traversing_photos(self):
        for source in ("assets/projects/missing.jpg", "../../outside.jpg", "C:/private/photo.jpg", "https://example.com/photo.jpg",
                       "assets/projects/./baseline.jpg", "assets/projects//baseline.jpg"):
            bad = copy.deepcopy(self.data)
            bad["projects"][0]["cover"]["src"] = source
            self.assertIn("photo_file", self.codes(bad), source)
        (self.root / "assets" / "projects" / "baseline.jpg").write_bytes(b"broken picture")
        self.assertIn("photo_file", self.codes(self.data))

    def test_symlink_or_junction_escape_rejected(self):
        external = self.directory / "outside-images"
        external.mkdir()
        Image.new("RGB", (12, 12), "red").save(external / "escaped.jpg")
        link = self.root / "assets" / "projects" / "escape"
        self.directory_alias(link, external)
        bad = copy.deepcopy(self.data)
        bad["projects"][0]["cover"]["src"] = "assets/projects/escape/escaped.jpg"
        self.assertIn("photo_file", self.codes(bad))
        with self.assertRaises(review.ReviewError):
            review.protected_output(link / "new.json", self.root)

    def test_private_junction_cannot_enter_preview_or_prepared_zip(self):
        draft, approval = self.create_draft()
        self.approve(approval)
        private = self.root / "_개발준비" / "private-export"
        write(private / "imports.json", {"fixturePrivateSentinel": "must stay private"})
        original_hash = review.sha256(private / "imports.json")
        self.directory_alias(self.root / "assets" / "private-export", private)
        for prepare in (False, True):
            with self.subTest(prepare=prepare):
                output = self.root / "_개발준비" / ("blocked-link-" + str(prepare))
                with self.assertRaisesRegex(review.ReviewError, "symlink|junction"):
                    self.tool.bundle(draft, output, prepare=prepare)
                self.assertFalse((output / "deployment-site.zip").exists())
                self.assertFalse((output / "site" / "assets" / "private-export" / "imports.json").exists())
        self.assertEqual(original_hash, review.sha256(private / "imports.json"))

    def test_hardlinked_private_asset_cannot_enter_preview_or_prepared_zip(self):
        draft, approval = self.create_draft()
        self.approve(approval)
        private = self.root / "_개발준비" / "imports.json"
        write(private, {"fixturePrivateSentinel": "must stay private"})
        original_hash = review.sha256(private)
        os.link(private, self.root / "assets" / "private-alias.json")
        self.assertGreater(private.stat().st_nlink, 1)
        for prepare in (False, True):
            with self.subTest(prepare=prepare):
                output = self.root / "_개발준비" / ("blocked-hardlink-" + str(prepare))
                with self.assertRaisesRegex(review.ReviewError, "hardlink"):
                    self.tool.bundle(draft, output, prepare=prepare)
                self.assertFalse((output / "deployment-site.zip").exists())
                self.assertFalse((output / "site" / "assets" / "private-alias.json").exists())
        self.assertEqual(original_hash, review.sha256(private))

    def test_hardlinked_photos_and_baseline_json_rejected(self):
        os.link(self.photo, self.root / "assets" / "projects" / "private-alias.jpg")
        bad = copy.deepcopy(self.data)
        bad["projects"][0]["cover"]["src"] = "assets/projects/private-alias.jpg"
        self.assertIn("photo_file", self.codes(bad))
        private = self.root / "_개발준비"
        private.mkdir()
        os.link(self.tool.public_json, private / "public-json-alias.json")
        with self.assertRaisesRegex(review.ReviewError, "hardlink"):
            self.tool.baseline()

    def test_gps_import_removes_metadata_and_preserves_original_hash(self):
        exif = Image.Exif()
        exif[270] = "private original 010-1234-5678"
        exif[274] = 6
        exif[34853] = {1: "N", 2: (37.0, 30.0, 0.0), 3: "E", 4: (127.0, 0.0, 0.0)}
        Image.new("RGB", (40, 30), "green").save(self.photo, exif=exif)
        original_hash = review.sha256(self.photo)
        (self.root / "assets" / "projects" / "baseline.jpg").write_bytes(self.photo.read_bytes())
        self.assertIn("gps_metadata", self.codes(self.data))
        Image.new("RGB", (32, 24), "navy").save(self.root / "assets" / "projects" / "baseline.jpg")
        draft, approval = self.create_draft()
        sanitized = draft.parent / "assets" / "projects" / "new-show-01.jpg"
        details = review.image_details(sanitized)
        self.assertFalse(details["gps"] or details["exifPresent"] or details["textMetadata"])
        self.assertEqual((details["width"], details["height"]), (30, 40))
        self.assertEqual(original_hash, review.sha256(self.photo))
        self.assertTrue(all(review.load_json(approval)[key] is False for key in review.APPROVAL_FLAGS))

    def test_xmp_gps_and_text_metadata_detected(self):
        from PIL.PngImagePlugin import PngInfo
        metadata = PngInfo()
        metadata.add_text("XML:com.adobe.xmp", '<gps:GPSLatitude>37.5</gps:GPSLatitude>')
        target = self.root / "assets" / "projects" / "meta.png"
        Image.new("RGB", (16, 16), "blue").save(target, pnginfo=metadata)
        bad = copy.deepcopy(self.data)
        bad["projects"][0]["cover"]["src"] = "assets/projects/meta.png"
        self.assertTrue({"gps_metadata", "image_metadata"} <= self.codes(bad))

    def test_unapproved_prepare_and_placeholder_evidence_blocked(self):
        draft, approval = self.create_draft()
        output = self.root / "_개발준비" / "blocked"
        with self.assertRaises(review.ReviewError):
            self.tool.bundle(draft, output, prepare=True)
        self.assertFalse(output.exists())
        values = review.load_json(approval)
        values.update({key: True for key in review.APPROVAL_FLAGS})
        write(approval, values)
        with self.assertRaises(review.ReviewError):
            self.tool.bundle(draft, output, prepare=True)
        self.assertFalse(output.exists())
        self.approve(approval)
        values = review.load_json(approval)
        values["publicationApproved"] = "true"
        write(approval, values)
        with self.assertRaises(review.ReviewError):
            self.tool.bundle(draft, output, prepare=True)

    def test_preview_and_preparation_preserve_baseline_and_exclude_private_files(self):
        baseline_hash = review.sha256(self.tool.public_json)
        source_hash = review.sha256(self.photo)
        draft, approval = self.create_draft()
        preview = self.tool.bundle(draft, self.root / "_개발준비" / "preview")
        self.assertEqual(preview["projectCount"], 2)
        self.assertFalse(preview["published"])
        self.assertTrue(all(review.load_json(Path(preview["approvalTemplate"]))[key] is False for key in review.APPROVAL_FLAGS))
        self.assertFalse(review.load_json(approval)["publicationApproved"])
        self.approve(approval)
        prepared = self.tool.bundle(draft, self.root / "_개발준비" / "prepared", prepare=True)
        package = Path(prepared["siteDirectory"])
        candidate = review.load_json(package / "assets" / "projects.json")
        self.assertEqual(candidate["projects"][0], self.base_project)
        self.assertTrue(review.validate_data(candidate, package)["passed"])
        with zipfile.ZipFile(prepared["deploymentArchive"]) as archive:
            self.assertIn("assets/projects.json", archive.namelist())
            self.assertFalse(any("review.json" in name or "imports.json" in name or "draft.json" in name or "_개발준비" in name for name in archive.namelist()))
        self.assertEqual(baseline_hash, review.sha256(self.tool.public_json))
        self.assertEqual(source_hash, review.sha256(self.photo))

    def test_changed_draft_or_photos_cannot_reuse_approval(self):
        draft, approval = self.create_draft()
        self.approve(approval)
        value = review.load_json(draft)
        value["project"]["title"] = "변경한 공연"
        write(draft, value)
        with self.assertRaises(review.ReviewError):
            self.tool.bundle(draft, self.root / "_개발준비" / "stale", prepare=True)
        value["project"]["title"] = "추가 확정 공연"
        write(draft, value)
        Image.new("RGB", (40, 30), "red").save(draft.parent / "assets" / "projects" / "new-show-01.jpg")
        with self.assertRaises(review.ReviewError):
            self.tool.bundle(draft, self.root / "_개발준비" / "changed-photo", prepare=True)

    def test_confirmed_flags_do_not_approve_unconfirmed_project_text(self):
        draft, approval = self.create_draft(self.project(title="확인필요"))
        self.approve(approval)
        with self.assertRaisesRegex(review.ReviewError, "unconfirmed_text"):
            self.tool.bundle(draft, self.root / "_개발준비" / "unconfirmed", prepare=True)

    def test_output_cannot_touch_public_repository_or_photo_inputs(self):
        for path in [self.root / "assets" / "new", self.root / "index.html", ROOT / "assets" / "new-review", self.raw / "output", self.directory]:
            with self.assertRaises(review.ReviewError, msg=str(path)):
                self.tool.draft(self.project(), [self.photo], ["공연 사진"], path)
        with self.assertRaises(review.ReviewError):
            self.tool.validate(report_path=self.tool.public_json)
        self.assertTrue(self.photo.is_file())

    def test_existing_ids_outputs_and_duplicate_json_keys_rejected(self):
        with self.assertRaises(review.ReviewError):
            self.tool.draft(self.project(id="baseline"), [self.photo], ["사진"])
        self.create_draft()
        with self.assertRaises(review.ReviewError):
            self.create_draft()
        path = self.root / "_개발준비" / "duplicate.json"
        path.write_text('{"schemaVersion":1,"schemaVersion":2}', encoding="utf-8")
        with self.assertRaises(review.ReviewError):
            review.load_json(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
