# 🏢 한국 기업정보 조회 MCP 서버

**DART API**를 활용한 고성능 MCP (Model Context Protocol) 서버입니다.

AI 에이전트(Claude Desktop, Cursor 등)가 실시간으로 한국 상장기업의 재무제표, 공시정보, 임원정보, 지분구조 등을 조회하고 분석할 수 있도록 합니다.

---

## ✨ 주요 기능

### 📊 기업 정보 조회 (DART API)

| 기능 | 설명 |
|------|------|
| **기업 검색** | 회사명으로 기업 검색 및 기본정보 조회 |
| **기업 기본정보** | 회사명, 대표자명, 설립일, 본사주소 등 기본정보 조회 |
| **재무제표 조회** | 손익계산서, 재무상태표, 현금흐름표 |
| **재무 추이 분석** | 최근 5-10년 재무제표 추이 분석 |
| **공시정보 조회** | 최근 공시 목록 및 상세 내용 |
| **주요사항보고서** | 임원변경, 자본금변경 등 주요사항 조회 |
| **임원정보 조회** | 임원명, 직책, 보수 등 임원정보 조회 |
| **지분보고서** | 주주명, 보유지분, 비율 등 지분구조 조회 |
| **공시원문 다운로드** | 공시보고서 원문 XML/PDF 다운로드 및 파싱 |

### 🚀 성능 최적화

- **전략적 캐싱**: 기업정보 데이터를 24시간 캐싱하여 API 호출 최소화
- **빠른 응답 속도**: 캐시 기반 즉시 응답
- **안정적인 운영**: 에러 핸들링 및 로깅 시스템
- **API 키 우선순위**: 메인 서버에서 받은 키 → .env 파일 (로컬 개발용)

---

## 🎯 활용 사례

### 투자사/VC
- **투자 검토**: 스타트업 재무제표 분석 및 성장성 평가
- **기업 가치 평가**: 재무 추이 분석을 통한 가치 산정
- **경쟁사 분석**: 여러 기업의 재무제표 비교 분석

### B2B 영업팀
- **고객사 분석**: 잠재 고객의 재무 상태 파악
- **영업 전략 수립**: 기업 정보 기반 맞춤형 영업 전략
- **신용도 확인**: 거래 전 재무 건전성 확인

### 컨설팅 회사
- **기업 분석 리포트**: 재무제표, 공시정보 자동 수집 및 분석
- **경쟁사 비교**: 여러 기업의 재무 지표 비교
- **시장 분석**: 업종별 기업 재무 현황 분석

### 스타트업/개발자
- **경쟁사 모니터링**: 경쟁사의 재무 현황 추적
- **투자 유치 준비**: 재무제표 분석을 통한 투자 자료 준비
- **기업 리서치**: 잠재 파트너사 정보 수집

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
HTTP_MODE=1 python src/main.py
```

또는

```bash
export HTTP_MODE=1
python src/main.py
```

HTTP 서버는 기본적으로 `http://localhost:8097`에서 실행됩니다.

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

## 🔌 Claude Desktop 연동

### 설정 파일 위치

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 설정 예시

```json
{
  "mcpServers": {
    "company-info": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "C:/Users/사용자명/Desktop/company-info-mcp",
      "env": {
        "DART_API_KEY": "your_dart_api_key_here"
      }
    }
  }
}
```

> ⚠️ **중요**: `cwd` 경로를 실제 프로젝트 경로로 변경하세요!

### 사용 방법

Claude Desktop 재시작 후 Claude에게 질문:

- "삼성전자 재무제표 분석해줘"
- "네이버 최근 공시 확인해줘"
- "카카오뱅크 투자 검토해줘"
- "네이버, 카카오, 라인 재무 비교해줘"

---

## 🧰 사용 가능한 도구 (Tools)

### 1. `health`
서비스 상태 및 API 키 설정 확인

**파라미터**: 없음 (또는 `arguments.env.DART_API_KEY`)

**반환 예시**:
```json
{
  "status": "ok",
  "message": "정상",
  "service": "Korean Company Information MCP Server (Free Version)",
  "environment": {
    "dart_api_key": "설정됨",
    "dart_key_preview": "abc123...",
    "key_source": "arguments.env"
  }
}
```

---

### 2. `search_company_tool`
기업을 회사명으로 검색

**파라미터**:
- `query` (string, 필수): 검색할 회사명 (예: '삼성전자', '네이버')

**반환**: 검색된 기업 목록 (기업 고유번호 포함)

---

### 3. `get_financial_statement_tool`
기업의 재무제표 조회

**파라미터**:
- `corp_code` (string, 선택): 기업 고유번호
- `company_name` (string, 선택): 회사명 (corp_code 또는 company_name 중 하나 필수)
- `bsns_year` (string, 선택): 사업연도 (YYYY 형식, 기본값: 최근 연도)
- `reprt_code` (string, 선택): 보고서 코드 (11011: 사업보고서, 11013: 분기보고서, 기본값: 11011)

