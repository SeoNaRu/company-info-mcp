#!/usr/bin/env python3
"""
Korean Company Information MCP Server using FastMCP
DART API를 활용한 기업정보 조회 서버 (무료 버전)
"""
import asyncio
import sys
import os
import logging
from fastmcp import FastMCP
from fastapi import FastAPI
from pydantic import BaseModel, Field
from .tools import (
    search_company,
    get_financial_statement,
    get_public_disclosure,
    analyze_financial_trend,
    get_company_overview,
    get_executives,
    get_shareholders
)
from typing import Optional
from dotenv import load_dotenv
from contextlib import contextmanager

# .env 파일 로드 (로컬 개발용 - 우선순위 2순위)
load_dotenv()  # arguments.env가 없을 때 fallback으로 사용

# FastAPI / FastMCP 앱 구성
api = FastAPI()
mcp_logger = logging.getLogger("company-mcp")
level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
mcp_logger.setLevel(level)
if not mcp_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    mcp_logger.addHandler(handler)
mcp_logger.propagate = True
mcp = FastMCP()


# Pydantic 모델 정의
class CompanySearchRequest(BaseModel):
    company_name: str = Field(..., description="검색할 회사명")


class FinancialStatementRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")
    bsns_year: Optional[str] = Field(None, description="사업연도 (YYYY 형식, 기본값: 최근 연도)")
    reprt_code: str = Field("11011", description="보고서 코드 (11011: 사업보고서, 11013: 분기보고서)")


class PublicDisclosureRequest(BaseModel):
    corp_code: str = Field(..., description="기업 고유번호")
    bgn_de: Optional[str] = Field(None, description="시작일 (YYYYMMDD 형식)")
    end_de: Optional[str] = Field(None, description="종료일 (YYYYMMDD 형식)")
    page_no: int = Field(1, description="페이지 번호", ge=1)
    page_count: int = Field(10, description="페이지당 건수", ge=1, le=100)


class FinancialTrendRequest(BaseModel):
    corp_code: str = Field(..., description="기업 고유번호")
    years: int = Field(5, description="분석할 연수", ge=1, le=10)


class CompanyOverviewRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")


class ExecutivesRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")
    bsns_year: Optional[str] = Field(None, description="사업연도 (YYYY 형식, 기본값: 최근 연도)")
    reprt_code: str = Field("11011", description="보고서 코드 (11011: 사업보고서, 11013: 분기보고서)")


class ShareholdersRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")
    bsns_year: Optional[str] = Field(None, description="사업연도 (YYYY 형식, 기본값: 최근 연도)")
    reprt_code: str = Field("11011", description="보고서 코드 (11011: 사업보고서, 11013: 분기보고서)")


# 실제 구현 함수들
async def search_company_impl(req: CompanySearchRequest, arguments: Optional[dict] = None):
    """기업 검색 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(search_company, req.company_name, arguments)
    except Exception as e:
        return {"error": f"기업 검색 중 오류가 발생했습니다: {str(e)}"}


async def get_financial_statement_impl(req: FinancialStatementRequest, arguments: Optional[dict] = None):
    """재무제표 조회 구현"""
    try:
        # arguments를 전달하여 API 키 등 크레덴셜 접근 가능하도록 함
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_financial_statement, 
            req.corp_code,
            req.company_name,
            req.bsns_year, 
            req.reprt_code,
            arguments
        )
    except Exception as e:
        mcp_logger.exception("Error in get_financial_statement_impl: %s", str(e))
        return {"error": f"재무제표 조회 중 오류가 발생했습니다: {str(e)}"}


async def get_public_disclosure_impl(req: PublicDisclosureRequest, arguments: Optional[dict] = None):
    """공시정보 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_public_disclosure,
            req.corp_code,
            req.bgn_de,
            req.end_de,
            req.page_no,
            req.page_count,
            arguments
        )
    except Exception as e:
        return {"error": f"공시정보 조회 중 오류가 발생했습니다: {str(e)}"}


