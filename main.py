import os
import json
from typing import List, Generator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from together import Together
from dotenv import load_dotenv

load_dotenv()

# Config
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL = "moonshotai/Kimi-K2-Thinking"
MAX_TOKENS = 4096
MAX_TURNS = 5
SYSTEM_PROMPT = "You are Kimi, an AI assistant created by Moonshot AI."
USER_PROMPT_TEMPLATE = "You are 'The Together Deep Market Researcher'. Research the target company and its main competitor, then provide a deep-dive comparison. Use the provided tools. Perform a deep-dive comparison for {company_name}."

client = Together(api_key=TOGETHER_API_KEY)

app = FastAPI(title="Together Deep Market Researcher (Kimi K2-Thinking)")

# Tool Implementations
# Note: Tools return mock data for demo purposes.
def get_competitors(company_name: str) -> List[str]:
    competitors = {
        "Apple": ["Samsung", "Google", "Microsoft"],
        "Microsoft": ["Oracle", "Amazon", "Apple"],
        "Google": ["Microsoft", "Meta", "Amazon"],
        "Netflix": ["Disney+", "Hulu", "Amazon Prime Video"],
        "Tesla": ["BYD", "Rivian", "Ford"]
    }
    return competitors.get(company_name, ["Competitor A", "Competitor B", "Competitor C"])

def search_financials(company_name: str) -> str:
    return f"{company_name} Financial Summary: Revenue $100B, Growth +15% YoY, Market Share 25%."

def get_recent_news(company_name: str) -> List[str]:
    return [
        f"{company_name} announces new product line",
        f"Analysts upgrade {company_name} stock rating",
        f"{company_name} expands operations into new markets"
    ]

# Mapping of tool names to functions
TOOLS = {
    "get_competitors": get_competitors,
    "search_financials": search_financials,
    "get_recent_news": get_recent_news
}

# Define the tool schemas (tool names + parameters)
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_competitors",
            "description": "Get the top 3 competitors for a company",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_financials",
            "description": "Search financial data (revenue, growth, market share) for a company",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_news",
            "description": "Get the latest news headlines for a company",
            "parameters": {
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"]
            }
        }
    }
]

# Agent Loop
def run_agent(company_name: str, max_turns: int = MAX_TURNS) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(company_name=company_name)}
    ]
    
    for turn in range(max_turns):
        print(f"\n>> Turn {turn + 1} >>")
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            max_tokens=MAX_TOKENS
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"[Tool Call] {name}({args})")
                result = TOOLS[name](**args) if name in TOOLS else f"Unknown tool: {name}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })
        else:
            return {
                "analysis": msg.content,
                "reasoning": getattr(msg, "reasoning_content", None),
                "turns": turn + 1
            }
    
    return {"analysis": "Max turns reached", "reasoning": None, "turns": max_turns}

# Streaming Agent Loop (useful for debugging or UI display)
def run_agent_streaming(company_name: str, max_turns: int = MAX_TURNS) -> Generator[str, None, None]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(company_name=company_name)}
    ]
    
    for turn in range(max_turns):
        yield f"data: {json.dumps({'type': 'turn', 'turn': turn + 1})}\n\n"
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            max_tokens=MAX_TOKENS
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                yield f"data: {json.dumps({'type': 'tool_call', 'name': name, 'args': args})}\n\n"
                result = TOOLS[name](**args) if name in TOOLS else f"Unknown tool: {name}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })
        else:
            yield f"data: {json.dumps({'type': 'final_start'})}\n\n"
            if msg.content:
                yield f"data: {json.dumps({'type': 'content', 'content': msg.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'turns': turn + 1})}\n\n"
            return
    
    yield f"data: {json.dumps({'type': 'error', 'message': 'Max turns reached'})}\n\n"

# API
class AnalysisRequest(BaseModel):
    company_name: str

@app.get("/")
async def root():
    return {"message": "Deep Market Researcher is ready"}

@app.post("/analyze")
async def analyze_company(request: AnalysisRequest):
    if not TOGETHER_API_KEY or TOGETHER_API_KEY == "your_api_key_here":
        raise HTTPException(status_code=500, detail="TOGETHER_API_KEY is not set.")
    try:
        result = run_agent(request.company_name)
        return {
            "company": request.company_name,
            "model": MODEL,
            **result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/stream")
async def analyze_company_stream(request: AnalysisRequest):
    if not TOGETHER_API_KEY or TOGETHER_API_KEY == "your_api_key_here":
        raise HTTPException(status_code=500, detail="TOGETHER_API_KEY is not set.")
    return StreamingResponse(
        run_agent_streaming(request.company_name),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
