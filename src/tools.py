# tools.py
"""
한국 기업정보 조회를 위한 도구 모음
DART API 사용 (무료)
"""
import os
import logging
import requests
from cachetools import TTLCache
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json
import time

# 기본 API URL
DART_API_URL = "https://opendart.fss.or.kr/api"

# Logger
logger = logging.getLogger("company-mcp")
level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logger.setLevel(level)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
logger.propagate = True

# 캐시 설정
company_cache = TTLCache(maxsize=100, ttl=86400)  # 24시간 유지
financial_cache = TTLCache(maxsize=50, ttl=86400)
disclosure_cache = TTLCache(maxsize=100, ttl=3600)  # 1시간
company_overview_cache = TTLCache(maxsize=100, ttl=86400 * 7)  # 7일 (기본정보는 자주 변하지 않음)
executives_cache = TTLCache(maxsize=100, ttl=86400 * 7)  # 7일 (임원정보는 자주 변하지 않음)
shareholders_cache = TTLCache(maxsize=100, ttl=86400)  # 24시간
# 실패한 요청 캐시 (불필요한 재시도 방지, 5분 유지)
failure_cache = TTLCache(maxsize=200, ttl=300)  # 5분


def get_credentials(arguments: Optional[dict] = None) -> dict:
    """
    환경 변수에서 API 인증 정보를 가져옵니다.
    우선순위: 1) arguments.env, 2) .env 파일
    
    Args:
        arguments: 도구 호출 인자
        
    Returns:
        인증 정보가 담긴 딕셔너리
    """
    dart_key = ""
    key_source = "none"
    
    # 우선순위 1: arguments.env에서 받기 (메인 서버에서 받은 키)
    if isinstance(arguments, dict) and "env" in arguments:
        env = arguments["env"]
        if isinstance(env, dict) and "DART_API_KEY" in env:
            dart_key = env["DART_API_KEY"]
            key_source = "arguments.env"
    
    # 우선순위 2: .env 파일에서 받기 (로컬 개발용)
    if not dart_key:
        dart_key = os.environ.get("DART_API_KEY", "")
        if dart_key:
            key_source = ".env file"
    
    credentials = {
        "DART_API_KEY": dart_key,
    }
    
    # 로깅 (키 마스킹)
    masked_dart = credentials["DART_API_KEY"]
    if masked_dart:
        masked_dart = masked_dart[:6] + "***" + f"({len(masked_dart)} chars)"
    logger.debug(
        "Resolved credentials | DART_API_KEY=%s, source=%s",
        masked_dart or "<empty>",
        key_source
    )
    
    return credentials


def validate_corp_code(corp_code: str) -> tuple[bool, Optional[str]]:
    """
    corp_code 형식 검증
    
    Returns:
        (is_valid, error_message)
    """
    if not corp_code:
        return False, "corp_code가 비어있습니다."
    
    corp_code = str(corp_code).strip()
    
    if not corp_code.isdigit():
        return False, f"corp_code는 숫자만 가능합니다. (입력값: {corp_code})"
    
    if len(corp_code) > 8:
        return False, f"corp_code는 최대 8자리입니다. (입력값: {corp_code}, 길이: {len(corp_code)})"
    
    return True, None