async def analyze_financial_trend_impl(req: FinancialTrendRequest, arguments: Optional[dict] = None):
    """재무 추이 분석 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            analyze_financial_trend,
            req.corp_code,
            req.years,
            arguments
        )
    except Exception as e:
        return {"error": f"재무 추이 분석 중 오류가 발생했습니다: {str(e)}"}


async def get_company_overview_impl(req: CompanyOverviewRequest, arguments: Optional[dict] = None):
    """기업 기본정보 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_company_overview,
            req.corp_code,
            req.company_name,
            arguments
        )
    except Exception as e:
        return {"error": f"기업정보 조회 중 오류가 발생했습니다: {str(e)}"}


async def get_executives_impl(req: ExecutivesRequest, arguments: Optional[dict] = None, bsns_year: Optional[str] = None, reprt_code: str = "11011"):
    """임원정보 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        # req에서 가져오거나 파라미터로 받은 값 사용
        final_bsns_year = req.bsns_year if hasattr(req, 'bsns_year') and req.bsns_year else bsns_year
        final_reprt_code = req.reprt_code if hasattr(req, 'reprt_code') and req.reprt_code else reprt_code
        return await asyncio.to_thread(
            get_executives,
            req.corp_code,
            req.company_name,
            final_bsns_year,
            final_reprt_code,
            arguments
        )
    except Exception as e:
        return {"error": f"임원정보 조회 중 오류가 발생했습니다: {str(e)}"}


async def get_shareholders_impl(req: ShareholdersRequest, arguments: Optional[dict] = None):
    """지분보고서 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_shareholders,
            req.corp_code,
            req.company_name,
            req.bsns_year,
            req.reprt_code,
            arguments
        )
    except Exception as e:
        return {"error": f"지분보고서 조회 중 오류가 발생했습니다: {str(e)}"}


async def health_impl():
    """서비스 상태 확인 구현"""
    dart_key = os.environ.get("DART_API_KEY", "")
    return {
        "status": "ok",
        "environment": {
            "dart_api_key": "설정됨" if dart_key else "설정되지 않음"
        }
    }


# 일시 환경 변수 적용용 컨텍스트 매니저
@contextmanager
def temporary_env(overrides: dict):
    saved_values = {}
    try:
        for key, value in (overrides or {}).items():
            saved_values[key] = os.environ.get(key)
            if value is not None:
                os.environ[key] = str(value)
        yield
    finally:
        for key, original in saved_values.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


# HTTP 엔드포인트
@api.get("/health")
async def health_check_get():
    """HTTP GET 엔드포인트: 서비스 상태 확인"""
    return await health_impl()

@api.post("/health")
async def health_check_post():
    """HTTP POST 엔드포인트: 서비스 상태 확인"""
    return await health_impl()




