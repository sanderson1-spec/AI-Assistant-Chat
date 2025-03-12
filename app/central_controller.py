import logging

class CentralController:
    def __init__(self, bot_registry, task_scheduler, notification_service):
        self.bot_registry = bot_registry
        self.task_scheduler = task_scheduler
        self.notification_service = notification_service
        self.logger = logging.getLogger("ai-assistant.central-controller")

    async def initialize(self):
        """Initialize the central controller and its components"""
        try:
            # Initialize components if they have initialization methods
            components = [self.bot_registry, self.task_scheduler, self.notification_service]
            for component in components:
                if hasattr(component, 'initialize'):
                    await component.initialize()
            
            self.logger.info("Central Controller initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing Central Controller: {str(e)}", exc_info=True)
            return False 