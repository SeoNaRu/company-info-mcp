#!/usr/bin/env python3
"""
Gemini Function Calling 테스트 스크립트
이 스크립트는 company-info-mcp 서버의 도구들을 Gemini API를 통해 테스트합니다.
"""
import os
import json
import asyncio
import time
import re
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from google.api_core import exceptions as google_exceptions

# .env 파일 로드
load_dotenv()

# Gemini API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DART_API_KEY = os.environ.get("DART_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY 환경 변수를 설정해주세요.")
    print("   .env 파일에 GEMINI_API_KEY=your_gemini_api_key 추가")
    exit(1)

if not DART_API_KEY:
    print("⚠️  DART_API_KEY가 설정되지 않았습니다. 일부 기능이 작동하지 않을 수 있습니다.")
    print("   .env 파일에 DART_API_KEY=your_dart_api_key 추가")

# Gemini API 키 설정
# Gemini API 키 설정
# 방법 1: 환경 변수 설정
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# 방법 2: genai.configure() 시도 (런타임에 동적으로 호출)
if GEMINI_API_KEY:
    try:
        # getattr을 사용하여 런타임에 configure 함수 확인
        configure_func = getattr(genai, 'configure', None)
        if configure_func:
            configure_func(api_key=GEMINI_API_KEY)
            print("✅ genai.configure()로 API 키 설정 완료")
    except Exception as e:
        # configure가 없거나 실패하면 환경 변수만 사용
        pass

def get_mcp_tools() -> Optional[list]:
    """
    MCP 서버에서 도구 목록을 가져와서 Gemini Function Calling 형식으로 변환합니다.
    """
    import requests
    try:
        response = requests.get("http://localhost:8097/tools", timeout=10)
        response.raise_for_status()
        tools_list = response.json()
        
        # Gemini Function Calling 형식으로 변환
        function_declarations = []
        
        for tool in tools_list:
            tool_name = tool.get("name", "")
            description = tool.get("description", "")
            parameters = tool.get("parameters", {})
            
            # health 도구는 제외 (테스트용이 아님)
            if tool_name == "health":
                continue
            
            # Gemini 형식으로 변환
            function_declaration = {
                "name": tool_name,
                "description": description,
                "parameters": parameters
            }
            
            function_declarations.append(function_declaration)
        
        return [{
            "function_declarations": function_declarations
        }]
        
    except Exception as e:
        print(f"⚠️  MCP 서버에서 도구 목록을 가져오지 못했습니다: {str(e)}")
        print("   하드코딩된 도구 목록을 사용합니다.")
        return None


# Function Calling을 위한 도구 정의 (Gemini 형식)
# MCP 서버에서 동적으로 가져오거나, fallback으로 하드코딩된 목록 사용
TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_company_tool",
                "description": "기업을 회사명으로 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "검색할 회사명 (예: '삼성전자', '네이버')"
                        }
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
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "회사명 (corp_code가 없을 경우 사용)"
                        }
                    }
                }
            },
            {
                "name": "get_financial_statement_tool",
                "description": "기업의 재무제표를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "회사명 (corp_code가 없을 경우 사용)"
                        },
                        "bsns_year": {
                            "type": "string",
                            "description": "사업연도 (YYYY 형식, 기본값: 최근 연도)"
                        },
                        "reprt_code": {
                            "type": "string",
                            "description": "보고서 코드 (11011: 사업보고서, 11013: 분기보고서, 기본값: 11011)"
                        }
                    }
                }
            },
            {
                "name": "analyze_financial_trend_tool",
                "description": "기업의 재무 추이를 분석합니다. (최근 N년)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "years": {
                            "type": "integer",
                            "description": "분석할 연수 (기본값: 5, 최대: 10)"
                        }
                    },
                    "required": ["corp_code"]
                }
            },
            {
                "name": "get_public_disclosure_tool",
                "description": "기업의 공시정보를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "bgn_de": {
                            "type": "string",
                            "description": "시작일 (YYYYMMDD 형식, 기본값: 최근 1개월)"
                        },
                        "end_de": {
                            "type": "string",
                            "description": "종료일 (YYYYMMDD 형식, 기본값: 오늘)"
                        },
                        "page_no": {
                            "type": "integer",
                            "description": "페이지 번호 (기본값: 1)"
                        },
                        "page_count": {
                            "type": "integer",
                            "description": "페이지당 건수 (기본값: 10)"
                        }
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
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "회사명 (corp_code가 없을 경우 사용)"
                        },
                        "bsns_year": {
                            "type": "string",
                            "description": "사업연도 (YYYY 형식, 기본값: 최근 연도)"
                        },
                        "reprt_code": {
                            "type": "string",
                            "description": "보고서 코드 (11011: 사업보고서, 기본값: 11011)"
                        }
                    }
                }
            },
            {
                "name": "get_shareholders_tool",
                "description": "지분보고서를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corp_code": {
                            "type": "string",
                            "description": "기업 고유번호"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "회사명 (corp_code가 없을 경우 사용)"
                        },
                        "bsns_year": {
                            "type": "string",
                            "description": "사업연도 (YYYY 형식, 기본값: 최근 연도)"
                        },
                        "reprt_code": {
                            "type": "string",
                            "description": "보고서 코드 (11011: 사업보고서, 11013: 분기보고서, 기본값: 11011)"
                        }
                    }
                }
            }
        ]
    }
]


