import os
import json
from typing import List, Generator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from together import Together
from dotenv import load_dotenv

load_dotenv()

# Config
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL = "moonshotai/Kimi-K2-Thinking"
MAX_TOKENS = 4096
MAX_TURNS = 10
SYSTEM_PROMPT = "You are Kimi, an AI assistant created by Moonshot AI."
USER_PROMPT_TEMPLATE = "You are 'The Together Deep Market Researcher'. Research the target company and its main competitor, then provide a deep-dive comparison. Use the provided tools. Perform a deep-dive comparison for {company_name}."

client = Together(api_key=TOGETHER_API_KEY)

app = FastAPI(title="Together Deep Market Researcher (Kimi K2-Thinking)")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tool Implementations
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

TOOLS = {
    "get_competitors": get_competitors,
    "search_financials": search_financials,
    "get_recent_news": get_recent_news
}

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


def run_agent_streaming(company_name: str, max_turns: int = MAX_TURNS) -> Generator[str, None, None]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(company_name=company_name)}
    ]
    
    for turn in range(max_turns):
        print(f"\n>> Turn {turn + 1} >>")
        yield f"data: {json.dumps({'type': 'turn_start', 'turn': turn + 1})}\n\n"
        
        try:
            # Use non-streaming for reliability
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                max_tokens=MAX_TOKENS
            )
            
            msg = response.choices[0].message
            
            # Check for reasoning content (try multiple field names)
            reasoning = None
            for field in ['reasoning_content', 'reasoning', 'thinking_content', 'thinking']:
                reasoning = getattr(msg, field, None)
                if reasoning:
                    break
            
            # Debug: print message attributes
            print(f"  [Debug] msg attrs: {[a for a in dir(msg) if not a.startswith('_')]}")
            print(f"  [Debug] content={repr(msg.content)[:100] if msg.content else None}")
            print(f"  [Debug] reasoning={repr(reasoning)[:100] if reasoning else None}")
            print(f"  [Debug] tool_calls={len(msg.tool_calls) if msg.tool_calls else 0}")
            
            if reasoning:
                print(f"  [Reasoning] {len(reasoning)} chars")
                yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning})}\n\n"
            
            if msg.tool_calls:
                # Append the assistant message with tool calls
                messages.append(msg)
                
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    
                    # Execute tool
                    tool_result = TOOLS[name](**args) if name in TOOLS else f"Unknown tool: {name}"
                    print(f"  [Tool] {name}({args})")
                    
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': name, 'args': args, 'result': tool_result})}\n\n"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result)
                    })
                
                yield f"data: {json.dumps({'type': 'turn_end', 'turn': turn + 1})}\n\n"
                
            elif msg.content:
                # Final analysis
                print(f"  [Final] {len(msg.content)} chars")
                yield f"data: {json.dumps({'type': 'analysis', 'content': msg.content})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'turns': turn + 1})}\n\n"
                return
                
            else:
                # Empty response - continue
                print(f"  [Empty response, continuing...]")
                yield f"data: {json.dumps({'type': 'turn_end', 'turn': turn + 1})}\n\n"
                
        except Exception as e:
            print(f"  [Error] {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return
    
    yield f"data: {json.dumps({'type': 'error', 'message': 'Max turns reached'})}\n\n"


class AnalysisRequest(BaseModel):
    company_name: str

@app.get("/")
async def root():
    return {"message": "Deep Market Researcher is ready"}

@app.post("/analyze/stream")
async def analyze_company_stream(request: AnalysisRequest):
    if not TOGETHER_API_KEY or TOGETHER_API_KEY == "your_api_key_here":
        raise HTTPException(status_code=500, detail="TOGETHER_API_KEY is not set.")
    return StreamingResponse(
        run_agent_streaming(request.company_name),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
