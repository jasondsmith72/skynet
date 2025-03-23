"""
AI Talent Integration System

This module implements a prototype of the AI Talent Integration Framework,
which allows the core OS AI to discover, integrate with, and learn from
specialized AI models with particular talents or capabilities.
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from clarityos.core.message_bus import MessagePriority, system_bus
from clarityos.prototype.talent_models import (
    TalentDomain, TalentLevel, IntegrationStatus,
    TalentCapability, AITalent, TalentRequest, TalentEvaluation
)
from clarityos.prototype.talent_discovery import (
    discover_local_talents, discover_api_talents
)
from clarityos.prototype.talent_execution import (
    execute_talent_request, generate_simulated_result
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TalentIntegrationSystem:
    """
    System for discovering, evaluating, integrating, and learning from
    specialized AI talents.
    
    This system allows the core OS AI to leverage specialized capabilities from
    other AI models, creating a collective intelligence that can dynamically
    grow and adapt as new AI capabilities become available.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Registered AI talents
        self.talents: Dict[str, AITalent] = {}
        
        # Active talent requests
        self.active_requests: Dict[str, TalentRequest] = {}
        
        # Capability benchmarks for evaluation
        self.benchmarks: Dict[str, Dict[str, Any]] = {}
        
        # Internal state
        self._next_id_counter = 0
        self._subscription_ids = []
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Discovery providers
        self._discovery_providers: Dict[str, Callable] = {}
        
        # Default limits
        self.max_concurrent_requests = self.config.get("max_concurrent_requests", 5)
        self.evaluation_timeout = self.config.get("evaluation_timeout", 30.0)
        self.request_timeout = self.config.get("request_timeout", 10.0)
    
    async def start(self):
        """Start the talent integration system."""
        if self._running:
            return
        
        logger.info("Starting AI Talent Integration System")
        
        # Register message handlers
        self._subscription_ids.append(
            system_bus.subscribe(
                "talent.discover",
                self._handle_talent_discover,
                "talent_integration"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "talent.request",
                self._handle_talent_request,
                "talent_integration"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "talent.evaluate",
                self._handle_talent_evaluate,
                "talent_integration"
            )
        )
        
        # Register default discovery providers
        self._register_default_discovery_providers()
        
        # Load benchmarks
        self._load_benchmarks()
        
        # Start background tasks
        asyncio.create_task(self._monitor_requests())
        asyncio.create_task(self._periodic_discovery())
        
        self._running = True
        logger.info("AI Talent Integration System started")
    
    async def stop(self):
        """Stop the talent integration system."""
        if not self._running:
            return
        
        logger.info("Stopping AI Talent Integration System")
        
        # Set shutdown event to stop background tasks
        self._shutdown_event.set()
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        # Cancel any ongoing requests
        for request_id in list(self.active_requests.keys()):
            await self._cancel_request(request_id)
        
        self._running = False
        logger.info("AI Talent Integration System stopped")
    
    async def register_talent(self, talent: AITalent) -> bool:
        """
        Register a new AI talent with the system.
        
        Args:
            talent: The AI talent to register
        
        Returns:
            True if successful, False if the talent was already registered
        """
        if talent.id in self.talents:
            logger.warning(f"Talent with ID {talent.id} already registered")
            return False
        
        self.talents[talent.id] = talent
        logger.info(f"Registered talent: {talent.name} (ID: {talent.id})")
        
        # Announce new talent
        await system_bus.publish(
            message_type="talent.registered",
            content={
                "talent_id": talent.id,
                "talent_name": talent.name,
                "capabilities": [
                    {
                        "id": cap.id,
                        "name": cap.name,
                        "domain": cap.domain.value,
                        "level": cap.level.value
                    }
                    for cap in talent.capabilities.values()
                ]
            },
            source="talent_integration",
            priority=MessagePriority.NORMAL
        )
        
        # Schedule evaluation if not already evaluated
        if talent.status == IntegrationStatus.DISCOVERED:
            asyncio.create_task(self._evaluate_talent(talent.id))
        
        return True
    
    async def request_talent(
        self, 
        talent_id: str, 
        capability_id: str, 
        parameters: Dict[str, Any],
        context: Dict[str, Any] = None,
        priority: int = 1
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Request the use of a specific talent capability.
        
        Args:
            talent_id: ID of the AI talent
            capability_id: ID of the specific capability
            parameters: Parameters for the capability execution
            context: Additional context for execution
            priority: Request priority (higher numbers = higher priority)
            
        Returns:
            Tuple of (success, message, result)
        """
        # Check if talent exists
        talent = self.talents.get(talent_id)
        if not talent:
            return False, f"Talent with ID {talent_id} not found", None
        
        # Check if capability exists
        capability = talent.capabilities.get(capability_id)
        if not capability:
            return False, f"Capability with ID {capability_id} not found for talent {talent.name}", None
        
        # Check if talent is integrated
        if talent.status != IntegrationStatus.INTEGRATED:
            return False, f"Talent {talent.name} is not fully integrated (status: {talent.status.value})", None
        
        # Create request
        request_id = self._generate_id("request")
        request = TalentRequest(
            id=request_id,
            talent_id=talent_id,
            capability_id=capability_id,
            parameters=parameters,
            context=context or {},
            priority=priority
        )
        
        # Add to active requests
        self.active_requests[request_id] = request
        
        # Execute request
        try:
            result = await execute_talent_request(request, talent, capability)
            
            # Update request and talent statistics
            request.completed_at = time.time()
            request.success = True
            request.result = result
            
            talent.last_used = time.time()
            talent.usage_count += 1
            
            # Add performance record
            execution_time = request.completed_at - request.started_at if request.started_at else 0
            talent.performance_history.append({
                "capability_id": request.capability_id,
                "execution_time": execution_time,
                "timestamp": time.time()
            })
            
            # Remove from active requests
            if request.id in self.active_requests:
                del self.active_requests[request.id]
            
            return True, "Request executed successfully", result
            
        except Exception as e:
            # Update request with error
            request.completed_at = time.time()
            request.success = False
            request.error = str(e)
            
            # Remove from active requests
            if request.id in self.active_requests:
                del self.active_requests[request.id]
            
            logger.error(f"Error executing talent request: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def register_discovery_provider(self, name: str, provider_func: Callable) -> bool:
        """
        Register a provider function for discovering AI talents.
        
        Args:
            name: Name of the discovery provider
            provider_func: Async function that discovers talents
            
        Returns:
            True if registered successfully, False if already exists
        """
        if name in self._discovery_providers:
            return False
            
        self._discovery_providers[name] = provider_func
        logger.info(f"Registered talent discovery provider: {name}")
        return True
    
    async def discover_talents(self) -> List[str]:
        """
        Discover new AI talents using all registered providers.
        
        Returns:
            List of discovered talent IDs
        """
        discovered_ids = []
        
        for provider_name, provider_func in self._discovery_providers.items():
            try:
                logger.info(f"Running talent discovery using provider: {provider_name}")
                talents = await provider_func()
                
                for talent in talents:
                    if talent.id not in self.talents:
                        success = await self.register_talent(talent)
                        if success:
                            discovered_ids.append(talent.id)
            
            except Exception as e:
                logger.error(f"Error in talent discovery provider {provider_name}: {str(e)}")
        
        if discovered_ids:
            logger.info(f"Discovered {len(discovered_ids)} new AI talents")
        
        return discovered_ids
    
    async def evaluate_talent(self, talent_id: str) -> Optional[Dict[str, TalentEvaluation]]:
        """
        Evaluate an AI talent against benchmarks.
        
        Args:
            talent_id: ID of the talent to evaluate
            
        Returns:
            Dictionary mapping capability IDs to evaluation results, or None if talent not found
        """
        return await self._evaluate_talent(talent_id)
    
    def get_capabilities_by_domain(self, domain: TalentDomain, min_level: TalentLevel = None) -> List[Tuple[str, str, TalentCapability]]:
        """
        Get all capabilities in a specific domain.
        
        Args:
            domain: Domain to filter capabilities
            min_level: Minimum talent level (optional)
            
        Returns:
            List of (talent_id, talent_name, capability) tuples
        """
        results = []
        
        for talent_id, talent in self.talents.items():
            if talent.status != IntegrationStatus.INTEGRATED:
                continue
                
            for capability_id, capability in talent.capabilities.items():
                if capability.domain == domain:
                    if min_level is None or capability.level.value >= min_level.value:
                        results.append((talent_id, talent.name, capability))
        
        # Sort by level (highest first)
        results.sort(key=lambda x: x[2].level.value, reverse=True)
        
        return results

    # Remaining methods are continued in talent_integration_ext.py
