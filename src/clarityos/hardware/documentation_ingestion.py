"""
Documentation Ingestion System

This module implements a system for ingesting and processing hardware documentation
from various sources. It enables ClarityOS to learn about hardware components through
technical documentation.
"""

import os
import json
import re
import aiohttp
import aiofiles
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Processes documents to extract structured hardware knowledge.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
    async def extract_hardware_knowledge(self, 
                                         text_content: str, 
                                         component_type: Optional[str] = None,
                                         specifications: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract structured hardware knowledge from text content.
        
        Args:
            text_content: The text content to process
            component_type: Optional type of component to focus on
            specifications: Optional specifications to help narrow focus
            
        Returns:
            Dictionary with extraction results
        """
        # In a real implementation, this would use advanced NLP/AI techniques
        # For now, we'll implement a simple rule-based extraction
        
        results = {
            "success": False,
            "extracted_knowledge": []
        }
        
        try:
            # Extract component types mentioned in the text
            component_types = self._extract_component_types(text_content)
            
            # Extract specifications for each component type
            for comp_type in component_types:
                # If a specific component type was requested, skip others
                if component_type and comp_type != component_type:
                    continue
                
                extracted_specs = self._extract_specifications(text_content, comp_type)
                extracted_behaviors = self._extract_behaviors(text_content, comp_type)
                extracted_interfaces = self._extract_interfaces(text_content, comp_type)
                
                # If we found any knowledge, add it to the results
                if extracted_specs or extracted_behaviors or extracted_interfaces:
                    results["extracted_knowledge"].append((
                        comp_type,
                        extracted_specs,
                        {
                            "behaviors": extracted_behaviors,
                            "interfaces": extracted_interfaces
                        }
                    ))
            
            results["success"] = len(results["extracted_knowledge"]) > 0
            return results
            
        except Exception as e:
            logger.error(f"Error extracting hardware knowledge: {str(e)}")
            results["error"] = str(e)
            return results
            
    def _extract_component_types(self, text_content: str) -> List[str]:
        """Extract component types mentioned in the text."""
        # Simple keyword-based extraction
        component_types = []
        
        # Common component type keywords
        cpu_keywords = ["cpu", "processor", "central processing unit"]
        gpu_keywords = ["gpu", "graphics", "graphics processing unit"]
        memory_keywords = ["memory", "ram", "ddr", "dimm"]
        storage_keywords = ["storage", "ssd", "hdd", "hard drive", "nvme"]
        motherboard_keywords = ["motherboard", "mainboard", "system board"]
        
        # Check for keywords
        text_lower = text_content.lower()
        
        if any(keyword in text_lower for keyword in cpu_keywords):
            component_types.append("cpu")
            
        if any(keyword in text_lower for keyword in gpu_keywords):
            component_types.append("gpu")
            
        if any(keyword in text_lower for keyword in memory_keywords):
            component_types.append("memory")
            
        if any(keyword in text_lower for keyword in storage_keywords):
            component_types.append("storage")
            
        if any(keyword in text_lower for keyword in motherboard_keywords):
            component_types.append("motherboard")
            
        return component_types
        
    def _extract_specifications(self, text_content: str, component_type: str) -> Dict[str, Any]:
        """Extract specifications for a component type."""
        specifications = {}
        text_lower = text_content.lower()
        
        # CPU specifications
        if component_type == "cpu":
            # Architecture
            architecture_patterns = [
                ("x86", ["x86", "x86-64", "amd64", "intel"]),
                ("arm", ["arm", "arm64", "aarch64"]),
                ("risc-v", ["risc-v", "riscv"])
            ]
            
            for arch, keywords in architecture_patterns:
                if any(keyword in text_lower for keyword in keywords):
                    specifications["architecture"] = arch
                    break
            
            # Cores and threads
            core_match = re.search(r'(\d+)\s*cores?', text_lower)
            if core_match:
                specifications["cores"] = int(core_match.group(1))
                
            thread_match = re.search(r'(\d+)\s*threads?', text_lower)
            if thread_match:
                specifications["threads"] = int(thread_match.group(1))
                
            # Frequency
            freq_match = re.search(r'(\d+\.?\d*)\s*(GHz|MHz)', text_lower)
            if freq_match:
                freq_value = float(freq_match.group(1))
                freq_unit = freq_match.group(2)
                if freq_unit == "MHz":
                    freq_value /= 1000  # Convert to GHz
                specifications["frequency"] = freq_value
                
            # Cache
            cache_match = re.search(r'(\d+\.?\d*)\s*(MB|KB)\s*cache', text_lower)
            if cache_match:
                cache_value = float(cache_match.group(1))
                cache_unit = cache_match.group(2)
                if cache_unit == "KB":
                    cache_value /= 1024  # Convert to MB
                specifications["cache"] = cache_value
        
        # Process other component types (simplified for brevity)
        else:
            # Extract common specifications across component types
            model_match = re.search(rf'{component_type}\s+model:?\s+([a-z0-9\-]+)', text_lower)
            if model_match:
                specifications["model"] = model_match.group(1)
                
        return specifications
    
    def _extract_behaviors(self, text_content: str, component_type: str) -> Dict[str, Any]:
        """Extract behavioral characteristics of a component."""
        behaviors = {}
        text_lower = text_content.lower()
        
        # Power characteristics
        power_match = re.search(r'(\d+\.?\d*)\s*W(atts)?', text_lower)
        if power_match:
            behaviors["power_consumption"] = float(power_match.group(1))
            
        # Temperature characteristics
        temp_match = re.search(r'(\d+\.?\d*)\s*°C', text_lower)
        if temp_match:
            behaviors["operating_temperature"] = float(temp_match.group(1))
            
        # Performance modes
        if "power saving mode" in text_lower or "energy saving" in text_lower:
            behaviors["has_power_saving_mode"] = True
            
        if "turbo" in text_lower or "boost" in text_lower:
            behaviors["has_performance_boost"] = True
            
        return behaviors
    
    def _extract_interfaces(self, text_content: str, component_type: str) -> Dict[str, Any]:
        """Extract interface information for a component."""
        interfaces = {}
        text_lower = text_content.lower()
        
        # Bus interfaces
        if "pci express" in text_lower or "pcie" in text_lower:
            interfaces["pcie"] = True
            
            # PCIe version
            pcie_version_match = re.search(r'pcie\s+(\d+\.\d+)', text_lower)
            if pcie_version_match:
                interfaces["pcie_version"] = pcie_version_match.group(1)
        
        # Memory interfaces
        if component_type == "cpu" or component_type == "memory":
            if "ddr4" in text_lower:
                interfaces["memory"] = "DDR4"
            elif "ddr5" in text_lower:
                interfaces["memory"] = "DDR5"
                
        # Storage interfaces
        if component_type == "storage" or component_type == "motherboard":
            if "sata" in text_lower:
                interfaces["sata"] = True
            if "nvme" in text_lower:
                interfaces["nvme"] = True
                
        return interfaces


class DocumentationIngestion:
    """
    System for ingesting and processing hardware documentation from various sources.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.doc_processor = DocumentProcessor()
        self.document_sources = []
        self.tasks = {}
        
    async def initialize(self):
        """Initialize the documentation ingestion system."""
        # Load configuration for document sources
        self.document_sources = self.config.get("document_sources", [
            {"name": "Manufacturer Datasheets", "type": "web", "base_url": "https://example.com/api/datasheets"},
            {"name": "Technical Standards", "type": "web", "base_url": "https://standards.example.org/api"},
            {"name": "Local Documentation", "type": "filesystem", "base_path": "/docs/hardware"}
        ])
        
        logger.info(f"Initialized documentation ingestion with {len(self.document_sources)} sources")
    
    async def schedule_documentation_search(self, component_type: str, specifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule a search for documentation about a specific hardware component.
        
        Args:
            component_type: Type of hardware component
            specifications: Dictionary of component specifications
        
        Returns:
            Dictionary with task information
        """
        # Generate a task ID
        task_id = f"doc-search-{component_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create the task
        self.tasks[task_id] = {
            "type": "documentation_search",
            "component_type": component_type,
            "specifications": specifications,
            "status": "scheduled",
            "created_at": datetime.now(),
            "sources": [],
            "results": []
        }
        
        # For each document source, schedule a search
        for source in self.document_sources:
            self.tasks[task_id]["sources"].append({
                "name": source["name"],
                "status": "pending"
            })
        
        logger.info(f"Scheduled documentation search task {task_id} for {component_type}")
        
        return {"task_id": task_id, "status": "scheduled"}
    
    async def process_documentation(self, source: str, content_type: str, content: Any) -> Dict[str, Any]:
        """
        Process documentation content to extract hardware knowledge.
        
        Args:
            source: Source of the documentation
            content_type: Type of content (PDF, HTML, etc.)
            content: The actual documentation content
            
        Returns:
            Dictionary with extraction results
        """
        # Convert documentation to text if needed
        if content_type == "pdf":
            text_content = await self._convert_pdf_to_text(content)
        elif content_type == "html":
            text_content = await self._extract_text_from_html(content)
        else:
            text_content = content
        
        # Process the text to extract structured information
        extraction_result = await self.doc_processor.extract_hardware_knowledge(text_content)
        
        # Add source information
        extraction_result["source"] = source
        extraction_result["content_type"] = content_type
        extraction_result["processed_at"] = datetime.now().isoformat()
        
        return extraction_result
    
    async def _convert_pdf_to_text(self, pdf_content: bytes) -> str:
        """Convert PDF content to text."""
        # This would use a PDF extraction library in a real implementation
        # For now, return a placeholder
        return "PDF content would be extracted here"
    
    async def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text from HTML content."""
        # This would use an HTML parsing library in a real implementation
        # For now, return a placeholder
        return "HTML content would be extracted here"