**반환**: 재무제표 정보 (손익계산서, 재무상태표, 현금흐름표)

---

### 4. `analyze_financial_trend_tool`
기업의 재무 추이 분석 (최근 N년)

**파라미터**:
- `corp_code` (string, 필수): 기업 고유번호
- `years` (integer, 선택): 분석할 연수 (기본값: 5, 최대: 10)

**반환**: 재무 추이 분석 결과 (최근 N년 재무제표 데이터)

---

### 5. `get_public_disclosure_tool`
기업의 공시정보 조회

**파라미터**:
- `corp_code` (string, 필수): 기업 고유번호
- `bgn_de` (string, 선택): 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
- `end_de` (string, 선택): 종료일 (YYYYMMDD 형식, 기본값: 오늘)
- `page_no` (integer, 선택): 페이지 번호 (기본값: 1)
- `page_count` (integer, 선택): 페이지당 건수 (기본값: 10, 최대: 100)

**반환**: 공시정보 목록

---

### 6. `get_company_overview_tool`
기업의 기본정보 조회

**파라미터**:
- `corp_code` (string, 선택): 기업 고유번호
- `company_name` (string, 선택): 회사명 (corp_code 또는 company_name 중 하나 필수)

**반환**: 기업 기본정보 (회사명, 대표자명, 설립일, 본사주소 등)

---

### 7. `get_major_report_tool`
주요사항보고서 조회

**파라미터**:
- `corp_code` (string, 선택): 기업 고유번호
- `company_name` (string, 선택): 회사명
- `bgn_de` (string, 선택): 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
- `end_de` (string, 선택): 종료일 (YYYYMMDD 형식, 기본값: 오늘)

**반환**: 주요사항보고서 목록 (임원변경, 자본금변경 등)

---

### 8. `download_disclosure_document_tool`
공시원문 다운로드

**파라미터**:
- `rcept_no` (string, 필수): 접수번호 (공시정보에서 얻을 수 있음)
- `file_format` (string, 선택): 파일 형식 ("xml" 또는 "pdf", 기본값: "xml")

**반환**: 공시원문 데이터 (XML은 파싱된 데이터 포함, PDF는 base64 인코딩)

---

### 9. `get_executives_tool`
기업의 임원정보 조회

**파라미터**:
- `corp_code` (string, 선택): 기업 고유번호
- `company_name` (string, 선택): 회사명 (corp_code 또는 company_name 중 하나 필수)

**반환**: 임원정보 목록 (임원명, 직책, 보수 등)

---

### 10. `get_shareholders_tool`
지분보고서 조회

**파라미터**:
- `corp_code` (string, 선택): 기업 고유번호
- `company_name` (string, 선택): 회사명
- `bsns_year` (string, 선택): 사업연도 (YYYY 형식, 기본값: 최근 연도)
- `reprt_code` (string, 선택): 보고서 코드 (11011: 사업보고서, 11013: 분기보고서, 기본값: 11011)

**반환**: 지분보고서 (주주명, 보유지분, 비율 등)

---

## 💡 사용 예시

### 예시 1: 기업 재무제표 분석

**사용자**: "삼성전자 재무제표 분석해줘"

**AI 에이전트가 수행하는 작업**:
1. `search_company_tool(query="삼성전자")` 호출 → corp_code 확인
2. `get_financial_statement_tool(company_name="삼성전자", bsns_year="2024")` 호출
3. 재무제표 분석 및 요약 제공

---

### 예시 2: 재무 추이 분석

**사용자**: "네이버 최근 5년 재무 추이 분석해줘"

**AI 에이전트가 수행하는 작업**:
1. 기업 검색 → corp_code 확인
2. `analyze_financial_trend_tool(corp_code="...", years=5)` 호출
3. 최근 5년 매출, 영업이익, 순이익 추이 분석
4. 성장성 평가 및 그래프 생성

---

### 예시 3: 투자 검토

**사용자**: "카카오뱅크 투자 검토해줘"

**AI 에이전트가 수행하는 작업**:
1. `search_company_tool(query="카카오뱅크")` - 회사 검색
2. `get_company_overview_tool(company_name="카카오뱅크")` - 기본정보 확인
3. `analyze_financial_trend_tool(corp_code="...", years=3)` - 최근 3년 재무 추이
4. `get_executives_tool(company_name="카카오뱅크")` - 임원진 확인
5. `get_shareholders_tool(company_name="카카오뱅크")` - 지분구조 확인
6. `get_public_disclosure_tool(corp_code="...")` - 최근 공시 확인
7. 종합 투자 의견 제시

---

### 예시 4: 경쟁사 비교

**사용자**: "네이버, 카카오, 라인 재무 비교해줘"

