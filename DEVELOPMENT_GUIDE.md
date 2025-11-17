# 📚 DART API 개발 가이드

이 문서는 DART API의 각 그룹별 기능과 개발 방법을 안내합니다.

## 📋 DART API 그룹 개요

### DS001: 공시정보 조회

- **기능**: 기업의 공시정보 목록 및 상세 조회
- **현재 구현**: ✅ `get_public_disclosure_tool`
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS001

### DS002: 재무정보 조회

- **기능**: 재무제표, 손익계산서, 현금흐름표 등 재무정보 조회
- **현재 구현**: ✅ `get_financial_statement_tool`, `analyze_financial_trend_tool`
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS002

### DS003: 기업개황 정보

- **기능**: 기업 기본정보, 주요사항, 임원정보 등
- **현재 구현**: ✅ 대부분 구현 완료
  - ✅ 기업 기본정보 조회 (`get_company_overview_tool`)
  - ✅ 임원정보 조회 (`get_executives_tool`)
  - ⚠️ 주요사항 조회 (`/majorIssues.json`) - 미구현 (덜 중요)
  - ⚠️ 사업의 내용 조회 (`/bizrNo.json`) - 미구현 (덜 중요)
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS003

### DS004: 공시원문 다운로드

- **기능**: 공시보고서 원문(XML, PDF) 다운로드
- **현재 구현**: ✅ 구현 완료 (`download_disclosure_document_tool`)
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS004

### DS005: 주요사항보고서

- **기능**: 주요사항보고서 조회 및 분석
- **현재 구현**: ✅ 구현 완료 (`get_major_report_tool`)
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS005

### DS006: 기타 정보

- **기능**: 지분보고서, 증권신고서 등 기타 공시정보
- **현재 구현**: ⚠️ 부분 구현
  - ✅ 지분보고서 조회 (`get_shareholders_tool`)
  - ⚠️ 증권신고서 조회 (`/securitiesReport.json`) - 미구현 (덜 중요)
- **개발 가이드**: https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS006

---

## 🛠️ 추가 개발 가이드

### 1. DS003: 기업개황 정보 추가 개발

#### 1.1 기업 기본정보 조회

```python
def get_company_overview(corp_code: str, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 기본정보를 조회합니다.

    API: /company.json
    """
    api_url = f"{DART_API_URL}/company.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
    }
    # 구현...
```

#### 1.2 임원정보 조회

```python
def get_executives(corp_code: str, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 임원정보를 조회합니다.

    API: /empSttus.json
    """
    api_url = f"{DART_API_URL}/empSttus.json"
    # 구현...
```

#### 1.3 주요사항 조회

```python
def get_major_issues(corp_code: str, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 주요사항을 조회합니다.

    API: /majorIssues.json
    """
    api_url = f"{DART_API_URL}/majorIssues.json"
    # 구현...
```

### 2. DS004: 공시원문 다운로드 추가 개발

#### 2.1 공시원문 다운로드

```python
def download_disclosure_document(rcept_no: str, arguments: Optional[dict] = None) -> Dict:
    """
    공시원문을 다운로드합니다.

    API: /document.xml 또는 /document.pdf
    """
    api_url = f"{DART_API_URL}/document.xml"
    params = {
        "crtfc_key": api_key,
        "rcept_no": rcept_no,
    }
    # 구현...
```

#### 2.2 XML 파싱 및 데이터 추출

```python
def parse_disclosure_xml(xml_content: bytes) -> Dict:
    """
    공시원문 XML을 파싱하여 구조화된 데이터로 변환합니다.
    """
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_content)
    # 파싱 로직...
```

### 3. DS005: 주요사항보고서 추가 개발

#### 3.1 주요사항보고서 조회

```python
def get_major_report(corp_code: str, bgn_de: str = None, end_de: str = None,
                     arguments: Optional[dict] = None) -> Dict:
    """
    주요사항보고서를 조회합니다.

    API: /majorReport.json
    """
    api_url = f"{DART_API_URL}/majorReport.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de or (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
        "end_de": end_de or datetime.now().strftime("%Y%m%d"),
    }
    # 구현...
```

### 4. DS006: 기타 정보 추가 개발

#### 4.1 지분보고서 조회

```python
def get_shareholders_report(corp_code: str, arguments: Optional[dict] = None) -> Dict:
    """
    지분보고서를 조회합니다.

    API: /shareholders.json
    """
    api_url = f"{DART_API_URL}/shareholders.json"
    # 구현...
```

#### 4.2 증권신고서 조회

```python
def get_securities_report(corp_code: str, arguments: Optional[dict] = None) -> Dict:
    """
    증권신고서를 조회합니다.

    API: /securitiesReport.json
    """
    api_url = f"{DART_API_URL}/securitiesReport.json"
    # 구현...
```

---

## 🔧 구현 예시

### 예시 1: 기업 기본정보 조회 도구 추가

`src/tools.py`에 추가:

```python
def get_company_overview(corp_code: Optional[str] = None, company_name: Optional[str] = None,
                         arguments: Optional[dict] = None) -> Dict:
    """
    기업의 기본정보를 조회합니다.
    """
    # corp_code가 없으면 company_name으로 검색
    if not corp_code and company_name:
        search_result = search_company(company_name, arguments)
        if "error" in search_result:
            return {"error": f"기업 검색 실패: {search_result['error']}"}
        companies = search_result.get("companies", [])
        if not companies:
            return {"error": f"'{company_name}'에 해당하는 기업을 찾을 수 없습니다."}
        corp_code = companies[0].get("corp_code")

    if not corp_code:
        return {"error": "corp_code 또는 company_name 중 하나는 필수입니다."}

    # corp_code 정규화
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)

    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]

    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}

    api_url = f"{DART_API_URL}/company.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
    }

    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "000":
            return {
                "corp_code": corp_code,
                "company_info": data
            }
        else:
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
    except Exception as e:
        logger.exception("Company overview error: %s", str(e))
        return {"error": f"기업정보 조회 중 오류 발생: {str(e)}"}
```

