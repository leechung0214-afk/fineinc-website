# FINE INC. 홈페이지 운영 안내

주식회사 파인아이엔씨의 GitHub Pages 정적 홈페이지입니다.

- 홈페이지: https://leechung0214-afk.github.io/fineinc-website/
- 저장소: https://github.com/leechung0214-afk/fineinc-website
- 배포 전후 확인: [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)

## 현재 구현 상태

2026-11-06 코드·데이터 기준으로 행사 실적 **47건**, 행사 사진 **122장**, 보유 장비 **39종(음향 35종·LED 영상 4종)**이 등록되어 있습니다. 사진 수는 각 행사의 대표 사진과 추가 사진을 합산한 값이며, 같은 행사 안의 동일 경로는 중복 표시하지 않습니다. 이 숫자는 고정 목표가 아니라 확인 당시의 스냅샷입니다.

- 행사 목록: 최신 날짜순 정렬, 연도·행사 유형 필터, 결과 건수·사진 수, 결과 없음 안내
- 사진 상세보기: 대표 사진·추가 사진, 썸네일, 이전/다음, 좌우 방향키, 닫기·Esc
- 현재 별도의 키워드 검색창은 없습니다. 연도·유형 필터로 실적을 찾습니다.
- 장비: 음향 분류별 접기·펼치기, LED 규격·해상도·보유 수량, 제품 참고 사진 크게 보기
- 문의: 회사 이메일을 받는 사람으로 지정한 **메일 초안 작성**과 내용 복사. 서버 자동 발송이나 접수 완료 확인 기능은 없습니다.

## 무엇을 바꾸면 어떤 파일을 수정하나요?

| 작업 | 수정할 파일 | 반영 방법 |
| --- | --- | --- |
| 행사명·날짜·장소·수행 역할·유형 | `assets/projects.json` | 기존 행사 객체 수정 또는 새 객체 추가 |
| 행사 사진 추가·교체 | `assets/projects/` + `assets/projects.json` | 이미지 업로드 후 `cover`·`gallery` 경로 수정 |
| 장비명·모델·보유 수량·LED 규격 | `assets/equipment.json` + 생성된 `index.html` | JSON 수정 후 장비 생성 스크립트 실행 |
| 장비 참고 사진 | `assets/equipment/` + `assets/equipment.json` + 생성된 `index.html` | 이미지·`photo` 수정 후 스크립트 실행 |
| 회사 소개·일반 문구·연락처 | `index.html` | 해당 HTML 수정; 장비 생성 영역은 아래 절차 사용 |
| 문의 수신 이메일·초안 처리 | `assets/contact-mailto.js` | `RECIPIENT` 등 수정; `index.html`의 표시 이메일·메일 링크도 함께 확인 |
| 디자인 | `assets/style.css`, `assets/brand-theme.css`, `assets/projects.css`, `assets/equipment.css` | 해당 영역 스타일 수정 |
| 메뉴·스크롤 / 행사 표시 동작 | `assets/script.js` / `assets/projects.js` | 기능을 바꿀 때만 수정 |

## 행사 실적과 사진 추가·수정

1. 새 사진을 `assets/projects/`에 넣습니다. 파일명은 `event-name-2026-01.jpg`처럼 영문·숫자·하이픈을 권장합니다.
2. `assets/projects.json`의 `projects` 배열에서 기존 행사를 수정하거나 객체 하나를 추가합니다. 최상위 `schemaVersion: 1`, `replaceExisting: true`는 유지합니다.
3. 대표 사진은 `cover`, 나머지는 `gallery`에 순서대로 넣습니다. 사진을 폴더에 넣기만 해서는 표시되지 않습니다.
4. JSON과 사진을 같은 브랜치에서 커밋하고 미리보기 후 PR을 만듭니다. 일반적인 행사 추가에는 `index.html` 카드 수정이 필요 없습니다.

다음은 **입력 형식 예시**입니다. 실제 행사 정보와 업로드한 파일 경로로 바꿔 `projects` 배열 안에 넣으세요.

```json
{
  "id": "example-festival-2026",
  "title": "행사명",
  "startDate": "2026-11-06",
  "endDate": "2026-11-07",
  "category": "축제",
  "role": "음향·조명·영상 운영",
  "location": "행사 장소",
  "cover": {
    "src": "assets/projects/example-festival-2026-01.jpg",
    "alt": "행사 무대와 객석 전경",
    "position": "50% 50%"
  },
  "gallery": [
    {
      "src": "assets/projects/example-festival-2026-02.jpg",
      "alt": "야간 공연 조명 전경"
    }
  ]
}
```

