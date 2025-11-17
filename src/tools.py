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
major_report_cache = TTLCache(maxsize=100, ttl=86400)  # 24시간
document_cache = TTLCache(maxsize=50, ttl=86400)  # 24시간
executives_cache = TTLCache(maxsize=100, ttl=86400 * 7)  # 7일 (임원정보는 자주 변하지 않음)
shareholders_cache = TTLCache(maxsize=100, ttl=86400)  # 24시간


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


def search_company(query: str, arguments: Optional[dict] = None) -> Dict:
    """
    기업을 회사명으로 검색합니다. (DART API)
    DART의 corpCode.xml 파일을 사용하여 회사명으로 corp_code를 검색합니다.
    
    Args:
        query: 검색할 회사명
        arguments: 추가 인자
        
    Returns:
        검색 결과 딕셔너리
    """
    logger.debug("search_company called | query=%r", query)
    
    # 캐시 키 생성 (arguments 제외)
    cache_key = (query,)
    if cache_key in company_cache:
        logger.debug("Cache hit for company search | query=%r", query)
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
            query_lower = query.lower()
            
            # XML 구조에 따라 요소 찾기 (list 또는 다른 루트 요소)
            companies = root.findall(".//list") or root.findall("list")
            
            for company in companies:
                corp_name = company.findtext("corp_name", "")
                corp_code = company.findtext("corp_code", "")
                stock_code = company.findtext("stock_code", "")
                modify_date = company.findtext("modify_date", "")
                
                # 회사명에 검색어가 포함되어 있는지 확인
                if corp_name and query_lower in corp_name.lower():
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
            
            logger.debug("Company search results | query=%r total=%d", query, len(matching_companies))
            
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
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        bsns_year: 사업연도 (YYYY 형식, 기본값: 최근 연도)
        reprt_code: 보고서 코드 (11011: 사업보고서, 11013: 분기보고서)
        arguments: 추가 인자
        
    Returns:
        재무제표 정보 딕셔너리
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
    
    # corp_code를 8자리 문자열로 정규화 (앞에 0 패딩)
    # 검색 결과나 직접 입력 모두 정규화
    corp_code = str(corp_code).strip()
    if corp_code.isdigit():
        corp_code = corp_code.zfill(8)
    logger.debug("Normalized corp_code: %s", corp_code)
    
    logger.debug("get_financial_statement called | corp_code=%s bsns_year=%s", corp_code, bsns_year)
    
    # 캐시 키 생성 (arguments 제외)
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)
    cache_key = (corp_code, bsns_year, reprt_code)
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
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
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
            last_error = f"API 요청 실패: {str(e)}"
            continue
    
    # 모든 연도 시도 실패
    return {"error": f"재무제표 조회 실패: {last_error or '모든 연도에서 데이터를 찾을 수 없습니다.'}"}


