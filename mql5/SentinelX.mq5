//+------------------------------------------------------------------+
//|                                                    SentinelX.mq5 |
//|                                  Copyright 2024, Sentinel-X Team |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Sentinel-X"
#property link      "http://localhost:8000"
#property version   "2.00"

#include <Trade\Trade.mqh>

CTrade trade;

// --- Inputs (Matched to Screenshot) ---
input string InpAI_URL = "http://127.0.0.1:8000/api/v1/analyze";
input string InpReport_URL = "http://127.0.0.1:8000/api/v1/report"; // Forward Telegram via server
input string InpPing_URL = "http://127.0.0.1:8000/api/v1/mt5-ping"; // Heartbeat endpoint
input string InpChart_URL = "http://127.0.0.1:8000/api/v1/chart-data"; // Chart data endpoint
input string InpAccount_URL = "http://127.0.0.1:8000/api/v1/account-info"; // Account info endpoint
input string InpSharedSecret = "SentinelX-Secret-Key";
input double InpFixedLot = 0.01;
input int    InpTailCandles = 5; // Tail N candles for Price Action
input int    InpStructureLookback = 100; // Lookback for High/Low Structure
input int    InpPingInterval = 10; // Ping interval in seconds
input int    InpAccountUpdateInterval = 60; // Account info update interval in seconds

#define EA_VERSION "2.00"

// Globals
int ma_fast_handle;
int ma_slow_handle;
int ma_trend_handle;
datetime last_ping_time = 0;
datetime last_account_update = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   ma_fast_handle = iMA(_Symbol, _Period, 9, 0, MODE_EMA, PRICE_CLOSE);
   ma_slow_handle = iMA(_Symbol, _Period, 21, 0, MODE_EMA, PRICE_CLOSE);
   ma_trend_handle = iMA(_Symbol, _Period, 200, 0, MODE_EMA, PRICE_CLOSE);
   
   if(ma_fast_handle == INVALID_HANDLE || ma_slow_handle == INVALID_HANDLE || ma_trend_handle == INVALID_HANDLE)
     {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
     }

    trade.SetExpertMagicNumber(123456);
    Print("Sentinel-X Initialized. URL: ", InpAI_URL);
    
    // Send initial ping to establish connection
    last_ping_time = 0; // Force immediate ping
    SendPing();
    
    return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   IndicatorRelease(ma_fast_handle);
   IndicatorRelease(ma_slow_handle);
   IndicatorRelease(ma_trend_handle);
  }

//+------------------------------------------------------------------+
//| Send heartbeat ping to server                                    |
//+------------------------------------------------------------------+
void SendPing()
  {
   // Only send ping every InpPingInterval seconds
   if(TimeCurrent() - last_ping_time < InpPingInterval)
      return;
      
   last_ping_time = TimeCurrent();
   
   string json = StringFormat(
      "{\"ea_version\":\"%s\",\"symbol\":\"%s\",\"timeframe\":\"%s\"}",
      EA_VERSION, _Symbol, EnumToString(_Period)
   );
   
   char post_data[];
   StringToCharArray(json, post_data, 0, StringLen(json));
   char result_data[];
   string result_headers;
   
   string headers = "Content-Type: application/json\r\nX-Shared-Secret: " + InpSharedSecret;
   
   int res = WebRequest("POST", InpPing_URL, headers, 3000, post_data, result_data, result_headers);
   
    if(res == 200)
    {
       Print("Ping sent successfully");
    }
    else
    {
       Print("Ping failed: ", res, " Error: ", GetLastError());
    }
   }

