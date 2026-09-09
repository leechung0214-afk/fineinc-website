# FINE INC. Website — GitHub Pages 배포본

이 폴더는 **GitHub Pages에 그대로 올려서 무료 공개**할 수 있도록 정리한 버전입니다.

## 1) 가장 쉬운 배포 방법

1. GitHub에서 새 **Public repository**를 만듭니다.
   - 추천 이름: `fineinc-website`
2. 이 ZIP을 압축 해제합니다.
3. 압축을 푼 폴더 안의 **모든 파일과 폴더**를 저장소 최상위(root)에 업로드합니다.
   - `index.html`
   - `assets/`
   - `.nojekyll`
   - `site.webmanifest`
   - `robots.txt`
4. GitHub 저장소에서 **Settings → Pages**로 이동합니다.
5. **Build and deployment**에서 다음처럼 선택합니다.
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/(root)`
6. `Save`를 누릅니다.
7. 잠시 후 아래 형태의 공개 URL이 생성됩니다.
   - `https://사용자명.github.io/fineinc-website/`

### 주소를 더 짧게 만들고 싶다면

저장소 이름을 정확히 `사용자명.github.io`로 만들면:

`https://사용자명.github.io/`

주소로 바로 공개할 수 있습니다.

---

## 2) 앞으로 홈페이지 수정하는 방법

### 방법 A — GitHub 웹에서 직접 수정

1. 수정할 파일을 클릭합니다.
2. 연필 아이콘(Edit)을 누릅니다.
3. 내용을 수정합니다.
4. `Commit changes`를 누릅니다.
5. GitHub Pages가 자동으로 다시 배포합니다.

### 방법 B — 새 파일로 덮어쓰기

ChatGPT에서 수정된 `index.html`, `style.css`, `script.js`, 이미지 등을 받은 뒤 GitHub의 같은 위치에 업로드하고 Commit하면 됩니다.

주요 파일 위치:

```text
index.html              메인 홈페이지 내용
assets/style.css        전체 디자인
assets/script.js        메뉴/스크롤/애니메이션
assets/logo-white.png   어두운 배경용 로고
assets/logo-color.png   컬러 로고
```

---

## 3) 실제 프로젝트 사진 추가

사진을 다음처럼 넣는 것을 권장합니다.

```text
assets/projects/
  acc-01.jpg
  acc-02.jpg
  suncheon-01.jpg
  bitgaram-01.jpg
```

이후 `index.html`의 프로젝트 카드 영역을 사진 기반으로 변경하면 됩니다.

---

## 4) 문의 폼 안내

GitHub Pages는 정적 호스팅이라 자체 서버가 없습니다. 현재 문의 폼은 디자인/입력 화면까지 구현되어 있으며 실제 메일 전송은 연결되어 있지 않습니다.

회사 대표 이메일이 확정되면 다음 중 하나로 변경할 수 있습니다.

- 메일 프로그램을 여는 `mailto:` 방식
- 외부 무료 폼 서비스 연결
- 별도 API/서버 연결

**GitHub만 사용한다면 `mailto:` 방식이 가장 단순합니다.**

---

## 5) 개인 도메인 연결

나중에 `fineinc.co.kr` 같은 도메인을 보유하게 되면 GitHub Pages의 **Settings → Pages → Custom domain**에서 연결할 수 있습니다.

도메인이 확정되면 루트에 `CNAME` 파일을 추가하면 됩니다.

예:

```text
www.fineinc.co.kr
```

도메인이 아직 없다면 `CNAME` 파일은 만들지 않는 것이 맞습니다.

---

## 6) 현재 사이트 기본 정보

- 회사명: 주식회사 파인아이엔씨
- 브랜드: FINE INC.
- 대표: 김도훈
- 사업자등록번호: 632-88-01987
- 콘셉트: Event Production Company
- 핵심 영역: EVENT / SPACE / STAGE / SOUND / LIGHT / VIDEO / CONTENT

직원 수, 매출액, 주소, 프로젝트 실적 등 변동 가능한 정보는 실제 최신 회사자료에 맞춰 업데이트해 주세요.
