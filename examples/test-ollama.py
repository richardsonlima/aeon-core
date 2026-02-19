"""
Exemplo de uso do Æon Core com Ollama

Inicia um servidor HTTP na porta 8000 que aceita requisições POST.

Uso:
    python test-ollama.py

Teste com curl:
    curl -X POST http://localhost:8000/message \
      -H "Content-Type: application/json" \
      -d '{"text": "Hello, what is AI?"}'
"""
import asyncio
from aeon import Agent

# Criar agente com modelo Ollama
agent = Agent(
    name="MyAeonAssistant",
    model="ollama/phi3.5",  # Formato: ollama/model-name
    protocols=[]  # Protocolos opcionais (A2A, MCP)
)

async def main():
    print(f"✅ Agent '{agent.name}' inicializado!")
    print(f"📦 Modelo: {agent.cortex.config.model}")
    print(f"🌐 Gateway: http://localhost:8000")
    print(f"🔒 Axiomas ativos: {len(agent.executive._axioms)}")
    print()
    print("Teste com:")
    print('  curl -X POST http://localhost:8000/message \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"text": "Hello, what is AI?"}\'')
    print()
    print("Pressione Ctrl+C para parar o servidor")
    print()
    
    # Iniciar gateway (servidor HTTP)
    await agent.start()
    
    # Manter o servidor rodando até Ctrl+C
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Parando servidor...")
        await agent.stop()
        print("✅ Servidor parado com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())