//+------------------------------------------------------------------+
//| Send OHLCV chart data to server                                  |
//+------------------------------------------------------------------+
void SendChartData(datetime bar_time, double open, double high, double low, double close, long volume)
  {
   // Convert timeframe to string format
   string tf_str = "H1"; // Default
   switch(_Period)
   {
      case PERIOD_M15: tf_str = "M15"; break;
      case PERIOD_M30: tf_str = "M30"; break;
      case PERIOD_H1:  tf_str = "H1";  break;
      case PERIOD_H4:  tf_str = "H4";  break;
      case PERIOD_D1:  tf_str = "D1";  break;
      default:         tf_str = "H1";  break;
   }
   
   // Format timestamp (ISO 8601)
   MqlDateTime dt;
   TimeToStruct(bar_time, dt);
   string timestamp = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
      dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
   
   // Build JSON
   string json = StringFormat(
      "{"
      "\"symbol\":\"%s\","
      "\"timeframe\":\"%s\","
      "\"timestamp\":\"%s\","
      "\"open\":%.5f,"
      "\"high\":%.5f,"
      "\"low\":%.5f,"
      "\"close\":%.5f,"
      "\"volume\":%I64d"
      "}",
      _Symbol, tf_str, timestamp, open, high, low, close, volume
   );
   
   char post_data[];
   StringToCharArray(json, post_data, 0, StringLen(json));
   char result_data[];
   string result_headers;
   
   string headers = "Content-Type: application/json\r\nX-Shared-Secret: " + InpSharedSecret;
   
   int res = WebRequest("POST", InpChart_URL, headers, 5000, post_data, result_data, result_headers);
   
    if(res == 200)
    {
       Print("Chart data sent: ", _Symbol, " ", tf_str, " @ ", close);
    }
    else
    {
       Print("Chart data failed: ", res, " Error: ", GetLastError());
    }
  }