`src/main.py`에 MCP 도구 추가:

```python
@mcp.tool()
async def get_company_overview_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None
):
    """
    기업의 기본정보를 조회합니다.
    """
    req = CompanyOverviewRequest(
        corp_code=corp_code,
        company_name=company_name
    )
    return await get_company_overview_impl(req)
```

### 예시 2: 공시원문 다운로드 도구 추가

```python
def download_disclosure_document(rcept_no: str, file_format: str = "xml",
                                 arguments: Optional[dict] = None) -> Dict:
    """
    공시원문을 다운로드합니다.

    Args:
        rcept_no: 접수번호
        file_format: 파일 형식 ("xml" 또는 "pdf")
    """
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]

    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}

    api_url = f"{DART_API_URL}/document.{file_format}"
    params = {
        "crtfc_key": api_key,
        "rcept_no": rcept_no,
    }

    try:
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status()

        if file_format == "xml":
            # XML 파싱
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            # 파싱 로직...
            return {
                "rcept_no": rcept_no,
                "format": file_format,
                "content": response.text,
                "parsed": True
            }
        else:
            # PDF는 바이너리로 반환
            import base64
            return {
                "rcept_no": rcept_no,
                "format": file_format,
                "content_base64": base64.b64encode(response.content).decode('utf-8'),
                "size": len(response.content)
            }
    except Exception as e:
        logger.exception("Document download error: %s", str(e))
        return {"error": f"공시원문 다운로드 중 오류 발생: {str(e)}"}
```

---

## 📝 개발 체크리스트

### DS003 구현

- [x] 기업 기본정보 조회 (`/company.json`) ✅
- [x] 임원정보 조회 (`/empSttus.json`) ✅
- [ ] 주요사항 조회 (`/majorIssues.json`) - 선택사항
- [ ] 사업의 내용 조회 (`/bizrNo.json`) - 선택사항

### DS004 구현

- [x] 공시원문 XML 다운로드 (`/document.xml`) ✅
- [x] 공시원문 PDF 다운로드 (`/document.pdf`) ✅
- [x] XML 파싱 및 데이터 추출 ✅
- [ ] PDF 텍스트 추출 (선택사항) - 현재는 base64 인코딩으로 반환

### DS005 구현

- [x] 주요사항보고서 조회 (`/majorReport.json`) ✅
- [x] 주요사항보고서 필터링 (기간, 유형별) ✅

### DS006 구현

- [x] 지분보고서 조회 (`/shareholders.json`) ✅
- [ ] 증권신고서 조회 (`/securitiesReport.json`) - 선택사항
- [ ] 기타 공시정보 조회 - 선택사항

---

## 🔍 API 엔드포인트 참고

### 공통 파라미터

- `crtfc_key`: 인증키 (필수)
- `corp_code`: 기업 고유번호 (8자리, 필수)
- `bgn_de`: 시작일 (YYYYMMDD 형식)
- `end_de`: 종료일 (YYYYMMDD 형식)

### 응답 형식

```json
{
  "status": "000",  // "000": 성공, "013": 데이터 없음, 기타: 오류
  "message": "정상",
  "list": [...]  // 데이터 배열
}
```

### 오류 코드

- `000`: 정상
- `010`: 등록되지 않은 키
- `011`: 사용할 수 없는 키
- `012`: 접근할 수 없는 IP
- `013`: 조회된 데이터가 없습니다
- `020`: 요청 제한 초과

---

## 🚀 개발 팁

### 1. 캐싱 전략

```python
# 기업 기본정보는 자주 변하지 않으므로 긴 TTL 사용
company_overview_cache = TTLCache(maxsize=100, ttl=86400 * 7)  # 7일

# 공시정보는 자주 업데이트되므로 짧은 TTL 사용
disclosure_cache = TTLCache(maxsize=100, ttl=3600)  # 1시간
```

### 2. 에러 핸들링

```python
try:
    response = requests.get(api_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "000":
        return {"data": data.get("list", [])}
    elif data.get("status") == "013":
        return {"error": "조회된 데이터가 없습니다."}
    else:
        return {"error": f"DART API 오류: {data.get('message')}"}
except requests.exceptions.Timeout:
    return {"error": "API 요청 시간 초과"}
except requests.exceptions.RequestException as e:
    return {"error": f"API 요청 실패: {str(e)}"}
```

### 3. 로깅

```python
logger.debug("API request | url=%s params=%s", api_url,
            {k: v if k != "crtfc_key" else v[:6] + "***" for k, v in params.items()})
logger.info("API response | status=%s items=%d", data.get("status"), len(data.get("list", [])))
```

---

## 📚 참고 자료

- [DART API 공식 문서](https://opendart.fss.or.kr/guide/main.do)
- [DART API 그룹별 가이드](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS001)
- [Python requests 문서](https://requests.readthedocs.io/)
- [FastMCP 문서](https://github.com/jlowin/fastmcp)

---

## 💡 다음 단계

1. **DS003 구현**: 기업 기본정보, 임원정보 조회 기능 추가
2. **DS004 구현**: 공시원문 다운로드 및 파싱 기능 추가
3. **DS005 구현**: 주요사항보고서 조회 기능 추가
4. **DS006 구현**: 지분보고서, 증권신고서 조회 기능 추가
5. **테스트**: 각 기능에 대한 단위 테스트 및 통합 테스트 작성
6. **문서화**: README 및 API 문서 업데이트

---

**Happy Coding! 🚀**