# HTTP 엔드포인트: 도구 목록 조회
@api.get("/tools")
async def get_tools_http():
    """HTTP 엔드포인트: 사용 가능한 도구 목록 조회"""
    # FastMCP가 자동으로 생성한 도구 목록 반환
    try:
        # FastMCP의 내부 도구 목록 가져오기 (타입 체커 무시)
        tools_list = []
        server = getattr(mcp, 'server', None)  # type: ignore
        if server and hasattr(server, 'tools'):
            tools = getattr(server, 'tools', {})  # type: ignore
            for tool_name, tool in tools.items():
                tool_info = {
                    "name": tool_name,
                    "description": getattr(tool, 'description', '') or '',
                }
                # 파라미터 정보 추출
                if hasattr(tool, 'parameters'):
                    tool_info["parameters"] = getattr(tool, 'parameters', {})
                else:
                    tool_info["parameters"] = {}
                tools_list.append(tool_info)
        
        # HTTP 모드에서 FastMCP 내부 접근이 실패할 경우, 직접 정의된 도구 목록 반환
        if not tools_list:
            mcp_logger.warning("FastMCP tools not accessible, returning hardcoded tool list")
            tools_list = [
                {
                    "name": "search_company_tool",
                    "description": "기업명으로 기업을 검색합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {"type": "string", "description": "검색할 회사명"}
                        },
                        "required": ["company_name"]
                    }
                },
                {
                    "name": "get_company_overview_tool",
                    "description": "기업의 기본정보를 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "company_name": {"type": "string", "description": "회사명"}
                        }
                    }
                },
                {
                    "name": "get_financial_statement_tool",
                    "description": "기업의 재무제표를 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "company_name": {"type": "string", "description": "회사명"},
                            "bsns_year": {"type": "string", "description": "사업연도 (YYYY 형식)"},
                            "reprt_code": {"type": "string", "description": "보고서 코드 (11011: 사업보고서)"}
                        }
                    }
                },
                {
                    "name": "get_public_disclosure_tool",
                    "description": "기업의 공시정보를 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "bgn_de": {"type": "string", "description": "시작일 (YYYYMMDD)"},
                            "end_de": {"type": "string", "description": "종료일 (YYYYMMDD)"},
                            "page_no": {"type": "integer", "description": "페이지 번호"},
                            "page_count": {"type": "integer", "description": "페이지당 건수"}
                        },
                        "required": ["corp_code"]
                    }
                },
                {
                    "name": "analyze_financial_trend_tool",
                    "description": "기업의 재무 추이를 분석합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "years": {"type": "integer", "description": "분석할 연수"}
                        },
                        "required": ["corp_code"]
                    }
                },
                {
                    "name": "get_executives_tool",
                    "description": "기업의 임원정보를 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "company_name": {"type": "string", "description": "회사명"},
                            "bsns_year": {"type": "string", "description": "사업연도 (YYYY 형식)"},
                            "reprt_code": {"type": "string", "description": "보고서 코드 (11011: 사업보고서)"}
                        }
                    }
                },
                {
                    "name": "get_shareholders_tool",
                    "description": "기업의 지분보고서를 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "corp_code": {"type": "string", "description": "기업 고유번호"},
                            "company_name": {"type": "string", "description": "회사명"},
                            "bsns_year": {"type": "string", "description": "사업연도 (YYYY 형식)"},
                            "reprt_code": {"type": "string", "description": "보고서 코드 (11011: 사업보고서)"}
                        }
                    }
                }
            ]
        
        return tools_list
    except Exception as e:
        mcp_logger.exception("Error getting tools list: %s", str(e))
        return []


