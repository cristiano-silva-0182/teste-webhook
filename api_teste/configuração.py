# webhook_receiver.py

from fastapi import FastAPI, Request, Header, Depends, HTTPException, status
from datetime import datetime
import json
import os
import uvicorn

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

app = FastAPI(title="Foundry Webhook Receiver Simulator")

# Armazena payloads recebidos para inspeção
received_payloads = []


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _verify_bearer_token(authorization: str = Header(default=None)) -> None:
    expected = os.getenv("AUTH_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_TOKEN não configurado",
        )
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header ausente",
        )
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header inválido",
        )
    token = authorization[len(prefix) :].strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    content_type: str = Header(default="application/json"),
    authorization: str = Header(default=None),
    _: None = Depends(_verify_bearer_token),
):
    """Endpoint genérico para receber qualquer webhook do Foundry."""
    body = await request.body()
    
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = body.decode("utf-8")
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": str(request.url.path),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "payload": payload,
    }
    
    received_payloads.append(entry)
    
    print(f"\n{'='*60}")
    print(f"[{entry['timestamp']}] Webhook recebido!")
    print(f"Headers: {json.dumps(entry['headers'], indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2) if isinstance(payload, dict) else payload}")
    print(f"{'='*60}\n")
    
    # Resposta de sucesso para o Foundry
    return {
        "status": "received",
        "message": "Payload processado com sucesso",
        "id": len(received_payloads),
    }


@app.post("/webhook/action")
async def receive_action_webhook(
    request: Request,
    _: None = Depends(_verify_bearer_token),
):
    """Endpoint específico para simular recebimento de Action Side Effects."""
    payload = await request.json()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "action_side_effect",
        "payload": payload,
    }
    received_payloads.append(entry)
    
    print(f"\n[ACTION WEBHOOK] Payload: {json.dumps(payload, indent=2)}")
    
    return {"status": "ok", "processed": True}


@app.post("/webhook/create-record")
async def create_record(request: Request):
    """Simula criação de um registro externo (cenário comum de External Function)."""
    payload = await request.json()
    
    # Simula um ID gerado pelo sistema externo
    import uuid
    external_id = str(uuid.uuid4())
    
    print(f"\n[CREATE RECORD] Criando registro com dados: {json.dumps(payload, indent=2)}")
    print(f"[CREATE RECORD] ID gerado: {external_id}")
    
    return {
        "id": external_id,
        "created": True,
        "createdAt": datetime.now().isoformat(),
    }


@app.get("/webhook/history")
async def get_history():
    """Visualiza todos os payloads recebidos."""
    return {"total": len(received_payloads), "payloads": received_payloads}


@app.delete("/webhook/history")
async def clear_history():
    """Limpa o histórico de payloads."""
    received_payloads.clear()
    return {"status": "cleared"}


@app.get("/health")
async def health_check():
    """Health check para verificar se o servidor está ativo."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = _get_int_env("PORT", 8000)
    log_level = os.getenv("LOG_LEVEL", "info")

    print(f"🚀 Foundry Webhook Receiver iniciando em {host}:{port}...")
    print("📡 Endpoints disponíveis:")
    print("   POST /webhook              - Receber webhooks genéricos")
    print("   POST /webhook/action       - Receber Action Side Effects")
    print("   POST /webhook/create-record - Simular criação de registro")
    print("   GET  /webhook/history      - Ver payloads recebidos")
    print("   DELETE /webhook/history    - Limpar histórico")
    print("   GET  /health              - Health check")
    uvicorn.run(app, host=host, port=port, log_level=log_level)
