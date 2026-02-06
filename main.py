import os
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends, File, UploadFile, Request
from fastapi.responses import JSONResponse
import shutil
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime

# Load env variables
load_dotenv()
from core.config import ConfigManager
from core.notifications import send_telegram_alert
from core.database import TradeDatabase

# Import Core Logic
try:
    from core.judge import TheJudge, get_judge
    from core.tier1_math import get_tier1_engine
    from core.agents import get_arbitrator
    from core.mt5_monitor import get_mt5_monitor
except ImportError as e:
    # Fallback to prevent crash if core is not yet fully written during initial setup
    print(f"Import error: {e}")
    TheJudge = None
    get_judge = None
    get_mt5_monitor = None

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Sentinel-X Trading Core", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware - HARDENED: Localhost only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# --- Security ---
async def verify_secret(x_shared_secret: str = Header(None)):
    config = ConfigManager.load_config()
    server_conf = config.get('server', {})
    expected_secret = server_conf.get('shared_secret', '')
    
    # If no secret is set in config, allow all (or default to secure, let's decided to allow all if empty but warn)
    if not expected_secret:
        return
        
    if x_shared_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid Shared Secret")

# --- Data Models (DTO) ---
class MarketData(BaseModel):
    symbol: str
    timeframe: str
    price: float
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    balance: Optional[float] = 10000.0 # Default fallback
    min_lot: Optional[float] = 0.01
    step_lot: Optional[float] = 0.01
    # Add indicator values if pre-calculated in MQL5, or raw lists if calculating in Python
    # For simplicity, we assume MQL5 sends critical levels or raw arrays can be sent via JSON
    rsi: Optional[float] = None
    ma_fast: Optional[float] = None
    ma_slow: Optional[float] = None
    ma_trend: Optional[float] = 0.0 # SMA 200
    structure_high: Optional[float] = None
    structure_high: Optional[float] = None
    structure_low: Optional[float] = None
    tail_candles: Optional[List[dict]] = None # List of {"open": 1.1, "close": 1.2, ...}

class TradeSignal(BaseModel):
    action: str  # BUY, SELL, HOLD, CLOSE_BUY, CLOSE_SELL
    lot_size: float
    sl: float
    tp: float
    reason: str
    confidence_score: float

class ReportData(BaseModel):
    symbol: str
    action: str # OPEN, CLOSE, MODIFY
    pnl: float
    comment: str

# --- Dependencies ---
# Initialize The Judge Singleton
judge_instance = None

@app.on_event("startup")
async def startup_event():
    global judge_instance
    if get_judge:
        judge_instance = get_judge()
        print("Sentinel-X: The Judge 2.0 is now presiding.")
        print("✓ 3-Tier Decision Matrix active")
        print("✓ Tier 1: Mathematical Analysis (30% weight)")
        print("✓ Tier 2: RAG Context Retrieval")
        print("✓ Tier 3: AI Debate (70% weight)")
        
        # --- Auto-Ingest Knowledge Base ---
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            kb_path = os.path.join(base_dir, "knowledge", "concepts")
            # Ensure folder exists
            if not os.path.exists(kb_path):
                os.makedirs(kb_path, exist_ok=True)
                
            ingest_res = judge_instance.rag.ingest_knowledge_base(kb_path)
            print(f"Sentinel-X Auto-Ingest: {ingest_res}")
        except Exception as e:
            print(f"Sentinel-X Auto-Ingest Failed: {e}")
        
    else:
        print("Sentinel-X: Core logic not found, running in skeleton mode.")

# --- Endpoints ---
@app.get("/")
async def root():
    return {"status": "Sentinel-X Operational", "mode": "High-Alpha"}

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "Sentinel-X Core"}