# HTTP 엔드포인트: 도구 호출
@api.post("/tools/{tool_name}")
async def call_tool_http(tool_name: str, request_data: dict):
    mcp_logger.debug("HTTP call_tool | tool=%s request=%s", tool_name, request_data)
    env = request_data.get("env", {}) if isinstance(request_data, dict) else {}

    async def run_sync(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    
    # 공통 타입 변환 함수들
    def convert_float_to_int(data: dict, keys: list):
        """지정된 키의 float 값을 int로 변환"""
        for key in keys:
            if key in data and isinstance(data[key], float):
                data[key] = int(data[key])
    
    def convert_to_str(data: dict, keys: list):
        """지정된 키의 값을 문자열로 변환"""
        for key in keys:
            if key in data and data[key] is not None and not isinstance(data[key], str):
                data[key] = str(data[key])

    try:
        # 크레덴셜 추출
        creds = {}
        if isinstance(env, dict):
            if "DART_API_KEY" in env:
                creds["DART_API_KEY"] = env["DART_API_KEY"]
        
        if creds:
            masked = dict(creds)
            for key in masked:
                if masked[key]:
                    masked[key] = masked[key][:6] + "***"
            mcp_logger.debug("Applying temp env | %s", masked)

        async def run_with_env(coro_func):
            with temporary_env(creds):
                return await coro_func

        if tool_name == "health":
            return await health_impl()

        if tool_name == "search_company_tool":
            company_name = request_data.get("company_name")
            if not company_name:
                return {"error": "Missing required parameter: company_name"}
            return await run_with_env(
                run_sync(search_company, company_name, arguments=request_data)
            )

        if tool_name == "get_financial_statement_tool":
            corp_code = request_data.get("corp_code")
            company_name = request_data.get("company_name")
            if not corp_code and not company_name:
                return {"error": "Missing required parameter: corp_code or company_name"}
            # 타입 변환: 문자열로 변환
            convert_to_str(request_data, ["bsns_year", "reprt_code"])
            bsns_year = request_data.get("bsns_year")
            reprt_code = request_data.get("reprt_code", "11011")
            return await run_with_env(
                run_sync(get_financial_statement, corp_code, company_name, bsns_year, reprt_code, arguments=request_data)
            )

        if tool_name == "get_public_disclosure_tool":
            corp_code = request_data.get("corp_code")
            if not corp_code:
                return {"error": "Missing required parameter: corp_code"}
            bgn_de = request_data.get("bgn_de")
            end_de = request_data.get("end_de")
            page_no = request_data.get("page_no", 1)
            page_count = request_data.get("page_count", 10)
            if isinstance(page_no, float):
                page_no = int(page_no)
            if isinstance(page_count, float):
                page_count = int(page_count)
            return await run_with_env(
                run_sync(get_public_disclosure, corp_code, bgn_de, end_de, page_no, page_count, arguments=request_data)
            )

        if tool_name == "analyze_financial_trend_tool":
            corp_code = request_data.get("corp_code")
            if not corp_code:
                return {"error": "Missing required parameter: corp_code"}
            years = request_data.get("years", 5)
            if isinstance(years, float):
                years = int(years)
            return await run_with_env(
                run_sync(analyze_financial_trend, corp_code, years, arguments=request_data)
            )

        if tool_name == "get_company_overview_tool":
            corp_code = request_data.get("corp_code")
            company_name = request_data.get("company_name")
            if not corp_code and not company_name:
                return {"error": "Missing required parameter: corp_code or company_name"}
            return await run_with_env(
                run_sync(get_company_overview, corp_code, company_name, arguments=request_data)
            )

        if tool_name == "get_executives_tool":
            corp_code = request_data.get("corp_code")
            company_name = request_data.get("company_name")
            if not corp_code and not company_name:
                return {"error": "Missing required parameter: corp_code or company_name"}
            # 타입 변환: 문자열로 변환
            convert_to_str(request_data, ["bsns_year", "reprt_code"])
            bsns_year = request_data.get("bsns_year")
            reprt_code = request_data.get("reprt_code", "11011")
            return await run_with_env(
                run_sync(get_executives, corp_code, company_name, bsns_year, reprt_code, arguments=request_data)
            )

        if tool_name == "get_shareholders_tool":
            corp_code = request_data.get("corp_code")
            company_name = request_data.get("company_name")
            if not corp_code and not company_name:
                return {"error": "Missing required parameter: corp_code or company_name"}
            # 타입 변환: 문자열로 변환
            convert_to_str(request_data, ["bsns_year", "reprt_code"])
            bsns_year = request_data.get("bsns_year")
            reprt_code = request_data.get("reprt_code", "11011")
            return await run_with_env(
                run_sync(get_shareholders, corp_code, company_name, bsns_year, reprt_code, arguments=request_data)
            )

        return {"error": "Tool not found"}
    except Exception as e:
        mcp_logger.exception("Error in call_tool_http: %s", str(e))
        return {"error": f"Error calling tool: {str(e)}"}


# MCP 도구 정의
@mcp.tool()
async def health():
    """서비스 상태 확인"""
    return await health_impl()


@mcp.tool()
async def search_company_tool(company_name: str):
    """
    기업을 회사명으로 검색합니다.
    
    이 도구는 다른 도구들에서 company_name만 있고 corp_code가 없을 때 먼저 호출되어야 합니다.
    검색 결과에서 corp_code를 얻은 후 다른 도구들(get_financial_statement_tool, get_company_overview_tool 등)을 호출할 수 있습니다.
    
    중요: 부분 일치 검색이 가능합니다. 예를 들어 "삼성"을 입력하면 "삼성전자", "삼성SDI" 등이 검색됩니다.
    검색 결과가 여러 개일 경우, stock_code가 있는 상장기업을 우선 선택하거나 정확한 회사명과 일치하는 것을 선택해야 합니다.
    
    Args:
        company_name: 검색할 회사명 (필수, 예: '삼성전자', '네이버', '카카오')
                     부분 일치 검색이 가능합니다 (예: "삼성" 입력 시 "삼성전자", "삼성SDI" 등이 검색됨)
    
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
        - company_name="삼성전자" → 삼성전자 검색
        - company_name="네이버" → 네이버 관련 기업 검색
        - 검색 결과가 여러 개일 경우, stock_code가 있는 상장기업을 우선 선택하거나
          정확한 회사명과 일치하는 것을 선택해야 함
    """
    req = CompanySearchRequest(company_name=company_name)
    return await search_company_impl(req, None)


@mcp.tool()
async def get_financial_statement_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011"
):
    """
    기업의 재무제표를 조회합니다.
    
    손익계산서, 재무상태표, 현금흐름표 등의 재무 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 재무제표 조회
    - company_name만 제공되면: 먼저 search_company_tool로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company_tool를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업 우선, 정확한 이름 일치 우선으로 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 최근 연도부터 시도)
                  지정하지 않으면 최근 3년도 중 데이터가 있는 연도를 자동으로 찾음
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
    
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
    req = FinancialStatementRequest(
        corp_code=corp_code,
        company_name=company_name,
        bsns_year=bsns_year,
        reprt_code=reprt_code
    )
    return await get_financial_statement_impl(req, None)


@mcp.tool()
async def get_public_disclosure_tool(
    corp_code: str,
    bgn_de: Optional[str] = None,
    end_de: Optional[str] = None,
    page_no: int = 1,
    page_count: int = 10
):
    """
    기업의 공시정보를 조회합니다.
    
    기업이 공시한 주요사항보고서, 정기보고서 등의 공시 정보를 조회합니다.
    
    중요: corp_code는 필수 파라미터입니다. company_name만 있는 경우 먼저 search_company_tool를 호출하여 corp_code를 얻어야 합니다.
    
    Args:
        corp_code: 기업 고유번호 (필수, 8자리 문자열, 예: "00126380")
                  company_name만 있는 경우: 먼저 search_company_tool로 검색하여 corp_code를 얻어야 함
        bgn_de: 시작일 (YYYYMMDD 형식 문자열, 예: "20240101")
               기본값: None (자동으로 최근 30일로 설정)
               지정하지 않으면 오늘로부터 30일 전이 자동으로 설정됨
        end_de: 종료일 (YYYYMMDD 형식 문자열, 예: "20241231")
               기본값: None (자동으로 오늘 날짜로 설정)
        page_no: 페이지 번호 (기본값: 1, 1부터 시작)
        page_count: 페이지당 건수 (기본값: 10, 최대: 100)
    
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
    req = PublicDisclosureRequest(
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        page_no=page_no,
        page_count=page_count
    )
    return await get_public_disclosure_impl(req, None)