| 필드 | 작성 기준 |
| --- | --- |
| `id` | 비어 있지 않은 식별자. 운영상 행사마다 고유하게 유지 |
| `title`, `category` | 비어 있지 않은 행사명·유형. 유형 필터는 데이터에서 자동 생성되므로 표기 통일 |
| `startDate`, `endDate` | `YYYY-MM-DD`. 하루 행사는 같은 날짜 또는 `endDate` 생략. 종료일이 시작일보다 앞서지 않는지 직접 확인 |
| `year`, `month` | 정확한 날짜를 모르면 `startDate`·`endDate`를 빼고 `year: 2026`, 선택적으로 `month: 11` 사용. 월은 정수 1~12. 임의 날짜를 만들지 않음 |
| `role`, `location` | 수행 역할·장소. 확인되지 않은 값은 빈 문자열로 둘 수 있음 |
| `cover.src` | 필수 대표 사진. `assets/projects/`로 시작하는 상대 경로 |
| `cover.alt`, `gallery[].alt` | 사진별 설명. 생략 시 행사명 기반 설명이 표시되지만 구체적인 설명 권장 |
| `cover.position` | 선택 사항. `50% 50%` 같은 백분율 두 값으로 카드 사진의 보이는 위치 조정 |
| `gallery` | 추가 사진 배열. 없으면 `[]`; 대표 사진을 다시 넣을 필요 없음 |

이미지 경로는 영문·숫자·밑줄·점·하이픈·슬래시와 `jpg/jpeg/png/webp` 확장자만 허용합니다. 공백·한글 파일명, 외부 URL, `..` 경로는 허용하지 않습니다. 대소문자를 실제 파일명과 일치시키세요. JSON에는 주석과 마지막 항목 뒤 쉼표를 넣을 수 없습니다.

`assets/projects.js`가 JSON을 읽어 유효한 행사만 최신 날짜순으로 표시합니다. 배열 순서를 바꿔도 날짜 정렬이 우선합니다. 잘못된 행사 객체는 빠질 수 있고, JSON 로딩 실패 시 기존 HTML 실적이 남을 수 있으므로 화면이 보인다는 것만으로 갱신 성공을 판단하지 마세요. 전체 필터 상태의 건수와 새 행사를 확인합니다.

사진 교체는 새 파일 업로드 후 해당 `src`·`alt`를 수정합니다. 사진 삭제는 `gallery` 항목을 제거하고, 대표 사진 삭제 시 먼저 새 `cover`를 지정합니다. 행사 삭제는 해당 객체를 제거합니다. 이미지 파일은 다른 행사에서 참조하지 않는지 확인한 뒤 삭제합니다.

## 보유 장비 관리

장비는 운영 데이터베이스와 자동 동기화되지 않는 **공개용 스냅샷**입니다. `quantity`는 행사일의 대여 가능 수량이 아니라 보유 수량입니다. 자세한 공개 기준은 [design/EQUIPMENT.md](design/EQUIPMENT.md)를 참고하세요.

1. `assets/equipment.json`의 `items`를 추가·수정·삭제하고, 확인일 `asOf`를 `YYYY-MM-DD`로 갱신합니다.
2. 사진이 있으면 `assets/equipment/`에 업로드하고 `photo.src`를 지정합니다.
3. **Python 3.12 이상과 Pillow**가 필요합니다. 저장소 폴더에서 아래 명령을 실행합니다. 현재 스크립트는 Python 3.12의 f-string 문법을 사용합니다.

```bash
python --version
python -m pip install Pillow
python scripts/render-equipment.py
```

4. 생성된 `index.html`의 `<!-- equipment:start -->`와 `<!-- equipment:end -->` 사이 변경을 확인합니다.
5. JSON, 추가·교체한 이미지, **생성된 `index.html`을 함께 커밋**합니다. JSON만 올리면 공개 장비 화면은 바뀌지 않습니다. GitHub Pages가 이 Python 스크립트를 대신 실행하지 않습니다.

| 필드 | 작성 기준 |
| --- | --- |
| `domain` | 현재 렌더러 지원값: 음향 `audio`, LED 영상 `video`. 다른 값은 표시 대상이 아님 |
| `name`, `category`, `brand`, `model` | 장비명·분류·브랜드·모델. 기존 객체 형식을 유지; 음향 목록에는 주로 `name` 표시 |
| `quantity` | 확인한 보유 수량을 숫자로 입력. 렌더러가 0 수량을 자동 제외하지 않으므로 공개 목록 자체를 정리 |
| `led` | 음향은 `null`. 영상은 `widthMm`, `heightMm`, `pixelsWide`, `pixelsHigh`, `panelsPerCase` 숫자 포함 |
| `photo` | 선택 사항. `src`는 실제 로컬 이미지 경로, `caption`은 참고 이미지 설명, `source`는 선택적 출처 URL. 사진이 없으면 필드 생략 또는 `null` |

LED 화면에는 패널 크기·해상도·보유 수량이 표시됩니다. `panelsPerCase`는 데이터에 보관되지만 현재 화면에는 표시하지 않습니다. 이미지 크기를 읽어 HTML에 넣으므로 `photo.src` 파일이 없거나 손상되면 생성이 실패할 수 있습니다.

음향 분류는 현재 콘솔, 메인 스피커, 서브우퍼, 모니터 스피커, 무선 시스템, 무선 인이어 모니터, 퍼스널 모니터, 마이크 스탠드입니다. 새 분류를 추가하거나 기존 분류 전체를 삭제하면 `scripts/render-equipment.py`의 `order`와 실제 분류 집합을 함께 맞춰야 합니다. 불일치하면 검증에서 중단됩니다. 새로운 분야(예: 조명)는 JSON 추가만으로 지원되지 않아 렌더러 수정이 필요합니다.