@app.post("/api/ai-test")
async def test_ai_connection(verify_secret: None = Depends(verify_secret)):
    """Test connection to the configured AI provider."""
    try:
        if not judge_instance:
            # If judge is not initialized (skeleton mode), we can't test AI
            if 'TheJudge' not in globals() or TheJudge is None:
                 raise HTTPException(status_code=503, detail="AI Judge not loaded (Skeleton Mode)")
            
            # Try to grab the global judge if it was initialized in startup
            # For now, we assume if we are here, we might need to rely on the global variable if accessible
            # But let's check if we can instantiate it or if it's already there.
            # IN this file, judge_instance is set at the bottom usually? 
            # Let's check lines 220+ usually. 
            # Ideally we should use the one created in @app.on_event("startup")
            pass

        # Since judge_instance is global, we access it. 
        # Note: In a real app we'd use app.state.judge or dependency injection
        # But for this script, we'll try to use the global 'judge_instance' 
        
        if not judge_instance:
             raise HTTPException(status_code=503, detail="AI System not ready")

        # Use direct Ping logic to avoid complex RAG/Judge dependencies for status check
        # We access the internal agent's LLM directly like in test_llm
        try:
            # PING Check
            res = await judge_instance.pro_agent.llm.ainvoke("Ping. Reply with 'Pong'.")
            
            # --- Log Token Usage for Check ---
            try:
                usage = res.response_metadata.get('token_usage') or res.usage_metadata
                if usage:
                    in_tok = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
                    out_tok = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)
                    
                    model_name = judge_instance.pro_agent.config['llm']['model']
                    provider = judge_instance.pro_agent.config['llm']['provider']
                    
                    from core.pricing import calculate_cost
                    cost = calculate_cost(model_name, in_tok, out_tok)
                    
                    # Use a fresh DB connection for stats logging
                    db = TradeDatabase()
                    db.log_token_usage(provider, model_name, in_tok, out_tok, cost)
            except Exception as e_log:
                print(f"Failed to log ping stats: {e_log}")
            # -------------------------------

            return {
                "status": "connected", 
                "provider": judge_instance.pro_agent.config['llm']['provider'], 
                "response": res.content
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Ping Failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Connection Failed: {str(e)}")

@app.post("/api/v1/report", dependencies=[Depends(verify_secret)])
async def report_trade(data: ReportData):
    """
    Endpoint untuk MQL5 melaporkan hasil trade (Open/Close/PnL).
    """
    msg = f"🔔 **TRADE REPORT: {data.symbol}**\n"
    msg += f"Action: {data.action}\n"
    msg += f"PnL: {data.pnl:.2f}\n"
    msg += f"Comment: {data.comment}"
    
    await send_telegram_alert(msg)
    return {"status": "Report Recieved"}

@app.post("/api/v1/ingest", dependencies=[Depends(verify_secret)])
@limiter.limit("20/minute")
async def ingest_knowledge(request: Request):
    """
    Trigger manual ingestion of knowledge base files.
    """
    if not judge_instance:
        return {"status": "Error: Judge not initialized"}
        
    try:
        # Hardcoded path for now OR get from config
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "knowledge", "concepts")
        
        result_msg = judge_instance.rag.ingest_knowledge_base(kb_path)
        return {"status": result_msg}
    except Exception as e:
        return {"status": f"Error: {str(e)}"}

# --- Knowledge Base Manager Endpoints ---

@app.get("/api/v1/knowledge/files", dependencies=[Depends(verify_secret)])
async def list_knowledge_files():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "knowledge", "concepts")
        
        if not os.path.exists(kb_path):
            return {"files": []}
            
        files = [f for f in os.listdir(kb_path) if f.endswith(('.txt', '.md'))]
        return {"files": files}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/v1/knowledge/upload", dependencies=[Depends(verify_secret)])
async def upload_knowledge_file(file: UploadFile = File(...)):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "knowledge", "concepts")
        os.makedirs(kb_path, exist_ok=True)
        
        file_location = os.path.join(kb_path, file.filename)
        
        # Security check: prevent directory traversal
        if not os.path.abspath(file_location).startswith(os.path.abspath(kb_path)):
             raise HTTPException(status_code=400, detail="Invalid filename")

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"status": f"File '{file.filename}' uploaded successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/v1/knowledge/files/{filename}", dependencies=[Depends(verify_secret)])
async def read_knowledge_file(filename: str):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "knowledge", "concepts")
        file_path = os.path.join(kb_path, filename)
        
        # Security check
        if not os.path.abspath(file_path).startswith(os.path.abspath(kb_path)):
             raise HTTPException(status_code=400, detail="Invalid filename")
             
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {"filename": filename, "content": content}
    except Exception as e:
         return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/v1/knowledge/files/{filename}", dependencies=[Depends(verify_secret)])
async def delete_knowledge_file(filename: str):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "knowledge", "concepts")
        file_path = os.path.join(kb_path, filename)
        
        # Security check
        if not os.path.abspath(file_path).startswith(os.path.abspath(kb_path)):
             raise HTTPException(status_code=400, detail="Invalid filename")
             
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        os.remove(file_path)
        return {"status": f"File '{filename}' deleted"}
    except Exception as e:
         return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/test_llm", dependencies=[Depends(verify_secret)])
async def test_llm():
    if not judge_instance:
        return JSONResponse(status_code=503, content={"status": "Judge not presiding"})
    
    try:
        # Simple ping to ProAgent's LLM
        res = await judge_instance.pro_agent.llm.ainvoke("Hello. Reply with 'OK'.")
        return {"status": "connected", "reply": res.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "failed", "error": str(e)})