@mcp.tool()
async def analyze_financial_trend_tool(
    corp_code: str,
    years: int = 5
):
    """
    기업의 재무 추이를 분석합니다. (최근 N년)
    
    여러 연도의 재무제표를 수집하여 재무 추이를 분석합니다.
    각 연도별 재무 데이터를 반환하므로 AI가 추가 분석(성장률, 추세 등)을 수행할 수 있습니다.
    
    중요: corp_code는 필수 파라미터입니다. company_name만 있는 경우 먼저 search_company_tool를 호출하여 corp_code를 얻어야 합니다.
    
    Args:
        corp_code: 기업 고유번호 (필수, 8자리 문자열, 예: "00126380")
                  company_name만 있는 경우: 먼저 search_company_tool로 검색하여 corp_code를 얻어야 함
        years: 분석할 연수 (기본값: 5, 최대: 10)
              예: 5 → 최근 5년간의 재무제표 수집
              현재 연도 기준으로 과거 N년간의 데이터를 수집
    
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
    req = FinancialTrendRequest(corp_code=corp_code, years=years)
    return await analyze_financial_trend_impl(req, None)


@mcp.tool()
async def get_company_overview_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None
):
    """
    기업의 기본정보를 조회합니다.
    
    회사명, 대표자명, 설립일, 본사주소, 사업자등록번호 등 기업의 기본 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 기본정보 조회
    - company_name만 제공되면: 먼저 search_company_tool로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company_tool를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
    
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
    req = CompanyOverviewRequest(
        corp_code=corp_code,
        company_name=company_name
    )
    return await get_company_overview_impl(req, None)