시리얼·창고 위치·내부 메모·판매 이력·행사 배정·직원 정보는 공개 JSON에 넣지 않습니다. 참고 사진과 실제 보유품 사진을 구분하고 출처·설명을 유지합니다.

## 문의는 메일 초안 작성 방식입니다

`index.html`의 `projectForm`을 `assets/contact-mailto.js`가 처리하며, 현재 받는 사람은 **fine2211@naver.com**입니다.

1. 방문자가 회사/기관명, 담당자, 연락처, 이메일, 프로젝트 유형, 내용을 입력합니다. 프로젝트 내용은 필수이며 최대 5,000자입니다.
2. **메일 초안 작성**을 누르면 `mailto:`로 기기의 메일 앱 열기를 요청합니다. 제목은 `[FINE INC 문의] 유형 / 회사명 또는 담당자`, 본문에는 입력 항목을 넣습니다.
3. 방문자가 메일 앱에서 내용을 확인하고 **직접 전송**해야 합니다. 사이트는 발송 성공이나 회사 수신 여부를 확인하지 않습니다.
4. 인코딩된 `mailto:` 주소 길이가 1,800자를 초과하면 자동 열기를 생략하고 복사할 내용을 표시합니다. 이는 내용 글자 수 제한과 별개인 앱 자체 기준입니다.
5. **문의 내용 복사**로 받는 사람·제목·본문을 복사할 수 있습니다. 클립보드 접근 실패 시 선택 가능한 텍스트가 표시됩니다. **메일 앱 열기**는 받는 사람만 지정한 새 메일을 엽니다.

기본 메일 앱 미설정 등으로 열리지 않을 수 있습니다. 이 경우 내용을 복사해 웹메일이나 메일 앱에서 직접 작성하세요. 코드가 열기 요청을 했다는 안내는 메일 앱이 실제로 열렸거나 전송됐다는 보장이 아닙니다. 별도 메일 발송 API, 서버 저장, 자동 접수·알림은 구현되어 있지 않습니다.

## 수정·미리보기·GitHub Pages 배포

### 수정과 로컬 확인

GitHub 웹에서는 파일의 Edit 또는 Add file → Upload files로 변경하고 **새 브랜치 → PR**로 검토합니다. 장비 변경은 위 생성 작업을 할 수 있는 로컬 환경에서 처리하세요.

로컬에서는 저장소 루트에서 다음을 실행합니다(Python 명령 이름이 `python3`이면 바꿔 사용).

```bash
python -m json.tool assets/projects.json > /dev/null
python -m json.tool assets/equipment.json > /dev/null
python -m http.server 8000
```

`/dev/null`은 macOS/Linux용입니다. Windows에서는 `> /dev/null`을 빼고 실행해도 JSON 문법을 확인할 수 있습니다. 브라우저로 `http://localhost:8000/`을 엽니다. `index.html`을 더블클릭한 `file://`에서는 JSON 불러오기가 제한될 수 있습니다. 확인 후 서버는 Ctrl+C로 종료합니다.

JSON 문법 검사만으로 누락 이미지나 필드 오류가 검증되지는 않습니다. [배포 점검표](DEPLOY_CHECKLIST.md)의 화면 확인까지 수행하세요.

### 배포 설정과 반영 확인

1. 기존 저장소의 **Settings → Pages**에서 배포 소스를 확인합니다. 브랜치 배포 설정은 `Deploy from a branch` / `main` / `/(root)`입니다. 이 안내는 설정 절차이며 현재 관리자 설정을 확인했다는 의미는 아닙니다.
2. `index.html`, `assets/`, `site.webmanifest`, `robots.txt`, `sitemap.xml` 등 저장소 구조를 유지합니다. 별도 압축 폴더 안으로 옮기지 않습니다. 현재 저장소에는 사용자 정의 `.github/workflows` 배포 워크플로와 `.nojekyll` 파일이 없습니다.
3. PR을 검토하여 `main`에 병합하면 위 브랜치 배포 설정에 따라 Pages 배포가 진행됩니다. PR 생성만으로 운영 홈페이지가 갱신되지는 않습니다.
4. **Actions**의 Pages 빌드·배포 결과에서 병합 커밋이 성공했는지 확인합니다. 실패 시 로그를 확인합니다.
5. **Settings → Pages**에 표시된 공개 주소와 위 홈페이지 주소에 접속하고, [배포 점검표](DEPLOY_CHECKLIST.md)를 실행합니다. 이전 내용이 남으면 새로고침·캐시 비우기 후 다시 확인합니다.

개인 도메인으로 바꿀 때는 DNS와 Pages의 Custom domain 설정을 확인하고 필요한 `CNAME`을 관리합니다. 현재 저장소에는 `CNAME`이 없습니다. 도메인 변경 시 canonical·공유 이미지·구조화 데이터·사이트맵·robots.txt의 주소도 함께 갱신합니다. 상세 검색엔진 확인 사항은 배포 점검표에 있습니다.