//+------------------------------------------------------------------+
//| Send account information to server                               |
//+------------------------------------------------------------------+
void SendAccountInfo()
  {
   // Only update setiap InpAccountUpdateInterval detik
   if(TimeCurrent() - last_account_update < InpAccountUpdateInterval)
      return;
      
   last_account_update = TimeCurrent();
   
   // Get account information
   long account_id = AccountInfoInteger(ACCOUNT_LOGIN);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin_free = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   int leverage = (int)AccountInfoInteger(ACCOUNT_LEVERAGE);
   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   
   // Detect account type based on lot sizes
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   string account_type = "normal";
   if(min_lot >= 0.1)
      account_type = "micro";
   else if(StringFind(AccountInfoString(ACCOUNT_COMPANY), "Micro", 0) >= 0 ||
           StringFind(AccountInfoString(ACCOUNT_COMPANY), "Cent", 0) >= 0)
      account_type = "micro";
   
   // Build JSON
   string json = StringFormat(
      "{"
      "\"account_id\":\"%I64d\","
      "\"account_type\":\"%s\","
      "\"balance\":%.2f,"
      "\"equity\":%.2f,"
      "\"margin_free\":%.2f,"
      "\"leverage\":%d,"
      "\"currency\":\"%s\","
      "\"min_lot\":%.2f,"
      "\"max_lot\":%.2f,"
      "\"lot_step\":%.2f,"
      "\"symbol\":\"%s\""
      "}",
      account_id, account_type, balance, equity, margin_free, 
      leverage, currency, min_lot, max_lot, lot_step, _Symbol
   );
   
   char post_data[];
   StringToCharArray(json, post_data, 0, StringLen(json));
   char result_data[];
   string result_headers;
   
   string headers = "Content-Type: application/json\r\nX-Shared-Secret: " + InpSharedSecret;
   
   int res = WebRequest("POST", InpAccount_URL, headers, 5000, post_data, result_data, result_headers);
   
   if(res == 200)
   {
      Print("Account info sent: ", account_type, " | Balance: ", balance, " | MinLot: ", min_lot);
   }
   else
   {
      Print("Account info failed: ", res, " Error: ", GetLastError());
   }
  }
  
  void OnTick()
   {
    // Send heartbeat ping
    SendPing();
    
    // Send account info (periodic update)
    SendAccountInfo();
    
    static datetime last_bar_time = 0;
    datetime current_bar_time = iTime(_Symbol, _Period, 0);
    
    if(last_bar_time == current_bar_time) return; 
    last_bar_time = current_bar_time;
    
    // --- Send Chart Data for Previous Closed Candle ---
    double prev_open[], prev_high[], prev_low[], prev_close[];
    long   prev_vol[];
    ArraySetAsSeries(prev_open, true); ArraySetAsSeries(prev_high, true); 
    ArraySetAsSeries(prev_low, true); ArraySetAsSeries(prev_close, true);
    ArraySetAsSeries(prev_vol, true);
    
    if(CopyOpen(_Symbol, _Period, 1, 1, prev_open) > 0 &&
       CopyHigh(_Symbol, _Period, 1, 1, prev_high) > 0 &&
       CopyLow(_Symbol, _Period, 1, 1, prev_low) > 0 &&
       CopyClose(_Symbol, _Period, 1, 1, prev_close) > 0 &&
       CopyTickVolume(_Symbol, _Period, 1, 1, prev_vol) > 0)
    {
       datetime prev_time = iTime(_Symbol, _Period, 1);
       SendChartData(prev_time, prev_open[0], prev_high[0], prev_low[0], prev_close[0], prev_vol[0]);
    }
 
    // --- 1. Collect Report Data (Tail Candles) ---
    string tail_json = "[";
    double t_open[], t_high[], t_low[], t_close[];
    ArraySetAsSeries(t_open, true); ArraySetAsSeries(t_high, true); 
    ArraySetAsSeries(t_low, true); ArraySetAsSeries(t_close, true);
    
    CopyOpen(_Symbol, _Period, 1, InpTailCandles, t_open);
    CopyHigh(_Symbol, _Period, 1, InpTailCandles, t_high);
    CopyLow(_Symbol, _Period, 1, InpTailCandles, t_low);
    CopyClose(_Symbol, _Period, 1, InpTailCandles, t_close);
    
    for(int i=InpTailCandles-1; i>=0; i--)
    {
       string bar = StringFormat(
          "{\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f}",
          t_open[i], t_high[i], t_low[i], t_close[i]
       );
       tail_json += bar;
       if(i > 0) tail_json += ",";
    }
    tail_json += "]";
 
    // --- 2. Collect Current Data ---
    double close[]; ArraySetAsSeries(close, true); CopyClose(_Symbol, _Period, 0, 1, close);
    long   vol[];   ArraySetAsSeries(vol, true);   CopyTickVolume(_Symbol, _Period, 0, 1, vol);
    
    double ma_fast_val[]; CopyBuffer(ma_fast_handle, 0, 1, 1, ma_fast_val);
    double ma_slow_val[]; CopyBuffer(ma_slow_handle, 0, 1, 1, ma_slow_val);
    double ma_trend_val[]; CopyBuffer(ma_trend_handle, 0, 1, 1, ma_trend_val);
 
    // --- Structure Calculation ---
    int high_idx = iHighest(_Symbol, _Period, MODE_HIGH, InpStructureLookback, 1);
    int low_idx = iLowest(_Symbol, _Period, MODE_LOW, InpStructureLookback, 1);
   double struct_high = 0;
   double struct_low = 0;
   
   double highs[]; CopyHigh(_Symbol, _Period, high_idx, 1, highs);
   double lows[]; CopyLow(_Symbol, _Period, low_idx, 1, lows);
   
   if(ArraySize(highs)>0) struct_high = highs[0];
   if(ArraySize(lows)>0) struct_low = lows[0];

   // --- 3. Build Main JSON ---
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double step_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   string json = StringFormat(
      "{"
      "\"symbol\":\"%s\","
      "\"timeframe\":\"%s\","
      "\"balance\":%.2f,"
      "\"min_lot\":%.5f,"
      "\"step_lot\":%.5f,"
      "\"price\":%.5f,"
      "\"open\":%.5f,"
      "\"high\":%.5f,"
      "\"low\":%.5f,"
      "\"close\":%.5f,"
      "\"tick_volume\":%d,"
      "\"ma_fast\":%.5f,"
      "\"ma_slow\":%.5f,"
      "\"ma_trend\":%.5f,"
      "\"structure_high\":%.5f,"
      "\"structure_low\":%.5f,"
      "\"rsi\":50.0,"
      "\"tail_candles\":%s" 
      "}",
      _Symbol,
      EnumToString(_Period),
      balance,
      min_lot,
      step_lot,
      close[0],
      t_open[0], // Using last closed bar open/high/low for stability
      t_high[0],
      t_low[0],
      close[0],
      vol[0],
      ma_fast_val[0],
      ma_slow_val[0],
      ma_trend_val[0],
      struct_high,
      struct_low,
      tail_json
   );

   // --- 4. Send Request (With Shared Secret) ---
   char post_data[];
   StringToCharArray(json, post_data, 0, StringLen(json));
   char result_data[];
   string result_headers;
   
   string headers = "Content-Type: application/json\r\nX-Shared-Secret: " + InpSharedSecret;
   
   int res = WebRequest("POST", InpAI_URL, headers, 5000, post_data, result_data, result_headers);
   
   if(res == 200)
   {
      string response = CharArrayToString(result_data);
      Print("AI Says: ", response);
      
      // Simple Parsing (Enhanced)
      string action = GetJsonString(response, "action");
      double ai_sl  = GetJsonDouble(response, "sl");
      double ai_tp  = GetJsonDouble(response, "tp");
      double ai_lot = GetJsonDouble(response, "lot_size");
      
      // Safety Fallback
      if(ai_lot <= 0) ai_lot = InpFixedLot;
      
      if(action == "BUY")
      {
         if(trade.Buy(ai_lot, _Symbol, 0, ai_sl, ai_tp, "Sentinel-X AI"))
            SendReport("OPEN_BUY", 0.0, "AI Buy Executed");
      }
      else if(action == "SELL")
      {
         if(trade.Sell(ai_lot, _Symbol, 0, ai_sl, ai_tp, "Sentinel-X AI"))
            SendReport("OPEN_SELL", 0.0, "AI Sell Executed");
      }
   }
   else
   {
      Print("Error: ", res, " ", GetLastError());
   }
  }