def get_public_disclosure(corp_code: str, bgn_de: Optional[str] = None, end_de: Optional[str] = None, page_no: int = 1, page_count: int = 10, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 공시정보를 조회합니다. (DART API)
    
    Args:
        corp_code: 기업 고유번호
        bgn_de: 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
        end_de: 종료일 (YYYYMMDD 형식, 기본값: 오늘)
        page_no: 페이지 번호
        page_count: 페이지당 건수
        arguments: 추가 인자
        
    Returns:
        공시정보 딕셔너리
    """
    logger.debug("get_public_disclosure called | corp_code=%s", corp_code)
    
    # 기본값 설정
    if not end_de:
        end_de = datetime.now().strftime("%Y%m%d")
    if not bgn_de:
        bgn_de = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    # 캐시 키 생성 (arguments 제외)
    cache_key = (corp_code, bgn_de, end_de, page_no, page_count)
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
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
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
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("Public disclosure API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Public disclosure error: %s", str(e))
        return {"error": f"공시정보 조회 중 오류 발생: {str(e)}"}


def analyze_financial_trend(corp_code: str, years: int = 5, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 재무 추이를 분석합니다. (최근 N년)
    
    Args:
        corp_code: 기업 고유번호
        years: 분석할 연수 (기본값: 5)
        arguments: 추가 인자
        
    Returns:
        재무 추이 분석 결과 딕셔너리
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
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        arguments: 추가 인자
        
    Returns:
        기업 기본정보 딕셔너리
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
    
    logger.debug("get_company_overview called | corp_code=%s", corp_code)
    
    # 캐시 확인
    cache_key = corp_code
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
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
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
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("Company overview API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Company overview error: %s", str(e))
        return {"error": f"기업정보 조회 중 오류 발생: {str(e)}"}


def get_major_report(corp_code: Optional[str] = None, company_name: Optional[str] = None,
                     bgn_de: Optional[str] = None, end_de: Optional[str] = None,
                     arguments: Optional[dict] = None) -> Dict:
    """
    주요사항보고서를 조회합니다. (DART API - DS005)
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        bgn_de: 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
        end_de: 종료일 (YYYYMMDD 형식, 기본값: 오늘)
        arguments: 추가 인자
        
    Returns:
        주요사항보고서 딕셔너리
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
    if not end_de:
        end_de = datetime.now().strftime("%Y%m%d")
    if not bgn_de:
        bgn_de = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    logger.debug("get_major_report called | corp_code=%s bgn_de=%s end_de=%s", corp_code, bgn_de, end_de)
    
    # 캐시 확인
    cache_key = (corp_code, bgn_de, end_de)
    if cache_key in major_report_cache:
        logger.debug("Cache hit for major report | corp_code=%s", corp_code)
        return major_report_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 주요사항보고서 조회
    api_url = f"{DART_API_URL}/majorReport.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "000":
            result = {
                "corp_code": corp_code,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "reports": data.get("list", [])
            }
            logger.debug("Major report retrieved | corp_code=%s items=%d", corp_code, len(data.get("list", [])))
            # 캐시에 저장
            major_report_cache[cache_key] = result
            return result
        else:
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("Major report API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Major report error: %s", str(e))
        return {"error": f"주요사항보고서 조회 중 오류 발생: {str(e)}"}


def download_disclosure_document(rcept_no: str, file_format: str = "xml", arguments: Optional[dict] = None) -> Dict:
    """
    공시원문을 다운로드합니다. (DART API - DS004)
    
    Args:
        rcept_no: 접수번호 (공시정보에서 얻을 수 있음)
        file_format: 파일 형식 ("xml" 또는 "pdf", 기본값: "xml")
        arguments: 추가 인자
        
    Returns:
        공시원문 데이터 딕셔너리
    """
    logger.debug("download_disclosure_document called | rcept_no=%s format=%s", rcept_no, file_format)
    
    if file_format not in ["xml", "pdf"]:
        return {"error": "file_format은 'xml' 또는 'pdf'만 가능합니다."}
    
    # 캐시 확인
    cache_key = (rcept_no, file_format)
    if cache_key in document_cache:
        logger.debug("Cache hit for document | rcept_no=%s", rcept_no)
        return document_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 공시원문 다운로드
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
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                # XML을 딕셔너리로 변환 (간단한 구조만)
                def xml_to_dict(element):
                    result = {}
                    if element.text and element.text.strip():
                        result["text"] = element.text.strip()
                    if element.attrib:
                        result["attributes"] = element.attrib
                    for child in element:
                        child_data = xml_to_dict(child)
                        tag = child.tag
                        if tag in result:
                            if not isinstance(result[tag], list):
                                result[tag] = [result[tag]]
                            result[tag].append(child_data)
                        else:
                            result[tag] = child_data
                    return result
                
                parsed_data = xml_to_dict(root)
                
                result = {
                    "rcept_no": rcept_no,
                    "format": file_format,
                    "content": response.text,
                    "parsed": parsed_data,
                    "size": len(response.content)
                }
            except ET.ParseError as e:
                logger.warning("XML parsing failed, returning raw content: %s", str(e))
                result = {
                    "rcept_no": rcept_no,
                    "format": file_format,
                    "content": response.text,
                    "parsed": False,
                    "parse_error": str(e),
                    "size": len(response.content)
                }
        else:
            # PDF는 base64 인코딩
            import base64
            result = {
                "rcept_no": rcept_no,
                "format": file_format,
                "content_base64": base64.b64encode(response.content).decode('utf-8'),
                "size": len(response.content),
                "mime_type": "application/pdf"
            }
        
        logger.debug("Document downloaded | rcept_no=%s format=%s size=%d", rcept_no, file_format, len(response.content))
        # 캐시에 저장
        document_cache[cache_key] = result
        return result
        
    except requests.exceptions.RequestException as e:
        logger.exception("Document download API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Document download error: %s", str(e))
        return {"error": f"공시원문 다운로드 중 오류 발생: {str(e)}"}


def get_executives(corp_code: Optional[str] = None, company_name: Optional[str] = None, arguments: Optional[dict] = None) -> Dict:
    """
    기업의 임원정보를 조회합니다. (DART API - DS003)
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        arguments: 추가 인자
        
    Returns:
        임원정보 딕셔너리
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
    
    logger.debug("get_executives called | corp_code=%s", corp_code)
    
    # 캐시 확인
    cache_key = corp_code
    if cache_key in executives_cache:
        logger.debug("Cache hit for executives | corp_code=%s", corp_code)
        return executives_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 임원정보 조회
    api_url = f"{DART_API_URL}/empSttus.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "000":
            result = {
                "corp_code": corp_code,
                "executives": data.get("list", [])
            }
            logger.debug("Executives retrieved | corp_code=%s items=%d", corp_code, len(data.get("list", [])))
            # 캐시에 저장
            executives_cache[cache_key] = result
            return result
        else:
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("Executives API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Executives error: %s", str(e))
        return {"error": f"임원정보 조회 중 오류 발생: {str(e)}"}


def get_shareholders(corp_code: Optional[str] = None, company_name: Optional[str] = None,
                     bsns_year: Optional[str] = None, reprt_code: str = "11011",
                     arguments: Optional[dict] = None) -> Dict:
    """
    지분보고서를 조회합니다. (DART API - DS006)
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        bsns_year: 사업연도 (YYYY 형식, 기본값: 최근 연도)
        reprt_code: 보고서 코드 (11011: 사업보고서, 11013: 분기보고서)
        arguments: 추가 인자
        
    Returns:
        지분보고서 딕셔너리
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
    if cache_key in shareholders_cache:
        logger.debug("Cache hit for shareholders | corp_code=%s", corp_code)
        return shareholders_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["DART_API_KEY"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # DART API: 지분보고서 조회
    api_url = f"{DART_API_URL}/majorstock.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "000":
            result = {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code,
                "shareholders": data.get("list", [])
            }
            logger.debug("Shareholders retrieved | corp_code=%s items=%d", corp_code, len(data.get("list", [])))
            # 캐시에 저장
            shareholders_cache[cache_key] = result
            return result
        else:
            return {"error": f"DART API 오류: {data.get('message', '알 수 없는 오류')}"}
        
    except requests.exceptions.RequestException as e:
        logger.exception("Shareholders API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Shareholders error: %s", str(e))
        return {"error": f"지분보고서 조회 중 오류 발생: {str(e)}"}