@app.post("/api/v1/analyze", response_model=TradeSignal, dependencies=[Depends(verify_secret)])
@limiter.limit("10/minute")
async def analyze_market(request: Request, data: MarketData):
    """
    Endpoint utama yang dipanggil oleh MQL5 setiap candle close atau timer.
    The Judge 2.0 otomatis evaluasi dengan 3-Tier Decision Matrix.
    Rate limited to prevent abuse while allowing normal trading operations.
    """
    if not judge_instance:
        return TradeSignal(
            action="HOLD", 
            lot_size=0.0, 
            sl=0.0, 
            tp=0.0, 
            reason="System initializing or Judge logic missing", 
            confidence_score=0.0
        )

    try:
        # Record MT5 connection
        if get_mt5_monitor:
            monitor = get_mt5_monitor()
            monitor.record_data_received(data.symbol)
        
        # Convert MarketData to dict untuk The Judge 2.0
        market_data = {
            'symbol': data.symbol,
            'timeframe': data.timeframe,
            'price': data.price,
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.tick_volume,
            'balance': data.balance,
            'rsi': data.rsi,
            'ma_fast': data.ma_fast,
            'ma_slow': data.ma_slow,
            'ma_trend': data.ma_trend,
            'atr': getattr(data, 'atr', None)
        }
        
        # Panggil The Judge 2.0
        signal = await judge_instance.evaluate(market_data)
        
        # Convert TradingSignal ke TradeSignal format
        decision = TradeSignal(
            action=signal.action,
            lot_size=signal.lot_size,
            sl=signal.stop_loss or 0.0,
            tp=signal.take_profit or 0.0,
            reason=signal.reasoning[:200] if signal.reasoning else "No specific reason",
            confidence_score=signal.confidence_score
        )
        
        # Telegram Notification for Signals
        if decision.action in ["BUY", "SELL", "STRONG_BUY", "STRONG_SELL"]:
            msg = f"🚀 **SIGNAL: {decision.action} {data.symbol}**\n"
            msg += f"Confidence: {decision.confidence_score:.1%}\n"
            msg += f"Debate Winner: {signal.debate_winner}\n"
            msg += f"Tier 1: {signal.tier1_contrib:.1%} | Tier 3: {signal.tier3_contrib:.1%}\n"
            msg += f"SL: {decision.sl} | TP: {decision.tp}"
            await send_telegram_alert(msg)
            
        return decision
    except Exception as e:
        print(f"Error analyzing market: {e}")
        import traceback
        traceback.print_exc()
        
        # Record error
        if get_mt5_monitor:
            monitor = get_mt5_monitor()
            monitor.record_error(str(e)[:100])
        
        # Fail-safe: Always return HOLD on error
        return TradeSignal(
            action="HOLD", 
            lot_size=0.0, 
            sl=0.0, 
            tp=0.0, 
            reason=f"Internal Error: {str(e)}", 
            confidence_score=0.0
        )

@app.get("/api/v1/mt5-status")
async def get_mt5_status():
    """
    Get MT5/EA connection status.
    Returns current connection state and statistics.
    """
    if not get_mt5_monitor:
        return {
            "status": "unknown",
            "status_text": "Monitor not available",
            "color": "#888888"
        }
    
    try:
        monitor = get_mt5_monitor()
        status_info = monitor.get_status_info()
        return status_info
    except Exception as e:
        return {
            "status": "error",
            "status_text": f"Error: {str(e)}",
            "color": "#ff0000"
        }

