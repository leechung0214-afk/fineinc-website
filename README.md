# FINE INC. 회사 홈페이지

공개 홈페이지: https://leechung0214-afk.github.io/fineinc-website/

이 저장소의 `main` 브랜치를 기존 GitHub Pages로 배포합니다. 새 저장소나 별도 호스팅을 만들 필요가 없습니다. 2026-11-07 보완 작업의 기존 공개 자료 기준은 행사 47건·사진 122장입니다. 실제 화면의 건수는 로딩에 성공한 JSON과 현재 검색·필터 결과에서 계산합니다.

## 파일과 공개 자료

| 파일 | 역할 |
| --- | --- |
| `index.html` | 홈페이지 내용과 실적·문의 화면 |
| `assets/projects.json` | 공개 확인된 행사명·일자·분류·수행업무·장소·사진 목록 |
| `assets/projects/` | 메타데이터를 정리한 공개용 사진 사본 |
| `assets/projects.js`, `assets/projects.css` | 실적 로딩·검색·필터·사진 갤러리 |
| `assets/contact-mailto.js` | 문의 메일 초안과 문의 내용 복사 |
| `assets/brand-theme.css` | 기존 FINE 공통 디자인과 모바일 보정 |
| `scripts/portfolio_review.py` | 공개 전 자료·사진 검증과 비공개 검토 사본 준비 |

`_개발준비/`, `tests/_artifacts/`, 원본 사진, 승인 근거와 내부 운영 기록은 공개 커밋 대상이 아닙니다. 폴더 전체를 통째로 업로드하지 마세요. 기존 행사 ID와 확인된 날짜 정밀도(일자·월·연도)를 보존합니다.

## 실적 화면 동작

첫 화면은 로딩 상태를 표시하며, 자료를 확인하기 전에는 카드나 건수를 표시하지 않습니다. 네트워크·HTTP·JSON·자료 구조 오류가 있으면 실패 안내와 **다시 시도** 버튼을 표시합니다. 이전 장식 카드 4개를 대신 표시하지 않습니다. 정상적인 빈 자료와 검색 결과 0건은 각각 별도로 안내합니다.

성공 후 **실적 목록 확인 완료**에 표시하는 한국시간은 해당 브라우저가 목록을 읽고 검증한 시간입니다. 행사의 최종 수정 시각이나 배포 시각을 뜻하지 않습니다. **목록 다시 확인**으로 다시 읽을 수 있습니다.

행사명·장소·수행업무를 검색하며, 공백으로 나눈 모든 검색어가 포함된 결과를 찾습니다. 연도·분야와 함께 적용할 수 있습니다. 검색은 유니코드 NFKC 정규화와 대소문자 구분 없는 비교를 사용합니다. **조건 초기화**는 모든 검색·필터를 초기화합니다.

주소의 `p_q`(검색), `p_year`(연도), `p_category`(분야)로 현재 결과를 다시 열 수 있습니다. 검색어 입력은 현재 이력을 갱신하고 선택 필터·초기화는 이력을 추가하므로 브라우저 뒤로/앞으로 이동에 따라 복원됩니다. **필터 링크 복사**는 이 필터와 기존 `v` 표시만 공유하며 다른 쿼리는 제외합니다. 자동 복사가 불가능하면 직접 복사할 주소 입력란을 표시합니다.

사진을 누르면 확대 갤러리가 열립니다. 이전·다음, 썸네일, 좌우 방향키와 닫기를 지원합니다. 닫으면 열었던 버튼으로 키보드 초점이 돌아갑니다. 모바일에서는 사진 전체가 보이는 방식으로 확대하며, 실제 휴대폰 조작 확인은 브라우저 화면 폭 검사와 구분합니다.

## 새 실적 추가

[실적 추가 검토 절차](docs/portfolio-review.txt)를 따릅니다. Python 3.10 이상과 Pillow가 필요합니다.

```powershell
python scripts/portfolio_review.py validate
python scripts/portfolio_review.py draft --id new-show-2026 --title "행사명" --year 2026 --category "공연" --role "음향 운영" --photo "원본사진.jpg" --alt "행사 무대와 객석"
python scripts/portfolio_review.py preview --draft "작업폴더/draft.json"
python scripts/portfolio_review.py prepare --draft "작업폴더/draft.json"
```

`draft`는 원본을 읽어 방향·크기를 보정하고 GPS 등 메타데이터를 제거한 공개용 사본을 비공개 작업 폴더에 만듭니다. 원본의 전후 해시를 확인합니다. `preview`는 운영 파일과 분리된 미리보기 사본을 만듭니다. `prepare`는 수행범위·사진 사용권·공개승인 세 항목의 실제 근거와 승인이 있어야 배포 준비 묶음을 만듭니다. 변경 후에는 다시 검토해야 합니다. 도구는 Git 저장소를 수정하거나 배포하지 않습니다.

자동 검사는 사진 픽셀 속 글자, 인물의 공개 동의나 계약상 사용권을 판단하지 않습니다. 새 행사·사진은 사람이 내용과 권리를 확인한 후 별도 공개합니다. 기존 공개 자료 교체·수정은 이 신규 추가 도구의 대상이 아닙니다.

## 문의

문의 화면의 **메일 초안 작성**은 사용자의 메일 앱에 초안을 만들고, **문의 내용 복사**는 입력한 내용을 복사합니다. 실제 전송은 사용자가 메일 앱에서 수행합니다. 홈페이지가 자동으로 접수하거나 메일 서버로 전송하는 기능은 없습니다. 이 동작은 이미 구현돼 있습니다.

## 로컬 미리보기와 검사

프로젝트 폴더에서 HTTP 서버로 확인합니다. `file://`로 직접 열면 JSON을 읽을 수 없으므로 브라우저 보안을 변경하지 말고 HTTP 또는 공개 주소를 사용합니다.

```powershell
python -m http.server 8876 --bind 127.0.0.1 --directory .
node --check assets/projects.js
node tests/test-projects.cjs
python -m unittest discover -s tests -p test_portfolio_review.py -v
python scripts/portfolio_review.py validate
git diff --check
```

`python`이 Windows 별칭으로 연결된 PC에서는 설치된 Python 실행 파일의 절대 경로를 사용합니다. 이 PC의 확인된 경로는 `C:\Users\rcman\AppData\Local\Programs\Python\Python313\python.exe`입니다.

`tests/portfolio_preview_server.py`는 격리된 로컬 QA에서 정상·오류·빈 자료를 시험하는 서버입니다. 테스트는 운영 `projects.json`을 덮어쓰지 않으며 결과는 `tests/_artifacts/`에 둡니다.

## 기존 공개 배포 갱신

필요한 변경 파일만 검토해 `main`에 커밋·push하고 기존 Pages 빌드가 성공하는지 확인합니다. 공개 주소에서 변경된 검색·오류 상태·갤러리를 점검하고, 공개 JSON 및 사진이 의도한 자료와 일치하는지 확인합니다. 로컬 검사, Pages 배포, 공개 화면 확인, 실제 휴대폰 점검을 각각 기록합니다.
