# SNS 공유 이미지

- 공개 홈페이지: https://leechung0214-afk.github.io/fineinc-website/
- 이미지: `assets/fine-social-20261105.png` (1200×630, sRGB PNG, 불투명)
- 공식 `assets/fine-logo-white.png`를 가로 560px로 비율 축소해 중앙에 합성했다. 원본 로고 파일은 수정하지 않았다. 로고와 주요 문구는 중앙 630×630 영역 안에 있다.
- 배경은 이미지 생성 도구로 제작했다. 요청: 네이비 #10243a 바탕, 블루 #145aa4·시안 #00b8c8의 절제된 빛과 곡선, 중앙 여백, 글자·로고 없음.
- 재생성: Node.js와 sharp가 설치된 환경에서 `node scripts/render-social-image.cjs`. 배경 원본은 `design/social-background.png`에 보존했다. 사이트 운영에는 생성 도구나 Node.js가 필요 없다.

## 배포 후 확인

1. PR 병합 후 GitHub Pages 배포 성공을 확인한다.
2. 공개 HTML에서 og:image / twitter:image가 위 공개 주소 아래의 이미지 절대 URL을 가리키는지 확인한다.
3. 이미지 URL이 인증 없이 HTTP 200, Content-Type image/png로 응답하는지 확인한다.
4. 카카오톡 iOS/Android에서 홈페이지 링크를 새로 공유해 로고·제목·설명을 확인한다. X에서도 대형 카드 표시를 확인한다.
5. 이전 미리보기가 남으면 해당 서비스의 공유 캐시 갱신 후 다시 확인한다. 기존 메시지의 카드가 즉시 갱신된다고 보장하지 않는다.

PR 단계에서는 새 이미지가 아직 main에 배포되지 않으므로 공개 이미지 URL 응답 및 실제 카카오톡/X 카드 결과는 배포 후 검증 대상이다. 정사각형 잘림과 축소 이미지는 디자인 검토용이며 실제 앱 화면을 재현한 것은 아니다.

이미지를 다시 변경할 때는 새 버전 파일명을 사용하고 og:image, og:image:secure_url, twitter:image를 함께 갱신한다. 도메인 변경 시 canonical과 og:url도 함께 갱신한다.