@app.post("/api/v1/mt5-ping")
async def mt5_ping(request: Request):
    """
    Endpoint untuk EA MT5 mengirim heartbeat/ping.
    """
    if not get_mt5_monitor:
        return {"status": "error", "message": "Monitor not available"}
    
    try:
        body = await request.json()
        ea_version = body.get('ea_version', 'Unknown')
        
        monitor = get_mt5_monitor()
        monitor.record_ping(ea_version)
        
        return {
            "status": "ok",
            "message": "Ping recorded",
            "server_time": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/v1/chart-data")
async def receive_chart_data(request: Request):
    """
    Endpoint untuk menerima OHLCV data dari MT5 EA.
    Menerima candle data dan menyimpan ke chart buffer.
    
    Expected payload:
    {
        "symbol": "EURUSD",
        "timeframe": "H1",
        "timestamp": "2024-01-15T10:00:00",
        "open": 1.0850,
        "high": 1.0860,
        "low": 1.0845,
        "close": 1.0855,
        "volume": 1234
    }
    """
    try:
        from core.chart_manager import get_chart_manager
        from core.mt5_monitor import get_mt5_monitor
        
        body = await request.json()
        
        # Validate required fields
        required = ['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [f for f in required if f not in body]
        if missing:
            return {
                "status": "error",
                "message": f"Missing fields: {missing}"
            }
        
        # Parse timestamp
        try:
            if 'T' in body['timestamp']:
                timestamp = datetime.fromisoformat(body['timestamp'].replace('Z', '+00:00'))
            else:
                # Handle format dari MT5
                timestamp = datetime.strptime(body['timestamp'], '%Y.%m.%d %H:%M')
        except:
            timestamp = datetime.now()
        
        # Add to chart manager
        manager = get_chart_manager()
        success = manager.add_candle_data(
            symbol=body['symbol'],
            timeframe=body['timeframe'],
            timestamp=timestamp,
            open_price=body['open'],
            high=body['high'],
            low=body['low'],
            close=body['close'],
            volume=body['volume']
        )
        
        if success:
            # Record data received di MT5 monitor
            monitor = get_mt5_monitor()
            monitor.record_data_received(body['symbol'])
            
            return {
                "status": "ok",
                "message": f"Candle added untuk {body['symbol']} {body['timeframe']}",
                "buffer_status": "active"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to add candle data"
            }
    
    except Exception as e:
        logger.error(f"Chart data endpoint error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/v1/chart/{symbol}/{timeframe}")
async def get_chart_data(symbol: str, timeframe: str):
    """
    Get chart data dan indicators untuk symbol/timeframe.
    """
    try:
        from core.chart_manager import get_chart_manager
        
        manager = get_chart_manager()
        data = manager.get_chart_data(symbol, timeframe)
        
        return data
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/v1/chart/symbols")
async def get_chart_symbols():
    """
    Get list of all symbols dengan chart data.
    """
    try:
        from core.chart_manager import get_chart_manager
        
        manager = get_chart_manager()
        status = manager.get_all_symbols_status()
        
        return {
            "status": "ok",
            "symbols": list(status.keys()),
            "details": status
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/api/v1/account-info")
async def receive_account_info(request: Request):
    """
    Endpoint untuk menerima account information dari MT5 EA.
    
    Expected payload:
    {
        "account_id": "12345",
        "account_type": "normal",  # atau "micro"
        "balance": 10000.0,
        "equity": 9950.0,
        "margin_free": 9000.0,
        "leverage": 100,
        "currency": "USD",
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "symbol": "EURUSD"  # Current symbol being traded
    }
    """
    try:
        from core.account_manager import get_account_manager
        from core.mt5_monitor import get_mt5_monitor
        
        body = await request.json()
        
        # Validate required fields
        required = ['account_id', 'balance', 'equity']
        missing = [f for f in required if f not in body]
        if missing:
            return {
                "status": "error",
                "message": f"Missing fields: {missing}"
            }
        
        # Update account manager
        manager = get_account_manager()
        success = manager.update_account(body)
        
        if success:
            # Record di MT5 monitor
            monitor = get_mt5_monitor()
            monitor.record_data_received(f"Account:{body['account_id']}")
            
            account = manager.get_account(body['account_id'])
            
            return {
                "status": "ok",
                "message": "Account info updated",
                "account": {
                    "id": body['account_id'],
                    "type": account.account_type if account else 'unknown',
                    "is_micro": account.is_micro if account else False,
                    "balance": account.balance if account else 0,
                    "min_lot": account.min_lot if account else 0.01
                }
            }
        else:
            return {
                "status": "error",
                "message": "Failed to update account"
            }
    
    except Exception as e:
        logger.error(f"Account info endpoint error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/v1/account/{account_id}")
async def get_account_info(account_id: str):
    """
    Get account information.
    """
    try:
        from core.account_manager import get_account_manager
        
        manager = get_account_manager()
        account = manager.get_account(account_id)
        
        if account:
            return {
                "status": "ok",
                "account": account.to_dict()
            }
        else:
            return {
                "status": "error",
                "message": "Account not found"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/v1/accounts")
async def get_all_accounts():
    """
    Get summary of all accounts.
    """
    try:
        from core.account_manager import get_account_manager
        
        manager = get_account_manager()
        summary = manager.get_account_summary()
        
        return {
            "status": "ok",
            **summary
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    config = ConfigManager.load_config()
    port = config.get('server', {}).get('port', 8000)
    print(f"Sentinel-X: Starting on port {port}...")
    # Use 'app' object directly for better compatibility with PyInstaller
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
