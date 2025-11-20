# 🏢 한국 기업정보 조회 MCP 서버

**DART API**를 활용한 MCP (Model Context Protocol) 서버입니다.

AI 에이전트(Claude Desktop, Cursor 등)가 실시간으로 한국 상장기업의 재무제표, 공시정보, 임원정보, 지분구조 등을 조회하고 분석할 수 있도록 합니다.

---

## ✨ 주요 기능

### 📊 기업 정보 조회 (DART API)

| 기능               | 설명                                                |
| ------------------ | --------------------------------------------------- |
| **기업 검색**      | 회사명으로 기업 검색 및 기본정보 조회               |
| **기업 기본정보**  | 회사명, 대표자명, 설립일, 본사주소 등 기본정보 조회 |
| **재무제표 조회**  | 손익계산서, 재무상태표, 현금흐름표                  |
| **재무 추이 분석** | 최근 5-10년 재무제표 추이 분석                      |
| **공시정보 조회**  | 최근 공시 목록 및 상세 내용                         |
| **임원정보 조회**  | 임원명, 직책, 보수 등 임원정보 조회                 |
| **지분보고서**     | 주주명, 보유지분, 비율 등 지분구조 조회             |

### 🚀 성능 최적화

- **전략적 캐싱**: 기업정보 데이터를 24시간 캐싱하여 API 호출 최소화
- **빠른 응답 속도**: 캐시 기반 즉시 응답
- **안정적인 운영**: 에러 핸들링 및 로깅 시스템
- **API 키 우선순위**: 메인 서버에서 받은 키 → .env 파일 (로컬 개발용)

---

## 🛠️ 기술 스택

- **MCP Framework**: FastMCP
- **Data Validation**: Pydantic
- **HTTP Client**: Requests
- **Caching**: cachetools (TTL 캐시)
- **Async Processing**: asyncio
- **Environment**: Python-dotenv

---

## 📦 설치 및 설정

### 1) 의존성 설치

```bash
pip install -r requirements.txt
```

> 💡 `uv`를 사용하는 경우: `uv sync`

### 2) DART API 키 발급 (무료, 즉시)

