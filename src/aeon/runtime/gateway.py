from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from aeon.core.config import AeonConfig
from aeon.automation.scheduler import Scheduler
from aeon.automation.webhooks import WebhookListener
from aeon import Agent

logger = logging.getLogger("aeon.runtime")

class GatewayServer:
    def __init__(self, config: AeonConfig):
        self.config = config
        self.app = FastAPI(title=f"Aeon Gateway: {config.agent.name}")
        self.scheduler = Scheduler()
        self.webhooks = WebhookListener(self.app, secret=config.server.webhooks)
        self.agent = None
        
        # Setup routes
        self.setup_routes()
        
        # Build agent on startup
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)

    def setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {"status": "ok", "agent": self.config.agent.name}
            
        @self.app.post("/run")
        async def run_agent(request: Request):
            data = await request.json()
            user_input = data.get("input")
            if not user_input:
                return JSONResponse({"error": "No input provided"}, status_code=400)
                
            if self.agent:
                result = await self.agent.run(user_input)
                return {"result": result}
            else:
                return JSONResponse({"error": "Agent not initialized"}, status_code=503)

    async def startup(self):
        logger.info("Gateway starting up...")
        # Initialize Agent based on Config
        # This is where we wire everything together declaratively
        
        from aeon.tools.browser import BrowserTool
        from aeon.memory.event_memory import EventMemory
        from aeon.security.trust import TrustLevel
        
        tools = []
        if self.config.capabilities.browser.enabled:
            tools.append(BrowserTool(headless=self.config.capabilities.browser.headless))
            
        self.agent = Agent(
            name=self.config.agent.name,
            model=f"{self.config.agent.model.provider}/{self.config.agent.model.name}",
            protocols=[],
            trust_level=self.config.agent.trust_level
        )
        
        if self.config.capabilities.memory.enabled:
            # Rehydrating memory from storage
            # self.agent.memory = EventMemory(path=self.config.capabilities.memory.storage_path)
            pass

        # Start Scheduler if automation is enabled
        if self.config.capabilities.automation.enabled:
            await self.scheduler.start()
            
        logger.info(f"Agent {self.agent.name} initialized and ready.")

    async def shutdown(self):
        logger.info("Gateway shutting down...")
        if self.scheduler:
            await self.scheduler.stop()