def validate_bsns_year(bsns_year: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    bsns_year 형식 검증
    
    Returns:
        (is_valid, error_message)
    """
    if not bsns_year:
        return True, None  # None은 허용 (자동 설정됨)
    
    bsns_year = str(bsns_year).strip()
    
    if not bsns_year.isdigit():
        return False, f"bsns_year는 숫자만 가능합니다. (입력값: {bsns_year})"
    
    if len(bsns_year) != 4:
        return False, f"bsns_year는 YYYY 형식(4자리)이어야 합니다. (입력값: {bsns_year})"
    
    year = int(bsns_year)
    current_year = datetime.now().year
    
    if year < 2000 or year > current_year + 1:
        return False, f"bsns_year는 2000년부터 {current_year + 1}년 사이여야 합니다. (입력값: {bsns_year})"
    
    return True, None


def make_request_with_retry(url: str, params: dict, max_retries: int = 3, timeout: int = 30) -> requests.Response:
    """
    네트워크 요청을 재시도 로직과 함께 수행
    
    Args:
        url: 요청 URL
        params: 요청 파라미터
        max_retries: 최대 재시도 횟수
        timeout: 타임아웃 (초)
    
    Returns:
        Response 객체
    
    Raises:
        requests.exceptions.RequestException: 모든 재시도 실패 시
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1  # 1초, 2초, 3초...
                logger.warning("Request timeout (attempt %d/%d), retrying in %ds...", 
                             attempt + 1, max_retries, wait_time)
                time.sleep(wait_time)
            else:
                logger.error("Request timeout after %d attempts", max_retries)
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1
                logger.warning("Connection error (attempt %d/%d), retrying in %ds...", 
                             attempt + 1, max_retries, wait_time)
                time.sleep(wait_time)
            else:
                logger.error("Connection error after %d attempts", max_retries)
        except requests.exceptions.RequestException as e:
            # 재시도 불가능한 오류 (4xx, 5xx 등)
            logger.error("Request failed (non-retryable): %s", str(e))
            raise
    
    # 모든 재시도 실패
    if last_exception:
        raise last_exception
    else:
        raise requests.exceptions.RequestException("모든 재시도가 실패했습니다.")


def search_company(company_name: str, arguments: Optional[dict] = None) -> Dict:
    """
    기업을 회사명으로 검색합니다. (DART API)
    DART의 corpCode.xml 파일을 사용하여 회사명으로 corp_code를 검색합니다.
    
    이 함수는 다른 함수들에서 company_name만 있고 corp_code가 없을 때 먼저 호출되어야 합니다.
    검색 결과에서 corp_code를 얻은 후 다른 함수들(get_financial_statement, get_company_overview 등)을 호출할 수 있습니다.
    
    Args:
        company_name: 검색할 회사명 (필수, 예: "삼성전자", "네이버", "카카오")
                     부분 일치 검색이 가능합니다 (예: "삼성" 입력 시 "삼성전자", "삼성SDI" 등이 검색됨)
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        검색 결과 딕셔너리:
        {
            "total": 검색된 기업 수 (int),
            "companies": [
                {
                    "corp_code": "기업 고유번호 (8자리 문자열, 필수)",
                    "corp_name": "회사명",
                    "stock_code": "종목코드 (상장기업인 경우)",
                    "modify_date": "수정일자"
                },
                ...
            ]
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - "삼성전자" 검색 → 여러 삼성 관련 기업이 검색될 수 있음
        - "네이버" 검색 → 네이버 관련 기업 검색
        - 검색 결과가 여러 개일 경우, stock_code가 있는 상장기업을 우선 선택하거나
          정확한 회사명과 일치하는 것을 선택해야 함
    """
    logger.debug("search_company called | company_name=%r", company_name)
    
    # 캐시 키 생성 (arguments 제외)
    cache_key = (company_name,)
    if cache_key in company_cache:
        logger.debug("Cache hit for company search | company_name=%r", company_name)
        return company_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다. DART_API_KEY 환경 변수를 설정해주세요."}
    
    try:
        # DART API: 상장기업 고유번호 파일 다운로드
        # 이 파일은 ZIP으로 압축되어 있으며, 압축 해제 후 XML 파일을 읽어야 합니다
        corp_code_url = "https://opendart.fss.or.kr/api/corpCode.xml"
        
        params = {
            "crtfc_key": api_key,
        }
        
        response = requests.get(corp_code_url, params=params, timeout=60)
        response.raise_for_status()
        
        logger.debug("DART corpCode.xml downloaded | size=%d bytes", len(response.content))
        
        # ZIP 파일 압축 해제 및 XML 파싱
        try:
            import zipfile
            import io
            import xml.etree.ElementTree as ET
            
            # ZIP 파일로 읽기
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            
            # ZIP 파일 내의 XML 파일 찾기 (일반적으로 CORPCODE.xml)
            xml_file_name = None
            for name in zip_file.namelist():
                if name.endswith('.xml'):
                    xml_file_name = name
                    break
            
            if not xml_file_name:
                return {"error": "ZIP 파일 내에 XML 파일을 찾을 수 없습니다."}
            
            # XML 파일 읽기
            xml_content = zip_file.read(xml_file_name)
            root = ET.fromstring(xml_content)
            
            # 회사명으로 검색 (부분 일치)
            matching_companies = []
            company_name_lower = company_name.lower()
            
            # XML 구조에 따라 요소 찾기 (list 또는 다른 루트 요소)
            companies = root.findall(".//list") or root.findall("list")
            
            for company in companies:
                corp_name = company.findtext("corp_name", "")
                corp_code = company.findtext("corp_code", "")
                stock_code = company.findtext("stock_code", "")
                modify_date = company.findtext("modify_date", "")
                
                # 회사명에 검색어가 포함되어 있는지 확인
                if corp_name and company_name_lower in corp_name.lower():
                    matching_companies.append({
                        "corp_code": corp_code,
                        "corp_name": corp_name,
                        "stock_code": stock_code,
                        "modify_date": modify_date
                    })
            
            result = {
                "total": len(matching_companies),
                "companies": matching_companies
            }
            
            logger.debug("Company search results | company_name=%r total=%d", company_name, len(matching_companies))
            
            # 캐시에 저장
            company_cache[cache_key] = result
            return result
            
        except (zipfile.BadZipFile, ET.ParseError) as e:
            logger.exception("File parsing error: %s", str(e))
            return {"error": f"파일 파싱 오류: {str(e)}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("DART API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Company search error: %s", str(e))
        return {"error": f"기업 검색 중 오류 발생: {str(e)}"}


def get_financial_statement(corp_code: Optional[str] = None, company_name: Optional[str] = None, bsns_year: Optional[str] = None, reprt_code: str = "11011", arguments: Optional[dict] = None) -> Dict:
    """
    기업의 재무제표를 조회합니다. (DART API)
    
    손익계산서, 재무상태표, 현금흐름표 등의 재무 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 재무제표 조회
    - company_name만 제공되면: 먼저 search_company로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업 우선, 정확한 이름 일치 우선으로 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 최근 연도부터 시도)
                  지정하지 않으면 최근 3년도 중 데이터가 있는 연도를 자동으로 찾음
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        재무제표 정보 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "bsns_year": "사업연도",
            "reprt_code": "보고서 코드",
            "financial_data": [
                {
                    "account_nm": "계정명",
                    "thstrm_nm": "당기명",
                    "thstrm_amount": "당기금액",
                    ...
                },
                ...
            ]
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - company_name="삼성전자", bsns_year="2023" → 삼성전자 2023년 재무제표
        - corp_code="00126380", bsns_year="2024" → 해당 기업 2024년 재무제표
        - company_name="네이버" (bsns_year 없음) → 네이버 최근 연도 재무제표 자동 조회
    """
    # corp_code가 없으면 company_name으로 검색
    if not corp_code and company_name:
        logger.debug("corp_code not provided, searching by company_name: %s", company_name)
        search_result = search_company(company_name, arguments)
        
        if "error" in search_result:
            return {"error": f"기업 검색 실패: {search_result['error']}"}
        
        companies = search_result.get("companies", [])
        if not companies:
            return {"error": f"'{company_name}'에 해당하는 기업을 찾을 수 없습니다."}
        
        # 정확한 매칭 우선, 없으면 첫 번째 결과 사용
        # stock_code가 있는 상장기업 우선 선택
        exact_match = None
        listed_exact_match = None
        listed_first = None
        
        for company in companies:
            corp_name = company.get("corp_name", "").strip()
            stock_code = company.get("stock_code", "").strip()
            is_exact = corp_name == company_name.strip()
            is_listed = stock_code and stock_code != " "
            
            if is_exact and is_listed:
                listed_exact_match = company
            elif is_exact:
                exact_match = company
            elif is_listed and not listed_first:
                listed_first = company
        
        # 우선순위: 상장기업 정확매칭 > 정확매칭 > 상장기업 첫번째 > 첫번째
        selected_company = (listed_exact_match or exact_match or listed_first or companies[0])
        corp_code = selected_company.get("corp_code")
        found_name = selected_company.get("corp_name", "")
        stock_code = selected_company.get("stock_code", "")
        logger.debug("Found company: %s (corp_code: %s, stock_code: %s)", found_name, corp_code, stock_code)
        
        if not corp_code:
            return {"error": f"'{company_name}'의 corp_code를 찾을 수 없습니다."}
    
    if not corp_code:
        return {"error": "corp_code 또는 company_name 중 하나는 필수입니다."}
    
    # corp_code 검증 및 정규화
    is_valid, error_msg = validate_corp_code(corp_code)
    if not is_valid:
        return {"error": f"corp_code 검증 실패: {error_msg}"}
    
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    logger.debug("Normalized corp_code: %s", corp_code)
    
    # bsns_year 검증
    if bsns_year:
        is_valid, error_msg = validate_bsns_year(bsns_year)
        if not is_valid:
            return {"error": f"bsns_year 검증 실패: {error_msg}"}
    
    logger.debug("get_financial_statement called | corp_code=%s bsns_year=%s", corp_code, bsns_year)
    
    # 캐시 키 생성 (arguments 제외)
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)
    cache_key = (corp_code, bsns_year, reprt_code)
    
    # 실패 캐시 확인
    failure_key = f"failure:{cache_key}"
    if failure_key in failure_cache:
        logger.debug("Failure cache hit, skipping request | corp_code=%s", corp_code)
        return failure_cache[failure_key]
    
    if cache_key in financial_cache:
        logger.debug("Cache hit for financial statement | corp_code=%s", corp_code)
        return financial_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 재무제표 조회
    api_url = f"{DART_API_URL}/fnlttSinglAcnt.json"
    
    # 여러 연도 시도 (bsns_year가 지정되어도 실패 시 다른 연도 시도)
    years_to_try = []
    if bsns_year:
        # 지정된 연도를 먼저 시도하고, 실패 시 최근 3년도 시도
        current_year = datetime.now().year
        years_to_try = [bsns_year] + [str(current_year - i - 1) for i in range(3) if str(current_year - i - 1) != bsns_year]
    else:
        # 최근 3년 시도
        current_year = datetime.now().year
        years_to_try = [str(current_year - 1), str(current_year - 2), str(current_year - 3)]
    
    last_error = None
    for year in years_to_try:
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
            "fs_div": "CFS",  # 연결재무제표
        }
        
        logger.debug("DART API request | url=%s params=%s", api_url, {k: v if k != "crtfc_key" else v[:6] + "***" for k, v in params.items()})
        
        try:
            response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
            data = response.json()
            
            # 응답 데이터 검증
            if not isinstance(data, dict):
                logger.error("Invalid response format: expected dict, got %s", type(data))
                last_error = f"{year}년도: API 응답 형식이 올바르지 않습니다."
                continue
            
            error_status = data.get("status", "unknown")
            error_msg = data.get("message", "알 수 없는 오류")
            logger.debug("DART API response | corp_code=%s year=%s status=%s message=%s", 
                        corp_code, year, error_status, error_msg)
            
            if error_status == "000":
                result_data = data.get("list", [])
                if result_data:  # 데이터가 있는 경우만 반환
                    result = {
                        "corp_code": corp_code,
                        "bsns_year": year,
                        "reprt_code": reprt_code,
                        "financial_data": result_data
                    }
                    logger.debug("Financial statement retrieved | year=%s items=%d", year, len(result_data))
                    # 캐시에 저장
                    financial_cache[(corp_code, year, reprt_code)] = result
                    return result
                else:
                    logger.debug("No data in response for year %s (status=000 but list is empty), trying next year", year)
                    last_error = f"{year}년도: 응답은 성공했지만 데이터가 없습니다."
                    continue
            else:
                logger.debug("DART API error for year %s | status=%s message=%s", year, error_status, error_msg)
                # "013"은 데이터 없음, 다른 오류는 그대로 전달
                if error_status == "013":
                    last_error = f"{year}년도: 조회된 데이터가 없습니다."
                else:
                    last_error = f"{year}년도: {error_msg} (status: {error_status})"
                continue
                
        except requests.exceptions.RequestException as e:
            logger.debug("Request failed for year %s: %s", year, str(e))
            last_error = f"API 요청 실패: {str(e)} (네트워크 오류로 인해 재시도했지만 실패했습니다.)"
            continue
    
    # 모든 연도 시도 실패 - 실패 캐시에 저장 (5분)
    error_result = {"error": f"재무제표 조회 실패: {last_error or '모든 연도에서 데이터를 찾을 수 없습니다.'}"}
    failure_cache[failure_key] = error_result
    return error_result