**AI 에이전트가 수행하는 작업**:
1. 각 회사별로 `analyze_financial_trend_tool` 호출
2. 매출, 영업이익, 순이익 추이 비교
3. 성장률 계산 및 비교표 생성
4. `get_shareholders_tool`로 지분구조 비교

---

### 예시 5: 공시 원문 상세 분석

**사용자**: "삼성전자 최근 공시 중 중요한 것 하나 상세 분석해줘"

**AI 에이전트가 수행하는 작업**:
1. `get_public_disclosure_tool(company_name="삼성전자", page_count=10)` - 최근 공시 목록
2. 공시 제목 분석하여 중요 공시 선택
3. `download_disclosure_document_tool(rcept_no="...", file_format="xml")` - 공시원문 다운로드
4. XML 파싱된 데이터 분석
5. 핵심 내용 요약 및 의견 제시

---

## 🌐 HTTP API 엔드포인트

HTTP 서버 모드로 실행 시 다음 엔드포인트를 사용할 수 있습니다:

### `GET /health`
서비스 상태 확인

**응답 예시**:
```json
{
  "status": "ok",
  "message": "정상",
  "service": "Korean Company Information MCP Server (Free Version)",
  "environment": {
    "dart_api_key": "설정됨",
    "key_source": ".env file"
  }
}
```

### `POST /health`
서비스 상태 확인 (env 포함 가능)

**요청 본문**:
```json
{
  "env": {
    "DART_API_KEY": "your_api_key_here"
  }
}
```

### `GET /tools`
사용 가능한 도구 목록 조회

**응답**: 도구 목록 배열

### `POST /tools/{tool_name}`
도구 호출

**요청 예시**:
```json
{
  "query": "삼성전자",
  "env": {
    "DART_API_KEY": "your_api_key_here"
  }
}
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

## 📁 프로젝트 구조

```
company-info-mcp/
├── src/
│   ├── __init__.py
│   ├── main.py        # MCP 서버 메인 파일
│   └── tools.py       # 기업정보 API 호출 도구
├── .env               # 환경 변수 파일 (API 키 등) - .gitignore에 포함
├── env.example        # 환경 변수 예시 파일
├── requirements.txt   # Python 의존성
├── pyproject.toml     # 프로젝트 설정
├── Dockerfile         # Docker 이미지 빌드 파일
├── DEVELOPMENT_GUIDE.md  # 개발 가이드 (DART API 그룹별 기능)
└── README.md          # 프로젝트 문서 (이 파일)
```

---

## ⚠️ 제한사항

### 무료 버전의 한계
- **상장기업만 가능**: DART API는 상장기업 정보만 제공 (비상장 기업 불가)
- **사업자등록정보 없음**: 기본 사업자 정보는 유료 API 필요
- **신용정보 없음**: 신용등급은 유료 API 필요

### API 사용 제한
- DART API: 일일 호출 제한 있음 (보통 충분함)
- API 키는 무료로 발급 가능

---

## 🐛 문제 해결

### "API 키가 설정되지 않았습니다" 오류

**원인**: DART_API_KEY 환경 변수가 설정되지 않음

**해결**:
1. `.env` 파일 확인
2. `DART_API_KEY=your_key_here` 형식으로 설정되어 있는지 확인
3. 또는 메인 서버에서 `arguments.env.DART_API_KEY`로 전달

### "DART API 오류" 메시지

**원인**: API 키가 잘못되었거나 기업을 찾을 수 없음

**해결**:
1. API 키가 올바른지 확인
2. 상장기업인지 확인 (비상장 기업은 지원 안 됨)
3. 회사명 정확히 입력 (예: "삼성전자" O, "삼성" X)

### Claude Desktop에서 도구가 보이지 않음

**해결**:
1. `claude_desktop_config.json` 파일 경로 확인
2. JSON 형식이 올바른지 확인 (콤마, 따옴표 등)
3. `cwd` 경로를 실제 프로젝트 경로로 변경
4. Claude Desktop 완전 종료 후 재시작
5. 로그 파일 확인 (Windows: `%APPDATA%\Claude\logs`)

---

## 📚 개발 가이드

DART API의 각 그룹별 기능과 추가 개발 방법은 [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)를 참고하세요.

### 구현 상태

- **DS001**: 공시정보 조회 (✅ 구현 완료)
- **DS002**: 재무정보 조회 (✅ 구현 완료)
- **DS003**: 기업개황 정보 (✅ 주요 기능 구현 완료)
- **DS004**: 공시원문 다운로드 (✅ 구현 완료)
- **DS005**: 주요사항보고서 (✅ 구현 완료)
- **DS006**: 기타 정보 (✅ 주요 기능 구현 완료)

---

## 🤝 기여 및 문의

- **이슈**: GitHub Issues
- **문의**: company-info-mcp@example.com
- **문서**: https://github.com/your-repo/company-info-mcp

---

## 📄 라이선스

MIT License

---

**Made with ❤️ for Korean Business Professionals**

DART API를 활용하여 개발되었습니다.
