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
    get_major_report,
    download_disclosure_document,
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
    query: str = Field(..., description="검색할 회사명")


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


class MajorReportRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")
    bgn_de: Optional[str] = Field(None, description="시작일 (YYYYMMDD 형식)")
    end_de: Optional[str] = Field(None, description="종료일 (YYYYMMDD 형식)")


class DocumentDownloadRequest(BaseModel):
    rcept_no: str = Field(..., description="접수번호")
    file_format: str = Field("xml", description="파일 형식 (xml 또는 pdf)")


class ExecutivesRequest(BaseModel):
    corp_code: Optional[str] = Field(None, description="기업 고유번호 (corp_code 또는 company_name 중 하나 필수)")
    company_name: Optional[str] = Field(None, description="회사명 (corp_code가 없을 경우 사용)")


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
        return await asyncio.to_thread(search_company, req.query, arguments)
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


async def get_major_report_impl(req: MajorReportRequest, arguments: Optional[dict] = None):
    """주요사항보고서 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_major_report,
            req.corp_code,
            req.company_name,
            req.bgn_de,
            req.end_de,
            arguments
        )
    except Exception as e:
        return {"error": f"주요사항보고서 조회 중 오류가 발생했습니다: {str(e)}"}


async def download_disclosure_document_impl(req: DocumentDownloadRequest, arguments: Optional[dict] = None):
    """공시원문 다운로드 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            download_disclosure_document,
            req.rcept_no,
            req.file_format,
            arguments
        )
    except Exception as e:
        return {"error": f"공시원문 다운로드 중 오류가 발생했습니다: {str(e)}"}


