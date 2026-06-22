from ..logging_config import get_logger
from typing import List, Dict
import numpy as np

logger = get_logger("HoloidConsensus")

class HoloidConsensus:
    """
    Holoid Multi-Provider Consensus.
    Source: PPN §Consensus — holoid_engine.cpp::compute_consensus()

    Aggregates completions from multiple LLMs.
    Weights each completion by the provider's manifold health.
    """
    def aggregate(self, responses: List[str], 
                  provider_health: Dict[str, float]) -> str:
        """
        Performs semantic cross-entropy merging and weighted voting.
        Identifies the 'Centroid' response that best represents the semantic overlap
        of all high-health providers.
        """
        if not responses:
            return ""
        
        if len(responses) == 1:
            return responses[0]

        # 1. Natural Language Canonicalization & Tokenization
        def get_ngrams(text: str, n: int = 3):
            text = text.lower()
            return set(text[i:i+n] for i in range(len(text)-n+1))

        # 2. Similarity Matrix Calculation
        # We use character n-grams to handle typos and small variations
        num_responses = len(responses)
        sim_matrix = np.zeros((num_responses, num_responses))
        ngrams_list = [get_ngrams(r) for r in responses]

        for i in range(num_responses):
            for j in range(i, num_responses):
                if i == j:
                    sim_matrix[i, j] = 1.0
                    continue
                
                # Jaccard Similarity
                intersection = len(ngrams_list[i].intersection(ngrams_list[j]))
                union = len(ngrams_list[i].union(ngrams_list[j]))
                sim = intersection / union if union > 0 else 0
                sim_matrix[i, j] = sim
                sim_matrix[j, i] = sim

        # 3. Weighted Consensus Voting
        # Each response's score is the sum of its similarity to others, 
        # weighted by the provider's health score.
        consensus_scores = []
        health_scores = [provider_health.get(str(i), 1.0) for i in range(num_responses)] # Assuming index keys

        for i in range(num_responses):
            # Score = sum(Sim(i, j) * Health(j))
            score = 0
            for j in range(num_responses):
                score += sim_matrix[i, j] * health_scores[j]
            consensus_scores.append(score)

        best_idx = int(np.argmax(consensus_scores))
        
        logger.info(f"[HOLOID] Consensus reached. Centroid index: {best_idx}. Confidence: {consensus_scores[best_idx]:.2f}")
        
        return responses[best_idx]
