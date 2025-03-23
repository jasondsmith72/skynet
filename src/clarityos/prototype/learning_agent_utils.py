"""
Learning Agent Utility Functions

This module provides utility functions for the Learning Agent
to manage observations, hypotheses, and knowledge.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from clarityos.core.message_bus import MessagePriority, system_bus
from clarityos.prototype.learning_models import (
    LearningMode, LearningDomain, Hypothesis, Observation, 
    Experiment, KnowledgeItem
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# These methods will be mixed into the LearningAgent class
async def create_observation(self, domain: LearningDomain, description: str, data: Dict[str, Any]) -> str:
    """Create a new observation."""
    observation_id = self._generate_id("observation")
    
    observation = Observation(
        id=observation_id,
        domain=domain,
        description=description,
        data=data
    )
    
    self.observations[observation_id] = observation
    
    return observation_id


async def create_hypothesis(self, domain: LearningDomain, description: str, confidence: float = 0.0) -> str:
    """Create a new hypothesis."""
    # Check if a similar hypothesis already exists
    for existing in self.hypotheses.values():
        if existing.domain == domain and existing.description == description:
            # Update confidence if this is higher
            if confidence > existing.confidence:
                existing.confidence = confidence
            return existing.id
    
    # Create new hypothesis
    hypothesis_id = self._generate_id("hypothesis")
    
    hypothesis = Hypothesis(
        id=hypothesis_id,
        domain=domain,
        description=description,
        confidence=confidence
    )
    
    self.hypotheses[hypothesis_id] = hypothesis
    
    logger.info(f"Created hypothesis: {description}")
    
    return hypothesis_id


async def create_knowledge_from_hypothesis(self, hypothesis_id: str) -> Optional[str]:
    """Create a knowledge item from a confirmed hypothesis."""
    hypothesis = self.hypotheses.get(hypothesis_id)
    if not hypothesis:
        return None
    
    # Check if we already have similar knowledge
    for knowledge_item in self.knowledge.values():
        if knowledge_item.domain == hypothesis.domain and knowledge_item.description == hypothesis.description:
            # Update confidence if this is higher
            if hypothesis.confidence > knowledge_item.confidence:
                knowledge_item.confidence = hypothesis.confidence
                knowledge_item.last_updated = time.time()
            
            # Add to source hypotheses if not already there
            if hypothesis_id not in knowledge_item.source_hypotheses:
                knowledge_item.source_hypotheses.append(hypothesis_id)
            
            return knowledge_item.id
    
    # Create new knowledge item
    knowledge_id = self._generate_id("knowledge")
    
    knowledge_item = KnowledgeItem(
        id=knowledge_id,
        domain=hypothesis.domain,
        description=hypothesis.description,
        confidence=hypothesis.confidence,
        source_hypotheses=[hypothesis_id]
    )
    
    self.knowledge[knowledge_id] = knowledge_item
    
    logger.info(f"Created new knowledge item: {hypothesis.description}")
    
    # Announce new knowledge
    await system_bus.publish(
        message_type="learning.knowledge.created",
        content={
            "knowledge_id": knowledge_id,
            "domain": hypothesis.domain.value,
            "description": hypothesis.description,
            "confidence": hypothesis.confidence,
            "agent_id": self.agent_id
        },
        source=f"learning_agent_{self.agent_id}",
        priority=MessagePriority.NORMAL
    )
    
    return knowledge_id


def generate_id(self, prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    self._next_id_counter += 1
    return f"{prefix}_{self._next_id_counter}"


def choose_hypothesis_for_testing(self) -> Optional[str]:
    """Choose a hypothesis for testing."""
    if not self.hypotheses:
        return None
    
    # Filter to hypotheses with medium confidence (most interesting to test)
    candidates = [
        h_id for h_id, h in self.hypotheses.items()
        if 0.3 <= h.confidence <= 0.7 and h.tests_run < 5
    ]
    
    if not candidates:
        # If no medium confidence hypotheses, choose any untested one
        candidates = [
            h_id for h_id, h in self.hypotheses.items()
            if h.tests_run < 3
        ]
    
    if not candidates:
        # If still no candidates, choose randomly
        candidates = list(self.hypotheses.keys())
    
    if candidates:
        return random.choice(candidates)
    
    return None


def choose_weighted_domain(self) -> LearningDomain:
    """Choose a domain based on exploration weights."""
    domains = list(LearningDomain)
    weights = [self.exploration_weights.get(d, 1.0) for d in domains]
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        normalized_weights = [w / total_weight for w in weights]
    else:
        normalized_weights = [1.0 / len(domains)] * len(domains)
    
    # Choose weighted random domain
    r = random.random()
    cumulative = 0
    
    for i, weight in enumerate(normalized_weights):
        cumulative += weight
        if r <= cumulative:
            return domains[i]
    
    # Fallback
    return random.choice(domains)


def update_exploration_weights(self, explored_domain: LearningDomain) -> None:
    """Update weights to favor less-explored domains."""
    # Reduce weight for the domain we just explored
    self.exploration_weights[explored_domain] *= 0.8
    
    # Increase weights for other domains
    for domain in LearningDomain:
        if domain != explored_domain:
            self.exploration_weights[domain] *= 1.05
    
    # Ensure weights don't get too extreme
    for domain in LearningDomain:
        self.exploration_weights[domain] = max(0.1, min(5.0, self.exploration_weights[domain]))


def get_related_knowledge(self, domain: LearningDomain) -> List[KnowledgeItem]:
    """Get knowledge items related to a specific domain."""
    return [k for k in self.knowledge.values() if k.domain == domain]


def get_knowledge_by_confidence(self, min_confidence: float = 0.0) -> List[KnowledgeItem]:
    """Get knowledge items with confidence above the specified threshold."""
    return [k for k in self.knowledge.values() if k.confidence >= min_confidence]


def calculate_knowledge_coverage(self) -> Dict[LearningDomain, float]:
    """Calculate knowledge coverage across domains."""
    # In a real system, would have a more sophisticated measure
    # For the prototype, just count knowledge items per domain
    
    coverage = {domain: 0.0 for domain in LearningDomain}
    
    # Count hypotheses with significant confidence
    for hypothesis in self.hypotheses.values():
        if hypothesis.confidence >= 0.5:
            coverage[hypothesis.domain] += 0.1
    
    # Count knowledge items with weight by confidence
    for knowledge in self.knowledge.values():
        coverage[knowledge.domain] += knowledge.confidence * 0.5
    
    # Cap at 1.0 for full coverage
    for domain in coverage:
        coverage[domain] = min(1.0, coverage[domain])
    
    return coverage


def get_learning_priorities(self) -> List[Tuple[LearningDomain, float]]:
    """Get prioritized domains for learning focus."""
    coverage = self.calculate_knowledge_coverage()
    
    # Priority is inverse of coverage (focus on areas with less knowledge)
    priorities = [(domain, 1.0 - coverage[domain]) for domain in LearningDomain]
    
    # Sort by priority (higher values first)
    priorities.sort(key=lambda x: x[1], reverse=True)
    
    return priorities


def find_conflicting_hypotheses(self) -> List[Tuple[str, str]]:
    """Find pairs of hypotheses that might conflict with each other."""
    # In a real system, would have a more sophisticated conflict detection
    # For the prototype, detect based on keywords
    
    conflicts = []
    
    # Simple string-based conflict detection for demonstration
    hypotheses = list(self.hypotheses.items())
    
    for i, (h1_id, h1) in enumerate(hypotheses):
        for h2_id, h2 in hypotheses[i+1:]:
            # Skip if different domains
            if h1.domain != h2.domain:
                continue
                
            # Check for contradictory phrases
            if ("improves" in h1.description and "degrades" in h2.description) or \
               ("increases" in h1.description and "decreases" in h2.description) or \
               ("better" in h1.description and "worse" in h2.description):
                conflicts.append((h1_id, h2_id))
    
    return conflicts


async def resolve_hypothesis_conflict(self, h1_id: str, h2_id: str) -> Optional[str]:
    """Attempt to resolve a conflict between hypotheses through experimentation."""
    h1 = self.hypotheses.get(h1_id)
    h2 = self.hypotheses.get(h2_id)
    
    if not h1 or not h2:
        return None
    
    # Design an experiment that can test both hypotheses
    experiment_id = self._generate_id("experiment")
    
    experiment = Experiment(
        id=experiment_id,
        hypothesis_id=f"{h1_id},{h2_id}",  # Track both hypotheses
        description=f"Resolving conflict: {h1.description} vs {h2.description}",
        parameters={"iterations": 20, "test_type": "comparative"},
        expected_outcome="Determine which hypothesis is more likely correct"
    )
    
    self.experiments[experiment_id] = experiment
    self._running_experiments.add(experiment_id)
    
    # Run the experiment
    experiment.started_at = time.time()
    asyncio.create_task(self._run_conflict_resolution_experiment(experiment_id))
    
    logger.info(f"Started conflict resolution experiment: {experiment_id}")
    
    return experiment_id


async def run_conflict_resolution_experiment(self, experiment_id: str) -> None:
    """Run an experiment to resolve conflicting hypotheses."""
    try:
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return
        
        # Parse the composite hypothesis ID
        hypothesis_ids = experiment.hypothesis_id.split(",")
        if len(hypothesis_ids) != 2:
            return
            
        h1_id, h2_id = hypothesis_ids
        h1 = self.hypotheses.get(h1_id)
        h2 = self.hypotheses.get(h2_id)
        
        if not h1 or not h2:
            return
        
        # Simulate experiment execution time
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # Simulate conflict resolution
        # In a real system, would run actual comparative tests
        
        # Weighted random selection based on prior confidence
        total_confidence = h1.confidence + h2.confidence
        h1_probability = h1.confidence / total_confidence if total_confidence > 0 else 0.5
        
        winner_id = h1_id if random.random() < h1_probability else h2_id
        winner = h1 if winner_id == h1_id else h2
        loser_id = h2_id if winner_id == h1_id else h1_id
        loser = h2 if winner_id == h1_id else h1
        
        # Update experiment
        experiment.completed_at = time.time()
        experiment.success = True
        experiment.result = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "confidence_delta": random.uniform(0.1, 0.3)
        }
        
        # Update hypotheses
        winner.tests_run += 1
        winner.successful_tests += 1
        winner.last_tested = time.time()
        winner.confidence = min(1.0, winner.confidence + experiment.result["confidence_delta"])
        
        loser.tests_run += 1
        loser.last_tested = time.time()
        loser.confidence = max(0.0, loser.confidence - experiment.result["confidence_delta"])
        
        # If winner has high confidence, convert to knowledge
        if winner.confidence >= self.min_confidence_threshold:
            await self._create_knowledge_from_hypothesis(winner_id)
        
        logger.info(
            f"Conflict resolution experiment {experiment_id} completed: "
            f"Winner: {winner.description} (confidence: {winner.confidence:.2f}), "
            f"Loser: {loser.description} (confidence: {loser.confidence:.2f})"
        )
    
    except Exception as e:
        logger.error(f"Error in conflict resolution experiment {experiment_id}: {str(e)}")
    
    finally:
        # Remove from running experiments
        self._running_experiments.discard(experiment_id)