async def get_executives_impl(req: ExecutivesRequest, arguments: Optional[dict] = None):
    """임원정보 조회 구현"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            get_executives,
            req.corp_code,
            req.company_name,
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


async def health_impl(arguments: Optional[dict] = None):
    """서비스 상태 확인 구현"""
    # 우선순위 1: arguments.env에서 받기 (메인 서버에서 받은 키)
    env = {}
    if isinstance(arguments, dict) and "env" in arguments:
        env = arguments["env"]
    
    dart_key = ""
    key_source = "none"
    
    # 우선순위 1: arguments.env에서 받기
    if isinstance(env, dict) and "DART_API_KEY" in env:
        dart_key = env["DART_API_KEY"]
        key_source = "arguments.env"
    
    # 우선순위 2: .env 파일에서 받기 (로컬 개발용)
    if not dart_key:
        dart_key = os.environ.get("DART_API_KEY", "")
        if dart_key:
            key_source = ".env file"
    
    # 둘 다 없으면 에러 상태
    status = "ok" if dart_key else "error"
    status_message = "정상" if dart_key else "등록된 키가 없습니다"
    
    return {
        "status": status,
        "message": status_message,
        "service": "Korean Company Information MCP Server (Free Version)",
        "environment": {
            "dart_api_key": "설정됨" if dart_key else "설정되지 않음",
            "dart_key_preview": dart_key[:10] + "..." if dart_key else "None",
            "key_source": key_source
        },
        "note": "DART API를 사용하여 기업정보를 조회합니다. API 키 우선순위: 1) arguments.env.DART_API_KEY, 2) .env 파일"
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
async def health_check_post(request_data: Optional[dict] = None):
    """HTTP POST 엔드포인트: 서비스 상태 확인 (env 포함 가능)"""
    arguments = request_data if request_data else {}
    return await health_impl(arguments)


async def get_tool_definitions_impl():
    """도구 정의 목록 반환"""
    tools = [
        {
            "name": "health",
            "description": "서비스 상태 확인 및 API 키 설정 상태 확인",
            "parameters": {
                "type": "object",
                "properties": {
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "env": {
                                "type": "object",
                                "properties": {
                                    "DART_API_KEY": {"type": "string", "description": "DART API 키"}
                                }
                            }
                        }
                    }
                },
                "required": []
            }
        },
        {
            "name": "search_company_tool",
            "description": "기업을 회사명으로 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 회사명 (예: '삼성전자', '네이버')"}
                },
                "required": ["query"]
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
                    "reprt_code": {"type": "string", "description": "보고서 코드 (11011: 사업보고서, 11013: 분기보고서)", "default": "11011"}
                },
                "required": []
            }
        },
        {
            "name": "get_public_disclosure_tool",
            "description": "기업의 공시정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp_code": {"type": "string", "description": "기업 고유번호"},
                    "bgn_de": {"type": "string", "description": "시작일 (YYYYMMDD 형식)"},
                    "end_de": {"type": "string", "description": "종료일 (YYYYMMDD 형식)"},
                    "page_no": {"type": "integer", "description": "페이지 번호", "default": 1},
                    "page_count": {"type": "integer", "description": "페이지당 건수", "default": 10}
                },
                "required": ["corp_code"]
            }
        },
        {
            "name": "analyze_financial_trend_tool",
            "description": "기업의 재무 추이를 분석합니다. (최근 N년)",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp_code": {"type": "string", "description": "기업 고유번호"},
                    "years": {"type": "integer", "description": "분석할 연수 (기본값: 5, 최대: 10)", "default": 5, "minimum": 1, "maximum": 10}
                },
                "required": ["corp_code"]
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
                },
                "required": []
            }
        },
        {
            "name": "get_major_report_tool",
            "description": "주요사항보고서를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp_code": {"type": "string", "description": "기업 고유번호"},
                    "company_name": {"type": "string", "description": "회사명"},
                    "bgn_de": {"type": "string", "description": "시작일 (YYYYMMDD 형식)"},
                    "end_de": {"type": "string", "description": "종료일 (YYYYMMDD 형식)"}
                },
                "required": []
            }
        },
        {
            "name": "download_disclosure_document_tool",
            "description": "공시원문을 다운로드합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rcept_no": {"type": "string", "description": "접수번호"},
                    "file_format": {"type": "string", "description": "파일 형식 (xml 또는 pdf)", "default": "xml"}
                },
                "required": ["rcept_no"]
            }
        },
        {
            "name": "get_executives_tool",
            "description": "기업의 임원정보를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp_code": {"type": "string", "description": "기업 고유번호"},
                    "company_name": {"type": "string", "description": "회사명"}
                },
                "required": []
            }
        },
        {
            "name": "get_shareholders_tool",
            "description": "지분보고서를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp_code": {"type": "string", "description": "기업 고유번호"},
                    "company_name": {"type": "string", "description": "회사명"},
                    "bsns_year": {"type": "string", "description": "사업연도 (YYYY 형식)"},
                    "reprt_code": {"type": "string", "description": "보고서 코드 (11011: 사업보고서, 11013: 분기보고서)", "default": "11011"}
                },
                "required": []
            }
        }
    ]
    return {"tools": tools}


# HTTP 엔드포인트: 도구 목록 조회
@api.get("/tools")
async def get_tools_http():
    """HTTP 엔드포인트: 사용 가능한 도구 목록 조회"""
    definitions = await get_tool_definitions_impl()
    return definitions.get("tools", [])


# HTTP 엔드포인트: 도구 호출
@api.post("/tools/{tool_name}")
async def call_tool_http(tool_name: str, request_data: dict):
    mcp_logger.debug("HTTP call_tool | tool=%s request=%s", tool_name, request_data)
    env = request_data.get("env", {}) if isinstance(request_data, dict) else {}

    async def run_sync(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

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
            return await run_with_env(health_impl())

        if tool_name == "search_company_tool":
            query = request_data.get("query")
            if not query:
                return {"error": "Missing required parameter: query"}
            return await run_with_env(
                run_sync(search_company, query, arguments=request_data)
            )

        if tool_name == "get_financial_statement_tool":
            corp_code = request_data.get("corp_code")
            company_name = request_data.get("company_name")
            if not corp_code and not company_name:
                return {"error": "Missing required parameter: corp_code or company_name"}
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
            return await run_with_env(
                run_sync(get_public_disclosure, corp_code, bgn_de, end_de, page_no, page_count, arguments=request_data)
            )

        if tool_name == "analyze_financial_trend_tool":
            corp_code = request_data.get("corp_code")
            if not corp_code:
                return {"error": "Missing required parameter: corp_code"}
            years = request_data.get("years", 5)
            return await run_with_env(
                run_sync(analyze_financial_trend, corp_code, years, arguments=request_data)
            )

        return {"error": "Tool not found"}
    except Exception as e:
        mcp_logger.exception("Error in call_tool_http: %s", str(e))
        return {"error": f"Error calling tool: {str(e)}"}


# MCP 도구 정의
@mcp.tool()
async def health(arguments: Optional[dict] = None):
    """
    서비스 상태 확인
    
    Args:
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        서비스 상태 및 환경 변수 설정 상태
    """
    return await health_impl(arguments)


@mcp.tool()
async def search_company_tool(query: str, arguments: Optional[dict] = None):
    """
    기업을 회사명으로 검색합니다.
    
    Args:
        query: 검색할 회사명 (예: '삼성전자', '네이버')
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        검색된 기업 목록 (기업 고유번호 포함)
    """
    req = CompanySearchRequest(query=query)
    return await search_company_impl(req, arguments)


@mcp.tool()
async def get_financial_statement_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011",
    arguments: Optional[dict] = None
):
    """
    기업의 재무제표를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용, 예: '삼성전자', '카카오')
        bsns_year: 사업연도 (YYYY 형식, 기본값: 최근 연도)
        reprt_code: 보고서 코드 (11011: 사업보고서, 11013: 분기보고서)
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        재무제표 정보 (손익계산서, 재무상태표, 현금흐름표)
    """
    req = FinancialStatementRequest(
        corp_code=corp_code,
        company_name=company_name,
        bsns_year=bsns_year,
        reprt_code=reprt_code
    )
    return await get_financial_statement_impl(req, arguments)


@mcp.tool()
async def get_public_disclosure_tool(
    corp_code: str,
    bgn_de: Optional[str] = None,
    end_de: Optional[str] = None,
    page_no: int = 1,
    page_count: int = 10,
    arguments: Optional[dict] = None
):
    """
    기업의 공시정보를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호
        bgn_de: 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
        end_de: 종료일 (YYYYMMDD 형식, 기본값: 오늘)
        page_no: 페이지 번호
        page_count: 페이지당 건수
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        공시정보 목록
    """
    req = PublicDisclosureRequest(
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        page_no=page_no,
        page_count=page_count
    )
    return await get_public_disclosure_impl(req, arguments)


@mcp.tool()
async def analyze_financial_trend_tool(
    corp_code: str,
    years: int = 5,
    arguments: Optional[dict] = None
):
    """
    기업의 재무 추이를 분석합니다. (최근 N년)
    
    Args:
        corp_code: 기업 고유번호
        years: 분석할 연수 (기본값: 5, 최대: 10)
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        재무 추이 분석 결과 (최근 N년 재무제표 데이터)
    """
    req = FinancialTrendRequest(corp_code=corp_code, years=years)
    return await analyze_financial_trend_impl(req, arguments)


@mcp.tool()
async def get_company_overview_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    arguments: Optional[dict] = None
):
    """
    기업의 기본정보를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용, 예: '삼성전자', '카카오')
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        기업 기본정보 (회사명, 대표자명, 설립일, 본사주소 등)
    """
    req = CompanyOverviewRequest(
        corp_code=corp_code,
        company_name=company_name
    )
    return await get_company_overview_impl(req, arguments)


@mcp.tool()
async def get_major_report_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bgn_de: Optional[str] = None,
    end_de: Optional[str] = None,
    arguments: Optional[dict] = None
):
    """
    주요사항보고서를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        bgn_de: 시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)
        end_de: 종료일 (YYYYMMDD 형식, 기본값: 오늘)
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        주요사항보고서 목록
    """
    req = MajorReportRequest(
        corp_code=corp_code,
        company_name=company_name,
        bgn_de=bgn_de,
        end_de=end_de
    )
    return await get_major_report_impl(req, arguments)


@mcp.tool()
async def download_disclosure_document_tool(
    rcept_no: str,
    file_format: str = "xml",
    arguments: Optional[dict] = None
):
    """
    공시원문을 다운로드합니다.
    
    Args:
        rcept_no: 접수번호 (공시정보에서 얻을 수 있음)
        file_format: 파일 형식 ("xml" 또는 "pdf", 기본값: "xml")
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        공시원문 데이터 (XML은 파싱된 데이터 포함, PDF는 base64 인코딩)
    """
    req = DocumentDownloadRequest(
        rcept_no=rcept_no,
        file_format=file_format
    )
    return await download_disclosure_document_impl(req, arguments)


@mcp.tool()
async def get_executives_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    arguments: Optional[dict] = None
):
    """
    기업의 임원정보를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용, 예: '삼성전자', '카카오')
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        임원정보 (임원명, 직책, 보수 등)
    """
    req = ExecutivesRequest(
        corp_code=corp_code,
        company_name=company_name
    )
    return await get_executives_impl(req, arguments)


@mcp.tool()
async def get_shareholders_tool(
    corp_code: Optional[str] = None,
    company_name: Optional[str] = None,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011",
    arguments: Optional[dict] = None
):
    """
    지분보고서를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호 (corp_code 또는 company_name 중 하나 필수)
        company_name: 회사명 (corp_code가 없을 경우 사용)
        bsns_year: 사업연도 (YYYY 형식, 기본값: 최근 연도)
        reprt_code: 보고서 코드 (11011: 사업보고서, 11013: 분기보고서)
        arguments: 도구 호출 인자 (env 필드 포함 가능)
    
    Returns:
        지분보고서 (주주명, 보유지분, 비율 등)
    """
    req = ShareholdersRequest(
        corp_code=corp_code,
        company_name=company_name,
        bsns_year=bsns_year,
        reprt_code=reprt_code
    )
    return await get_shareholders_impl(req, arguments)


async def main():
    """MCP 서버를 실행합니다."""
    print("MCP Korean Company Information Server starting...", file=sys.stderr)
    print("Server: company-info-service", file=sys.stderr)
    print("Available tools: health, search_company_tool, get_financial_statement_tool, get_public_disclosure_tool, analyze_financial_trend_tool, get_company_overview_tool, get_major_report_tool, download_disclosure_document_tool, get_executives_tool, get_shareholders_tool", file=sys.stderr)
    
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