def get_public_disclosure(corp_code: str, bgn_de: Optional[str] = None, end_de: Optional[str] = None, page_no: int = 1, page_count: int = 10, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 공시정보를 조회합니다. (DART API)
    
    기업이 공시한 주요사항보고서, 정기보고서 등의 공시 정보를 조회합니다.
    
    중요: corp_code는 필수 파라미터입니다. company_name만 있는 경우 먼저 search_company를 호출하여 corp_code를 얻어야 합니다.
    
    Args:
        corp_code: 기업 고유번호 (필수, 8자리 문자열, 예: "00126380")
                  company_name만 있는 경우: 먼저 search_company로 검색하여 corp_code를 얻어야 함
        bgn_de: 시작일 (YYYYMMDD 형식 문자열, 예: "20240101")
               기본값: None (자동으로 최근 30일로 설정)
               지정하지 않으면 오늘로부터 30일 전이 자동으로 설정됨
        end_de: 종료일 (YYYYMMDD 형식 문자열, 예: "20241231")
               기본값: None (자동으로 오늘 날짜로 설정)
        page_no: 페이지 번호 (기본값: 1, 1부터 시작)
        page_count: 페이지당 건수 (기본값: 10, 최대: 100)
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        공시정보 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "total_count": 전체 공시 건수,
            "page_no": 페이지 번호,
            "page_count": 페이지당 건수,
            "disclosures": [
                {
                    "rcept_no": "접수번호",
                    "corp_cls": "법인구분",
                    "corp_name": "회사명",
                    "report_nm": "보고서명",
                    "rcept_dt": "접수일자",
                    ...
                },
                ...
            ]
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - corp_code="00126380", bgn_de="20240101", end_de="20241231" → 2024년 전체 공시
        - corp_code="00126380" (날짜 없음) → 최근 30일 공시
    """
    logger.debug("get_public_disclosure called | corp_code=%s", corp_code)
    
    # corp_code 검증
    is_valid, error_msg = validate_corp_code(corp_code)
    if not is_valid:
        return {"error": f"corp_code 검증 실패: {error_msg}"}
    
    # corp_code 정규화
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    
    # 기본값 설정
    if not end_de:
        end_de = datetime.now().strftime("%Y%m%d")
    if not bgn_de:
        bgn_de = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    # 날짜 형식 검증
    try:
        datetime.strptime(bgn_de, "%Y%m%d")
        datetime.strptime(end_de, "%Y%m%d")
    except ValueError:
        return {"error": f"날짜 형식이 올바르지 않습니다. YYYYMMDD 형식이어야 합니다. (bgn_de: {bgn_de}, end_de: {end_de})"}
    
    # 캐시 키 생성 (arguments 제외)
    cache_key = (corp_code, bgn_de, end_de, page_no, page_count)
    failure_key = f"failure:disclosure:{cache_key}"
    if failure_key in failure_cache:
        logger.debug("Failure cache hit, skipping request | corp_code=%s", corp_code)
        return failure_cache[failure_key]
    
    if cache_key in disclosure_cache:
        logger.debug("Cache hit for public disclosure | corp_code=%s", corp_code)
        return disclosure_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 공시정보 조회
    api_url = f"{DART_API_URL}/list.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_no": page_no,
        "page_count": page_count,
    }
    
    try:
        response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
        data = response.json()
        
        # 응답 데이터 검증
        if not isinstance(data, dict):
            error_result = {"error": "API 응답 형식이 올바르지 않습니다."}
            failure_cache[failure_key] = error_result
            return error_result
        
        if data.get("status") == "000":
            result = {
                "corp_code": corp_code,
                "total_count": data.get("total_count", 0),
                "page_no": page_no,
                "page_count": page_count,
                "disclosures": data.get("list", [])
            }
            logger.debug("Public disclosure retrieved | total=%d returned=%d", 
                        data.get("total_count", 0), len(data.get("list", [])))
            # 캐시에 저장
            disclosure_cache[cache_key] = result
            return result
        else:
            error_result = {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')} (status: {data.get('status', 'unknown')})"}
            failure_cache[failure_key] = error_result
            return error_result
        
    except requests.exceptions.RequestException as e:
        logger.exception("Public disclosure API request failed: %s", str(e))
        error_result = {"error": f"API 요청 실패: {str(e)} (네트워크 오류로 인해 재시도했지만 실패했습니다.)"}
        failure_cache[failure_key] = error_result
        return error_result
    except Exception as e:
        logger.exception("Public disclosure error: %s", str(e))
        error_result = {"error": f"공시정보 조회 중 오류 발생: {str(e)}"}
        failure_cache[failure_key] = error_result
        return error_result


def analyze_financial_trend(corp_code: str, years: int = 5, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 재무 추이를 분석합니다. (최근 N년)
    
    여러 연도의 재무제표를 수집하여 재무 추이를 분석합니다.
    각 연도별 재무 데이터를 반환하므로 AI가 추가 분석(성장률, 추세 등)을 수행할 수 있습니다.
    
    중요: corp_code는 필수 파라미터입니다. company_name만 있는 경우 먼저 search_company를 호출하여 corp_code를 얻어야 합니다.
    
    Args:
        corp_code: 기업 고유번호 (필수, 8자리 문자열, 예: "00126380")
                  company_name만 있는 경우: 먼저 search_company로 검색하여 corp_code를 얻어야 함
        years: 분석할 연수 (기본값: 5, 최대: 10)
              예: 5 → 최근 5년간의 재무제표 수집
              현재 연도 기준으로 과거 N년간의 데이터를 수집
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        재무 추이 분석 결과 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "years_analyzed": 실제 수집된 연수,
            "financial_trend": [
                {
                    "year": "연도 (예: '2023')",
                    "data": [재무제표 데이터 배열]
                },
                ...
            ],
            "summary": "요약 메시지"
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - corp_code="00126380", years=3 → 최근 3년간 재무 추이
        - corp_code="00126380", years=10 → 최근 10년간 재무 추이 (최대)
    """
    logger.debug("analyze_financial_trend called | corp_code=%s years=%d", corp_code, years)
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    current_year = datetime.now().year
    financial_data = []
    
    for i in range(years):
        year = str(current_year - i - 1)
        result = get_financial_statement(corp_code=corp_code, bsns_year=year, reprt_code="11011", arguments=arguments)
        
        if "error" not in result:
            financial_data.append({
                "year": year,
                "data": result.get("financial_data", [])
            })
    
    # 간단한 추이 분석
    analysis = {
        "corp_code": corp_code,
        "years_analyzed": len(financial_data),
        "financial_trend": financial_data,
        "summary": "재무 추이 데이터가 수집되었습니다. AI가 추가 분석을 수행할 수 있습니다."
    }
    
    logger.debug("Financial trend analysis completed | years=%d", len(financial_data))
    return analysis


def get_company_overview(corp_code: Optional[str] = None, company_name: Optional[str] = None, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 기본정보를 조회합니다. (DART API - DS003)
    
    회사명, 대표자명, 설립일, 본사주소, 사업자등록번호 등 기업의 기본 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 기본정보 조회
    - company_name만 제공되면: 먼저 search_company로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        기업 기본정보 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "company_info": {
                "corp_name": "회사명",
                "corp_cls": "법인구분",
                "stock_code": "종목코드",
                "modify_date": "수정일자",
                ...
            }
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - company_name="삼성전자" → 삼성전자 기본정보 조회
        - corp_code="00126380" → 해당 기업 기본정보 조회
    """
    # corp_code가 없으면 company_name으로 검색
    if not corp_code and company_name:
        logger.debug("corp_code not provided, searching by company_name: %s", company_name)
        search_result = search_company(company_name, arguments)
        
        if "error" in search_result:
            return {"error": f"기업 검색 실패: {search_result['error']}"}
        
        companies = search_result.get("companies", [])
        if not companies:
            return {"error": f"'{company_name}'에 해당하는 기업을 찾을 수 없습니다."}
        
        # 상장기업 우선 선택
        selected_company = None
        for company in companies:
            stock_code = company.get("stock_code", "").strip()
            if stock_code and stock_code != " ":
                selected_company = company
                break
        
        if not selected_company:
            selected_company = companies[0]
        
        corp_code = selected_company.get("corp_code")
        found_name = selected_company.get("corp_name", "")
        logger.debug("Found company: %s (corp_code: %s)", found_name, corp_code)
        
        if not corp_code:
            return {"error": f"'{company_name}'의 corp_code를 찾을 수 없습니다."}
    
    if not corp_code:
        return {"error": "corp_code 또는 company_name 중 하나는 필수입니다."}
    
    # corp_code 검증 및 정규화
    is_valid, error_msg = validate_corp_code(corp_code)
    if not is_valid:
        return {"error": f"corp_code 검증 실패: {error_msg}"}
    
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    
    logger.debug("get_company_overview called | corp_code=%s", corp_code)
    
    # 캐시 확인
    cache_key = corp_code
    failure_key = f"failure:overview:{cache_key}"
    if failure_key in failure_cache:
        logger.debug("Failure cache hit, skipping request | corp_code=%s", corp_code)
        return failure_cache[failure_key]
    
    if cache_key in company_overview_cache:
        logger.debug("Cache hit for company overview | corp_code=%s", corp_code)
        return company_overview_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 기업 기본정보 조회
    api_url = f"{DART_API_URL}/company.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
    }
    
    try:
        response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
        data = response.json()
        
        # 응답 데이터 검증
        if not isinstance(data, dict):
            error_result = {"error": "API 응답 형식이 올바르지 않습니다."}
            failure_cache[failure_key] = error_result
            return error_result
        
        if data.get("status") == "000":
            result = {
                "corp_code": corp_code,
                "company_info": data
            }
            logger.debug("Company overview retrieved | corp_code=%s", corp_code)
            # 캐시에 저장
            company_overview_cache[cache_key] = result
            return result
        else:
            error_result = {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')} (status: {data.get('status', 'unknown')})"}
            failure_cache[failure_key] = error_result
            return error_result
        
    except requests.exceptions.RequestException as e:
        logger.exception("Company overview API request failed: %s", str(e))
        error_result = {"error": f"API 요청 실패: {str(e)} (네트워크 오류로 인해 재시도했지만 실패했습니다.)"}
        failure_cache[failure_key] = error_result
        return error_result
    except Exception as e:
        logger.exception("Company overview error: %s", str(e))
        error_result = {"error": f"기업정보 조회 중 오류 발생: {str(e)}"}
        failure_cache[failure_key] = error_result
        return error_result


def get_executives(corp_code: Optional[str] = None, company_name: Optional[str] = None,
                   bsns_year: Optional[str] = None, reprt_code: str = "11011",
                   arguments: Optional[dict] = None) -> Dict:
    """
    기업의 임원정보를 조회합니다. (DART API - DS003)
    
    임원명, 직책, 보수 등 임원진 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 임원정보 조회
    - company_name만 제공되면: 먼저 search_company로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 최근 연도로 설정)
                  지정하지 않으면 현재 월에 따라 자동 설정 (3월 이전이면 전년도)
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        임원정보 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "bsns_year": "사업연도",
            "reprt_code": "보고서 코드",
            "executives": [
                {
                    "nm": "임원명",
                    "ofcps": "직책",
                    "mendng_totamt": "보수총액",
                    ...
                },
                ...
            ]
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - company_name="삼성전자", bsns_year="2023" → 삼성전자 2023년 임원정보
        - corp_code="00126380" (bsns_year 없음) → 해당 기업 최근 연도 임원정보
    """
    # corp_code가 없으면 company_name으로 검색
    if not corp_code and company_name:
        logger.debug("corp_code not provided, searching by company_name: %s", company_name)
        search_result = search_company(company_name, arguments)
        
        if "error" in search_result:
            return {"error": f"기업 검색 실패: {search_result['error']}"}
        
        companies = search_result.get("companies", [])
        if not companies:
            return {"error": f"'{company_name}'에 해당하는 기업을 찾을 수 없습니다."}
        
        # 상장기업 우선 선택
        selected_company = None
        for company in companies:
            stock_code = company.get("stock_code", "").strip()
            if stock_code and stock_code != " ":
                selected_company = company
                break
        
        if not selected_company:
            selected_company = companies[0]
        
        corp_code = selected_company.get("corp_code")
        found_name = selected_company.get("corp_name", "")
        logger.debug("Found company: %s (corp_code: %s)", found_name, corp_code)
        
        if not corp_code:
            return {"error": f"'{company_name}'의 corp_code를 찾을 수 없습니다."}
    
    if not corp_code:
        return {"error": "corp_code 또는 company_name 중 하나는 필수입니다."}
    
    # corp_code 정규화
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    
    # bsns_year 기본값 설정 (최근 연도)
    if not bsns_year:
        current_year = datetime.now().year
        # 3월 이전이면 전년도로 설정
        if datetime.now().month < 3:
            bsns_year = str(current_year - 1)
        else:
            bsns_year = str(current_year)
    
    logger.debug("get_executives called | corp_code=%s bsns_year=%s reprt_code=%s", corp_code, bsns_year, reprt_code)
    
    # 캐시 확인
    cache_key = (corp_code, bsns_year, reprt_code)
    failure_key = f"failure:executives:{cache_key}"
    if failure_key in failure_cache:
        logger.debug("Failure cache hit, skipping request | corp_code=%s", corp_code)
        return failure_cache[failure_key]
    
    if cache_key in executives_cache:
        logger.debug("Cache hit for executives | corp_code=%s", corp_code)
        return executives_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 임원정보 조회
    api_url = f"{DART_API_URL}/empSttus.json"
    
    # 여러 연도 시도 (bsns_year가 지정되어도 실패 시 다른 연도 시도)
    years_to_try = []
    if bsns_year:
        # 지정된 연도를 먼저 시도하고, 실패 시 최근 3년도 시도
        current_year = datetime.now().year
        years_to_try = [bsns_year] + [str(current_year - i - 1) for i in range(3) if str(current_year - i - 1) != bsns_year]
    else:
        # 최근 3년 시도
        current_year = datetime.now().year
        years_to_try = [str(current_year - 1), str(current_year - 2), str(current_year - 3)]
    
    last_error = None
    for year in years_to_try:
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
        }
        
        logger.debug("DART API request | url=%s params=%s", api_url, {k: v if k != "crtfc_key" else v[:6] + "***" for k, v in params.items()})
        
        try:
            response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
            data = response.json()
            
            # 응답 데이터 검증
            if not isinstance(data, dict):
                logger.error("Invalid response format: expected dict, got %s", type(data))
                last_error = f"{year}년도: API 응답 형식이 올바르지 않습니다."
                continue
            
            error_status = data.get("status", "unknown")
            error_msg = data.get("message", "알 수 없는 오류")
            logger.debug("DART API response | corp_code=%s year=%s status=%s message=%s", 
                        corp_code, year, error_status, error_msg)
            
            if error_status == "000":
                result_data = data.get("list", [])
                if result_data:  # 데이터가 있는 경우만 반환
                    result = {
                        "corp_code": corp_code,
                        "bsns_year": year,
                        "reprt_code": reprt_code,
                        "executives": result_data
                    }
                    logger.debug("Executives retrieved | year=%s items=%d", year, len(result_data))
                    # 캐시에 저장
                    executives_cache[(corp_code, year, reprt_code)] = result
                    return result
                else:
                    logger.debug("No data in response for year %s (status=000 but list is empty), trying next year", year)
                    last_error = f"{year}년도: 응답은 성공했지만 데이터가 없습니다."
                    continue
            else:
                logger.debug("DART API error for year %s | status=%s message=%s", year, error_status, error_msg)
                # "013"은 데이터 없음, 다른 오류는 그대로 전달
                if error_status == "013":
                    last_error = f"{year}년도: 조회된 데이터가 없습니다."
                else:
                    last_error = f"{year}년도: {error_msg} (status: {error_status})"
                continue
                
        except requests.exceptions.RequestException as e:
            logger.debug("Request failed for year %s: %s", year, str(e))
            last_error = f"API 요청 실패: {str(e)} (네트워크 오류로 인해 재시도했지만 실패했습니다.)"
            continue
    
    # 모든 연도 시도 실패 - 실패 캐시에 저장
    error_result = {"error": f"임원정보 조회 실패: {last_error or '모든 연도에서 데이터를 찾을 수 없습니다.'}"}
    failure_cache[failure_key] = error_result
    return error_result


def get_shareholders(corp_code: Optional[str] = None, company_name: Optional[str] = None,
                     bsns_year: Optional[str] = None, reprt_code: str = "11011",
                     arguments: Optional[dict] = None) -> Dict:
    """
    지분보고서를 조회합니다. (DART API - DS006)
    
    주주명, 보유지분, 지분비율 등 지분구조 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 지분보고서 조회
    - company_name만 제공되면: 먼저 search_company로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 전년도로 설정)
                  지정하지 않으면 현재 연도 - 1년이 자동으로 설정됨
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
        arguments: 추가 인자 (일반적으로 사용하지 않음)
        
    Returns:
        지분보고서 딕셔너리:
        {
            "corp_code": "기업 고유번호",
            "bsns_year": "사업연도",
            "reprt_code": "보고서 코드",
            "shareholders": [
                {
                    "stock_knd": "주식종류",
                    "nm": "주주명",
                    "bsis_posesn_stock_co": "기초보유주식수",
                    "bsis_posesn_stock_qota_rt": "기초보유지분율",
                    ...
                },
                ...
            ]
        }
        또는 {"error": "오류 메시지"} 형식
    
    사용 예시:
        - company_name="삼성전자", bsns_year="2023" → 삼성전자 2023년 지분구조
        - corp_code="00126380" (bsns_year 없음) → 해당 기업 전년도 지분구조
    """
    # corp_code가 없으면 company_name으로 검색
    if not corp_code and company_name:
        logger.debug("corp_code not provided, searching by company_name: %s", company_name)
        search_result = search_company(company_name, arguments)
        
        if "error" in search_result:
            return {"error": f"기업 검색 실패: {search_result['error']}"}
        
        companies = search_result.get("companies", [])
        if not companies:
            return {"error": f"'{company_name}'에 해당하는 기업을 찾을 수 없습니다."}
        
        # 상장기업 우선 선택
        selected_company = None
        for company in companies:
            stock_code = company.get("stock_code", "").strip()
            if stock_code and stock_code != " ":
                selected_company = company
                break
        
        if not selected_company:
            selected_company = companies[0]
        
        corp_code = selected_company.get("corp_code")
        found_name = selected_company.get("corp_name", "")
        logger.debug("Found company: %s (corp_code: %s)", found_name, corp_code)
        
        if not corp_code:
            return {"error": f"'{company_name}'의 corp_code를 찾을 수 없습니다."}
    
    if not corp_code:
        return {"error": "corp_code 또는 company_name 중 하나는 필수입니다."}
    
    # corp_code 정규화
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    
    # 기본값 설정
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)
    
    logger.debug("get_shareholders called | corp_code=%s bsns_year=%s", corp_code, bsns_year)
    
    # 캐시 확인
    cache_key = (corp_code, bsns_year, reprt_code)
    failure_key = f"failure:shareholders:{cache_key}"
    if failure_key in failure_cache:
        logger.debug("Failure cache hit, skipping request | corp_code=%s", corp_code)
        return failure_cache[failure_key]
    
    if cache_key in shareholders_cache:
        logger.debug("Cache hit for shareholders | corp_code=%s", corp_code)
        return shareholders_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 지분보고서 조회
    api_url = f"{DART_API_URL}/majorstock.json"
    
    # 여러 연도 시도 (bsns_year가 지정되어도 실패 시 다른 연도 시도)
    years_to_try = []
    if bsns_year:
        # 지정된 연도를 먼저 시도하고, 실패 시 최근 3년도 시도
        current_year = datetime.now().year
        years_to_try = [bsns_year] + [str(current_year - i - 1) for i in range(3) if str(current_year - i - 1) != bsns_year]
    else:
        # 최근 3년 시도
        current_year = datetime.now().year
        years_to_try = [str(current_year - 1), str(current_year - 2), str(current_year - 3)]
    
    last_error = None
    for year in years_to_try:
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
        }
        
        logger.debug("DART API request | url=%s params=%s", api_url, {k: v if k != "crtfc_key" else v[:6] + "***" for k, v in params.items()})
        
        try:
            response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
            data = response.json()
            
            # 응답 데이터 검증
            if not isinstance(data, dict):
                logger.error("Invalid response format: expected dict, got %s", type(data))
                last_error = f"{year}년도: API 응답 형식이 올바르지 않습니다."
                continue
            
            error_status = data.get("status", "unknown")
            error_msg = data.get("message", "알 수 없는 오류")
            logger.debug("DART API response | corp_code=%s year=%s status=%s message=%s", 
                        corp_code, year, error_status, error_msg)
            
            if error_status == "000":
                result_data = data.get("list", [])
                if result_data:  # 데이터가 있는 경우만 반환
                    result = {
                        "corp_code": corp_code,
                        "bsns_year": year,
                        "reprt_code": reprt_code,
                        "shareholders": result_data
                    }
                    logger.debug("Shareholders retrieved | year=%s items=%d", year, len(result_data))
                    # 캐시에 저장
                    shareholders_cache[(corp_code, year, reprt_code)] = result
                    return result
                else:
                    logger.debug("No data in response for year %s (status=000 but list is empty), trying next year", year)
                    last_error = f"{year}년도: 응답은 성공했지만 데이터가 없습니다."
                    continue
            else:
                logger.debug("DART API error for year %s | status=%s message=%s", year, error_status, error_msg)
                # "013"은 데이터 없음, 다른 오류는 그대로 전달
                if error_status == "013":
                    last_error = f"{year}년도: 조회된 데이터가 없습니다."
                else:
                    last_error = f"{year}년도: {error_msg} (status: {error_status})"
                continue
                
        except requests.exceptions.RequestException as e:
            logger.debug("Request failed for year %s: %s", year, str(e))
            last_error = f"API 요청 실패: {str(e)} (네트워크 오류로 인해 재시도했지만 실패했습니다.)"
            continue
    
    # 모든 연도 시도 실패 - 실패 캐시에 저장
    error_result = {"error": f"지분보고서 조회 실패: {last_error or '모든 연도에서 데이터를 찾을 수 없습니다.'}"}
    failure_cache[failure_key] = error_result
    return error_result

