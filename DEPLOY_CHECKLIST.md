# GitHub Pages 배포 체크리스트

- [ ] GitHub Public repository 생성
- [ ] ZIP 압축 해제
- [ ] `index.html`이 저장소 최상위에 있도록 전체 파일 업로드
- [ ] Settings → Pages 진입
- [ ] Source: Deploy from a branch
- [ ] Branch: main / (root)
- [ ] Save
- [ ] 공개 URL 접속 확인
- [ ] PC 화면 확인
- [ ] 모바일 화면 확인
- [ ] 회사 대표 이메일/전화/주소 확정 후 반영
- [ ] 실제 프로젝트 사진 반영
- [ ] 필요 시 개인 도메인 연결

## 검색엔진 기본 설정 — 병합·배포 후 확인

- [ ] `https://leechung0214-afk.github.io/fineinc-website/sitemap.xml`이 HTTP 200으로 제공되는지 확인
- [ ] 홈페이지 소스의 Organization JSON-LD와 canonical URL 확인
- [ ] 필요 시 사이트 소유권 확인 후 Google Search Console 또는 네이버 서치어드바이저에서 사이트맵 직접 제출

현재 사이트맵에는 대표 홈페이지 URL 하나만 포함합니다. 페이지 내부 앵커(`#about` 등), 중복 주소인 `index.html`, 오류 페이지 `404.html`은 제외합니다. 확인되지 않은 수정일·갱신 주기는 넣지 않습니다.

Organization에는 홈페이지에서 확인한 회사명·브랜드명·공식 URL만 사용합니다. 전화번호·주소·직원 수 등 미확인 정보는 추가하지 않습니다.

**GitHub Pages 경로 제약:** 이 저장소의 `robots.txt`는 `/fineinc-website/robots.txt`에 배포됩니다. 검색 로봇이 표준으로 조회하는 위치는 호스트 루트인 `https://leechung0214-afk.github.io/robots.txt`입니다. 따라서 이 저장소에 추가한 Sitemap 지시문만으로 자동 발견된다고 보장할 수 없습니다. 필요하면 별도로 관리하는 호스트 루트의 robots.txt에 사이트맵 절대 URL을 추가하거나 검색엔진 도구에서 직접 제출해야 합니다. 이 변경은 다른 저장소나 호스트 루트 설정을 수정하지 않습니다.

도메인을 변경하면 canonical, Open Graph/Twitter 이미지 URL, Organization의 `@id`·`url`, 사이트맵의 `loc`, robots.txt의 Sitemap 주소를 함께 갱신합니다. 파일 구성·문법 검증은 검색엔진 등록, 색인 또는 검색 결과 노출 완료를 의미하지 않습니다.

참고: [사이트맵 규격](https://www.sitemaps.org/protocol.html), [Organization](https://schema.org/Organization), [robots.txt 위치 규칙](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt)
