
# Estimated Pricing per 1M tokens (USD)
# Source: Official docs (Approx as of early 2025/2026) -> User warned these are estimates.

PRICING = {
    # OpenAI
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    
    # Anthropic
    "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    
    # Google (Gemini)
    "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
    "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0}, # Free Preview usually
    "gemini-2.0-pro-exp": {"input": 0.0, "output": 0.0},
    "gemini-1.5-pro-002": {"input": 3.5, "output": 10.5},
    "gemini-1.5-flash-002": {"input": 0.35, "output": 1.05},
    
    # Groq (Often free/cheap or passthrough) - Assuming Llama3 70B rates
    "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b-32768": {"input": 0.27, "output": 0.27},
    
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    
    # Qwen (Alibaba)
    "qwen-plus": {"input": 3.0, "output": 9.0}, # Approx
    "qwen-max": {"input": 20.0, "output": 60.0},
}

def calculate_cost(model: str, input_tok: int, output_tok: int) -> float:
    """Calculate estimated cost in USD."""
    # Fuzzy match or direct match
    rates = PRICING.get(model)
    
    # Fallback for versioned models (e.g. gpt-4-turbo-0125 -> gpt-4-turbo)
    if not rates:
        for k in PRICING:
            if k in model:
                rates = PRICING[k]
                break
    
    if not rates:
        return 0.0 # Unknown model
        
    cost_in = (input_tok / 1_000_000) * rates["input"]
    cost_out = (output_tok / 1_000_000) * rates["output"]
    
    return round(cost_in + cost_out, 6)