def check_server_health() -> bool:
    """
    MCP 서버가 실행 중인지 확인합니다.
    """
    import requests
    try:
        response = requests.get("http://localhost:8097/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def call_mcp_tool(tool_name: str, **kwargs) -> dict:
    """
    MCP 서버의 도구를 호출합니다.
    HTTP 모드로 실행 중인 서버에 요청을 보냅니다.
    """
    import requests
    
    url = f"http://localhost:8097/tools/{tool_name}"
    
    # env에 DART_API_KEY 포함
    payload = {
        **kwargs,
        "env": {
            "DART_API_KEY": DART_API_KEY
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"도구 호출 실패: {str(e)}"}


def handle_function_call(function_name: str, args: dict) -> dict:
    """
    Gemini가 요청한 함수를 실행하고 결과를 반환합니다.
    """
    print(f"\n🔧 함수 호출: {function_name}")
    
    # 타입 변환: Gemini가 float로 전달하는 정수 파라미터를 정수로 변환
    integer_params = {
        "get_public_disclosure_tool": ["page_no", "page_count"],
        "analyze_financial_trend_tool": ["years"],
    }
    
    if function_name in integer_params:
        for param_name in integer_params[function_name]:
            if param_name in args and isinstance(args[param_name], float):
                args[param_name] = int(args[param_name])
    
    # 기본값 설정
    if function_name == "get_financial_statement_tool":
        if "reprt_code" not in args:
            args["reprt_code"] = "11011"
    elif function_name == "analyze_financial_trend_tool":
        if "years" not in args:
            args["years"] = 5
        elif isinstance(args.get("years"), float):
            args["years"] = int(args["years"])
    elif function_name == "get_public_disclosure_tool":
        if "page_no" not in args:
            args["page_no"] = 1
        elif isinstance(args.get("page_no"), float):
            args["page_no"] = int(args["page_no"])
        if "page_count" not in args:
            args["page_count"] = 10
        elif isinstance(args.get("page_count"), float):
            args["page_count"] = int(args["page_count"])
    elif function_name == "get_executives_tool":
        if "reprt_code" not in args:
            args["reprt_code"] = "11011"
    elif function_name == "get_shareholders_tool":
        if "reprt_code" not in args:
            args["reprt_code"] = "11011"
    
    print(f"   파라미터: {json.dumps(args, ensure_ascii=False, indent=2)}")
    
    # MCP 서버의 도구 호출
    result = call_mcp_tool(function_name, **args)
    
    print(f"   결과: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
    
    return result


# 전역 변수로 대화 컨텍스트 유지
_chat = None
_model = None
_current_model_name = None

def get_or_create_chat(model_name: str = "gemini-2.0-flash-exp"):
    """
    대화 컨텍스트를 유지하면서 chat 객체를 가져오거나 생성합니다.
    """
    global _chat, _model, _current_model_name
    
    # 모델이 변경되었거나 아직 생성되지 않은 경우
    if _model is None or _current_model_name != model_name:
        # API 키 확인 및 설정
        if not os.environ.get("GOOGLE_API_KEY") and GEMINI_API_KEY:
            os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        
        # genai.configure() 재시도 (모델 생성 전)
        if GEMINI_API_KEY:
            try:
                configure_func = getattr(genai, 'configure', None)
                if configure_func:
                    configure_func(api_key=GEMINI_API_KEY)
            except Exception:
                os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        
        try:
            _model = GenerativeModel(
                model_name=model_name,
                tools=TOOLS
            )
            _current_model_name = model_name
            _chat = _model.start_chat()
            print(f"✅ 새로운 대화 세션 시작 (모델: {model_name})")
        except Exception as e:
            print(f"❌ 모델 초기화 실패: {str(e)}")
            try:
                _model = GenerativeModel(
                    model_name="gemini-1.5-pro",
                    tools=TOOLS
                )
                _current_model_name = "gemini-1.5-pro"
                _chat = _model.start_chat()
                print("   기본 모델(gemini-1.5-pro)로 재시도 중...")
            except:
                print("   모델 초기화에 실패했습니다.")
                return None
    
    return _chat


def test_gemini_function_calling(user_query: str, model_name: str = "gemini-2.0-flash-exp"):
    """
    Gemini Function Calling을 테스트합니다.
    """
    print(f"\n🤖 사용자 질문: {user_query}")
    print(f"📱 사용 모델: {model_name}")
    print("=" * 60)
    
    # 대화 컨텍스트 가져오기 또는 생성
    chat = get_or_create_chat(model_name)
    if chat is None:
        return None
    
    try:
        # 사용자 질문 전송 (더 명확한 프롬프트 추가)
        enhanced_query = user_query
        # 사용자가 명확한 요청을 했는지 확인하고, 필요시 프롬프트 강화
        if any(keyword in user_query.lower() for keyword in ["분석", "조회", "검색", "정보", "재무", "공시", "임원", "지분", "기업"]):
            enhanced_query = f"{user_query}\n\n중요: 사용 가능한 도구(function)를 반드시 사용하여 정보를 조회하고 분석해주세요. 질문만 하지 말고 실제로 도구를 호출해주세요. 필요한 파라미터가 없으면 기본값을 사용하거나 회사명으로 먼저 검색하세요."
        
        # Gemini에 메시지 전송 (rate limit 처리 포함)
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = chat.send_message(enhanced_query)
                break  # 성공하면 루프 탈출
            except google_exceptions.ResourceExhausted as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"\n❌ Rate limit 오류: API 할당량을 초과했습니다.")
                    print(f"   오류 메시지: {str(e)[:200]}...")
                    print(f"   해결 방법: 잠시 후 다시 시도하거나 다른 모델을 사용하세요.")
                    return None
                
                # retry_delay 추출 (기본값 60초)
                retry_delay = 60
                error_str = str(e)
                if "retry_delay" in error_str or "seconds:" in error_str:
                    try:
                        match = re.search(r'seconds:\s*(\d+)', error_str)
                        if match:
                            retry_delay = int(match.group(1))
                    except:
                        pass
                
                print(f"\n⚠️  Rate limit 오류 발생 (시도 {retry_count}/{max_retries})")
                print(f"   {retry_delay}초 후 재시도합니다...")
                time.sleep(retry_delay)
                continue
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"\n❌ Rate limit 오류: API 할당량을 초과했습니다.")
                        print(f"   잠시 후 다시 시도하세요.")
                        return None
                    retry_delay = 60
                    print(f"\n⚠️  Rate limit 오류 발생 (시도 {retry_count}/{max_retries})")
                    print(f"   {retry_delay}초 후 재시도합니다...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise
        
        # Function calling이 필요한 경우 처리
        max_iterations = 10  # 무한 루프 방지
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 응답 확인
            if not response.candidates:
                break
                
            parts = response.candidates[0].content.parts
            if not parts:
                break
                
            # Function call 확인
            has_function_call = False
            for part in parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_function_call = True
                    function_call = part.function_call
                    function_name = function_call.name
                    args = dict(function_call.args)
                    
                    # 함수 실행
                    function_result = handle_function_call(function_name, args)
                    
                    # 결과를 Gemini에 전달 (rate limit 처리 포함)
                    max_retries_func = 3
                    retry_count_func = 0
                    
                    while retry_count_func < max_retries_func:
                        try:
                            response = chat.send_message({
                                "function_response": {
                                    "name": function_name,
                                    "response": function_result
                                }
                            })
                            break  # 성공하면 루프 탈출
                        except google_exceptions.ResourceExhausted as e:
                            retry_count_func += 1
                            if retry_count_func >= max_retries_func:
                                print(f"\n❌ Rate limit 오류: 함수 응답 전송 실패")
                                print(f"   잠시 후 다시 시도하세요.")
                                return None
                            
                            retry_delay = 60
                            error_str = str(e)
                            if "retry_delay" in error_str or "seconds:" in error_str:
                                try:
                                    match = re.search(r'seconds:\s*(\d+)', error_str)
                                    if match:
                                        retry_delay = int(match.group(1))
                                except:
                                    pass
                            
                            print(f"\n⚠️  Rate limit 오류 (함수 응답 전송, 시도 {retry_count_func}/{max_retries_func})")
                            print(f"   {retry_delay}초 후 재시도합니다...")
                            time.sleep(retry_delay)
                            continue
                        except Exception as e:
                            if "429" in str(e) or "quota" in str(e).lower():
                                retry_count_func += 1
                                if retry_count_func >= max_retries_func:
                                    print(f"\n❌ Rate limit 오류: 함수 응답 전송 실패")
                                    return None
                                retry_delay = 60
                                print(f"\n⚠️  Rate limit 오류 (함수 응답 전송, 시도 {retry_count_func}/{max_retries_func})")
                                print(f"   {retry_delay}초 후 재시도합니다...")
                                time.sleep(retry_delay)
                                continue
                            else:
                                raise
                    break
            
            if not has_function_call:
                break
        
        # 최종 응답 출력
        print("\n" + "=" * 60)
        print("💬 Gemini 응답:")
        print(response.text)
        print("=" * 60)
        
        return response.text
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """
    메인 함수
    """
    global TOOLS
    
    print("🚀 Gemini Function Calling 테스트 시작")
    print("=" * 60)
    
    # 서버 상태 확인
    if not check_server_health():
        print("❌ MCP 서버가 실행 중이지 않습니다!")
        print("   다음 명령어로 서버를 실행하세요:")
        print("   HTTP_MODE=1 python -m src.main")
        print("=" * 60)
        return
    
    print("✅ MCP 서버 연결 확인됨")
    print("=" * 60)
    
    # MCP 서버에서 도구 목록 가져오기
    print("\n📋 MCP 서버에서 도구 목록을 가져오는 중...")
    mcp_tools = get_mcp_tools()
    if mcp_tools:
        TOOLS = mcp_tools
        print(f"✅ {len(mcp_tools[0]['function_declarations'])}개의 도구를 가져왔습니다:")
        for tool in mcp_tools[0]['function_declarations']:
            print(f"   - {tool['name']}")
    else:
        print("⚠️  하드코딩된 도구 목록을 사용합니다.")
    print("=" * 60)
    
    # 테스트 쿼리들
    test_queries = [
        "삼성전자 회사 정보를 검색해줘",
        "네이버의 최근 재무제표를 조회해줘",
        "카카오의 기본 정보를 알려줘"
    ]
    
    # 모델 선택
    print("\n사용할 Gemini 모델을 선택하세요:")
    print("1. gemini-2.0-flash-exp (최신, 권장)")
    print("2. gemini-1.5-pro")
    print("3. gemini-1.5-flash")
    
    model_choice = input("\n모델 선택 (1-3, 기본값: 1): ").strip() or "1"
    
    model_map = {
        "1": "gemini-2.0-flash-exp",
        "2": "gemini-1.5-pro",
        "3": "gemini-1.5-flash"
    }
    model_name = model_map.get(model_choice, "gemini-2.0-flash-exp")
    
    # 사용자 입력 받기
    print("\n테스트 쿼리를 선택하거나 직접 입력하세요:")
    print("1. 삼성전자 회사 정보를 검색해줘")
    print("2. 네이버의 최근 재무제표를 조회해줘")
    print("3. 카카오의 기본 정보를 알려줘")
    print("4. 직접 입력")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        query = test_queries[0]
    elif choice == "2":
        query = test_queries[1]
    elif choice == "3":
        query = test_queries[2]
    elif choice == "4":
        query = input("질문을 입력하세요: ").strip()
    else:
        query = test_queries[0]
    
    if not query:
        print("❌ 질문을 입력해주세요.")
        return
    
    # 대화형 루프 시작
    print("\n💡 대화형 모드: 'quit', 'exit', 'q'를 입력하면 종료됩니다.")
    print("=" * 60)
    
    while True:
        # 테스트 실행
        result = test_gemini_function_calling(query, model_name)
        
        if result is None:
            print("\n⚠️  응답을 받지 못했습니다.")
        
        # 다음 질문 입력
        print("\n" + "=" * 60)
        next_query = input("\n다음 질문을 입력하세요 (종료: quit/exit/q): ").strip()
        
        if not next_query:
            continue
        
        # 종료 명령 확인
        if next_query.lower() in ['quit', 'exit', 'q', '종료']:
            print("\n👋 테스트를 종료합니다.")
            break
        
        query = next_query


if __name__ == "__main__":
    main()