@mcp.tool()
async def get_executives_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011"
):
    """
    기업의 임원정보를 조회합니다.
    
    임원명, 직책, 보수 등 임원진 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 임원정보 조회
    - company_name만 제공되면: 먼저 search_company_tool로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company_tool를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 최근 연도로 설정)
                  지정하지 않으면 현재 월에 따라 자동 설정 (3월 이전이면 전년도)
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
    
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
    req = ExecutivesRequest(
        corp_code=corp_code,
        company_name=company_name,
        bsns_year=bsns_year,
        reprt_code=reprt_code
    )
    return await get_executives_impl(req, None, bsns_year, reprt_code)


@mcp.tool()
async def get_shareholders_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011"
):
    """
    지분보고서를 조회합니다.
    
    주주명, 보유지분, 지분비율 등 지분구조 정보를 조회합니다.
    
    중요: corp_code 또는 company_name 중 하나는 반드시 제공해야 합니다.
    - corp_code가 제공되면: 바로 지분보고서 조회
    - company_name만 제공되면: 먼저 search_company_tool로 검색하여 corp_code를 찾은 후 조회
    - 둘 다 제공되면: corp_code를 우선 사용
    
    Args:
        corp_code: 기업 고유번호 (8자리 문자열, 예: "00126380")
                  corp_code 또는 company_name 중 하나 필수
                  company_name이 제공되면 이 값은 무시됨
        company_name: 회사명 (예: "삼성전자", "네이버", "카카오")
                     corp_code가 없을 때 사용
                     제공되면 내부적으로 search_company_tool를 호출하여 corp_code를 찾음
                     여러 검색 결과가 나오면 상장기업을 우선 선택
        bsns_year: 사업연도 (YYYY 형식 문자열, 예: "2023", "2024")
                  기본값: None (자동으로 전년도로 설정)
                  지정하지 않으면 현재 연도 - 1년이 자동으로 설정됨
        reprt_code: 보고서 코드 (기본값: "11011")
                   "11011": 사업보고서 (연간, 권장)
                   "11013": 분기보고서 (분기)
    
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
    req = ShareholdersRequest(
        corp_code=corp_code,
        company_name=company_name,
        bsns_year=bsns_year,
        reprt_code=reprt_code
    )
    return await get_shareholders_impl(req, None)


async def main():
    """MCP 서버를 실행합니다."""
    print("MCP Korean Company Information Server starting...", file=sys.stderr)
    print("Server: company-info-service", file=sys.stderr)
    print("Available tools: health, search_company_tool, get_financial_statement_tool, get_public_disclosure_tool, analyze_financial_trend_tool, get_company_overview_tool, get_executives_tool, get_shareholders_tool", file=sys.stderr)
    
    try:
        await mcp.run_stdio_async()
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    # MCP 서버로 실행 (stdio 모드)
    # HTTP 서버로 실행하려면 환경 변수 HTTP_MODE=1 설정
    if os.environ.get("HTTP_MODE") == "1":
        import uvicorn
        port = int(os.environ.get('PORT', 8097))
        uvicorn.run("src.main:api", host="0.0.0.0", port=port, reload=False)
    else:
        # MCP stdio 모드
        asyncio.run(main())