1. [전자공시시스템 Open DART](https://opendart.fss.or.kr/) 방문
2. 회원가입 및 로그인
3. **인증키 신청/관리** 메뉴에서 인증키 발급
4. **즉시 발급** (무료)

> 💡 **무료**이며, 일일 API 호출 제한이 충분히 넉넉합니다!

### 3) 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 API 키를 설정합니다:

```bash
cp env.example .env
```

`.env` 파일 내용:

```env
DART_API_KEY=your_dart_api_key_here
LOG_LEVEL=INFO
PORT=8097
```

### 4) 서버 실행

#### MCP 서버 모드 (stdio)

```bash
python -m src.main
```

#### HTTP 서버 모드

```bash
HTTP_MODE=1 python -m src.main
```

HTTP 서버는 기본적으로 `http://localhost:8097`에서 실행됩니다.

---

## 🔌 MCP 클라이언트 설정

### Claude Desktop

`claude_desktop_config.json` 파일에 다음을 추가:

**설정 파일 위치:**

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**설정 예시:**

```json
{
  "mcpServers": {
    "company-info": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/company-info-mcp",
      "env": {
        "DART_API_KEY": "your_dart_api_key_here"
      }
    }
  }
}
```

> ⚠️ **중요**: `cwd` 경로를 실제 프로젝트 경로로 변경하세요!

### Cursor

Cursor의 MCP 설정에서 위와 동일한 설정을 추가합니다.

---

## 🧰 사용 가능한 MCP 도구

### `search_company_tool`

회사명으로 기업을 검색합니다.

**파라미터:**

- `company_name` (필수): 검색할 회사명

### `get_company_overview_tool`

기업의 기본정보를 조회합니다.

**파라미터:**

- `corp_code` (선택): 기업 고유번호
- `company_name` (선택): 회사명 (corp_code 또는 company_name 중 하나 필수)

### `get_financial_statement_tool`

기업의 재무제표를 조회합니다.

**파라미터:**

- `corp_code` (선택): 기업 고유번호
- `company_name` (선택): 회사명
- `bsns_year` (선택): 사업연도 (YYYY 형식)
- `reprt_code` (선택): 보고서 코드 (기본값: "11011")

### `analyze_financial_trend_tool`

기업의 재무 추이를 분석합니다 (최근 N년).

**파라미터:**

- `corp_code` (필수): 기업 고유번호
- `years` (선택): 분석할 연수 (기본값: 5, 최대: 10)

### `get_public_disclosure_tool`

기업의 공시정보를 조회합니다.

**파라미터:**

- `corp_code` (필수): 기업 고유번호
- `bgn_de` (선택): 시작일 (YYYYMMDD 형식)
- `end_de` (선택): 종료일 (YYYYMMDD 형식)
- `page_no` (선택): 페이지 번호 (기본값: 1)
- `page_count` (선택): 페이지당 건수 (기본값: 10)

### `get_executives_tool`

기업의 임원정보를 조회합니다.

**파라미터:**

- `corp_code` (선택): 기업 고유번호
- `company_name` (선택): 회사명
- `bsns_year` (선택): 사업연도 (YYYY 형식)
- `reprt_code` (선택): 보고서 코드 (기본값: "11011")

### `get_shareholders_tool`

지분보고서를 조회합니다.

**파라미터:**

- `corp_code` (선택): 기업 고유번호
- `company_name` (선택): 회사명
- `bsns_year` (선택): 사업연도 (YYYY 형식)
- `reprt_code` (선택): 보고서 코드 (기본값: "11011")

---

## 📡 HTTP API 엔드포인트

HTTP 모드로 실행 시 다음 엔드포인트를 사용할 수 있습니다:

### Health Check

```bash
GET /health
POST /health
```

### 도구 목록 조회

```bash
GET /tools
```

### 도구 실행

```bash
POST /tools/{tool_name}
Content-Type: application/json

{
  "company_name": "삼성전자",
  "env": {
    "DART_API_KEY": "your_api_key"
  }
}
```

---

## 🐳 Docker 실행

```bash
# 이미지 빌드
docker build -t company-info-mcp:latest .

# 컨테이너 실행
docker run --rm \
  -e DART_API_KEY=your_dart_api_key_here \
  -p 8097:8097 \
  company-info-mcp:latest
```

---

## 🔑 API 키 우선순위

MCP 서버는 다음 순서로 API 키를 찾습니다:

1. **우선순위 1**: `arguments.env.DART_API_KEY` (메인 서버에서 받은 키)
2. **우선순위 2**: `.env` 파일의 `DART_API_KEY` (로컬 개발용)
3. **둘 다 없으면**: Health 체크에서 "등록된 키가 없습니다" 반환

이를 통해:

- **프로덕션**: 메인 서버에서 각 사용자별 키를 전달받아 사용
- **로컬 개발**: `.env` 파일에 키를 설정하여 개발

---

## 🐛 문제 해결

### "API 키가 설정되지 않았습니다" 오류

**해결 방법:**

1. `.env` 파일에 `DART_API_KEY`가 올바르게 설정되어 있는지 확인
2. 환경 변수로 직접 설정: `export DART_API_KEY=your_key`

### MCP 클라이언트 연결 오류

**해결 방법:**

1. 서버가 올바르게 실행되고 있는지 확인
2. Python 경로가 올바른지 확인
3. 의존성이 모두 설치되었는지 확인: `pip install -r requirements.txt`
4. `cwd` 경로를 실제 프로젝트 경로로 변경
5. Claude Desktop 완전 종료 후 재시작

---

## 📄 라이선스

이 프로젝트는 DART API를 사용하며, DART API의 이용약관을 준수합니다.