// --- Helper: Simple JSON Parser ---
string GetJsonString(string json, string key)
{
   string pattern = "\"" + key + "\":\"";
   int start = StringFind(json, pattern);
   if(start < 0) return "";
   
   start += StringLen(pattern);
   int end = StringFind(json, "\"", start);
   return StringSubstr(json, start, end - start);
}

double GetJsonDouble(string json, string key)
{
   string pattern = "\"" + key + "\":";
   int start = StringFind(json, pattern);
   if(start < 0) return 0.0;
   
   start += StringLen(pattern);
   // Find end of number (comma or brace)
   int end = -1;
   int end1 = StringFind(json, ",", start);
   int end2 = StringFind(json, "}", start);
   
   if(end1 > 0 && end2 > 0) end = MathMin(end1, end2);
   else if(end1 > 0) end = end1;
   else end = end2;
   
   if(end < 0) return 0.0;
   
   string val = StringSubstr(json, start, end - start);
   return StringToDouble(val);
}

void SendReport(string action, double pnl, string comment)
{
   string json = StringFormat(
      "{\"symbol\":\"%s\",\"action\":\"%s\",\"pnl\":%.2f,\"comment\":\"%s\"}",
      _Symbol, action, pnl, comment
   );
   
   char post_data[];
   StringToCharArray(json, post_data, 0, StringLen(json));
   char result_data[];
   string result_headers;
   string headers = "Content-Type: application/json\r\nX-Shared-Secret: " + InpSharedSecret;
   
   WebRequest("POST", InpReport_URL, headers, 3000, post_data, result_data, result_headers);
}
