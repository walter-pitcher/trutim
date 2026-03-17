"""
Command Language Model — contextual scoring for voice commands.

Provides n-gram and neural language model scoring to improve
speech recognition accuracy for platform-specific commands.
Constrains recognition output to valid command sequences.
"""
import numpy as np
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LMConfig:
    """Configuration for the command language model."""
    n_gram_order: int = 3
    smoothing: str = 'kneser_ney'
    discount: float = 0.75
    oov_penalty: float = -10.0
    beam_width: int = 5


class CommandLanguageModel:
    """
    Language model specialized for Trutim platform voice commands.

    Models the probability of command sequences to:
    1. Re-score ASR hypotheses
    2. Predict next likely tokens
    3. Validate command structure
    4. Resolve ambiguous recognition results

    Uses n-gram statistics learned from the command grammar plus
    a simple neural component for semantic scoring.
    """

    COMMAND_GRAMMAR = {
        'call': {
            'patterns': [
                ['call', '<user>'],
                ['call', 'user', '<user>'],
                ['video', 'call', '<user>'],
                ['start', 'call'],
                ['start', 'video', 'call'],
            ],
            'description': 'Initiate a voice or video call',
        },
        'message': {
            'patterns': [
                ['send', 'message', 'to', '<user>'],
                ['message', '<user>'],
                ['send', 'message'],
                ['send', 'to', '<user>'],
            ],
            'description': 'Send a text message',
        },
        'video': {
            'patterns': [
                ['video', 'call', '<user>'],
                ['start', 'video', 'call'],
                ['video', 'call'],
                ['start', 'video'],
            ],
            'description': 'Start a video call',
        },
        'room': {
            'patterns': [
                ['join', 'room', '<room>'],
                ['leave', 'room'],
                ['create', 'room', '<room>'],
                ['open', 'room', '<room>'],
            ],
            'description': 'Room management',
        },
        'media': {
            'patterns': [
                ['mute'],
                ['unmute'],
                ['mute', 'camera'],
                ['unmute', 'camera'],
                ['share', 'screen'],
                ['stop', 'share'],
                ['stop', 'screen', 'share'],
            ],
            'description': 'Media controls',
        },
        'navigation': {
            'patterns': [
                ['select', 'user', '<user>'],
                ['select', '<user>'],
                ['open', '<room>'],
                ['close'],
                ['back'],
                ['go', 'back'],
            ],
            'description': 'Navigation commands',
        },
        'confirmation': {
            'patterns': [
                ['yes'],
                ['no'],
                ['confirm'],
                ['cancel'],
            ],
            'description': 'Confirmation responses',
        },
    }

    def __init__(self, config: Optional[LMConfig] = None):
        self.config = config or LMConfig()

        self._unigrams: Dict[str, float] = {}
        self._bigrams: Dict[Tuple[str, str], float] = {}
        self._trigrams: Dict[Tuple[str, str, str], float] = {}

        self._transition_probs: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._build_ngram_model()

    def score_sequence(self, tokens: List[str]) -> float:
        """
        Score a token sequence using the n-gram language model.
        Returns log probability of the sequence.
        """
        if not tokens:
            return 0.0

        log_prob = 0.0
        padded = ['<s>', '<s>'] + [t.lower() for t in tokens] + ['</s>']

        for i in range(2, len(padded)):
            trigram = (padded[i-2], padded[i-1], padded[i])
            bigram = (padded[i-1], padded[i])
            unigram = padded[i]

            if trigram in self._trigrams:
                log_prob += np.log(self._trigrams[trigram] + 1e-10)
            elif bigram in self._bigrams:
                log_prob += np.log(self._bigrams[bigram] + 1e-10) * 0.8
            elif unigram in self._unigrams:
                log_prob += np.log(self._unigrams[unigram] + 1e-10) * 0.5
            else:
                log_prob += self.config.oov_penalty

        return log_prob

    def rescore_hypotheses(self, hypotheses: List[Dict]) -> List[Dict]:
        """
        Re-score ASR hypotheses using language model.
        Each hypothesis has 'text' and 'acoustic_score' keys.
        Returns sorted list (best first).
        """
        for hyp in hypotheses:
            tokens = hyp['text'].lower().split()
            lm_score = self.score_sequence(tokens)
            acoustic_score = hyp.get('acoustic_score', 0.0)

            hyp['lm_score'] = lm_score
            hyp['combined_score'] = (
                (1 - self.config.discount) * acoustic_score +
                self.config.discount * lm_score
            )

        return sorted(hypotheses, key=lambda h: h['combined_score'], reverse=True)

    def predict_next(self, context: List[str], top_k: int = 5) -> List[Dict]:
        """
        Predict most likely next tokens given context.
        Used for auto-completion and constrained decoding.
        """
        if not context:
            return [{'token': t, 'prob': p}
                    for t, p in sorted(self._unigrams.items(),
                                       key=lambda x: x[1], reverse=True)[:top_k]]

        last = context[-1].lower()
        candidates = self._transition_probs.get(last, {})

        if len(context) >= 2:
            second_last = context[-2].lower()
            trigram_candidates = {}
            for trigram, prob in self._trigrams.items():
                if trigram[0] == second_last and trigram[1] == last:
                    trigram_candidates[trigram[2]] = prob
            if trigram_candidates:
                candidates = trigram_candidates

        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [{'token': t, 'prob': p} for t, p in sorted_candidates[:top_k]]

    def validate_command(self, tokens: List[str]) -> Dict:
        """
        Validate if a token sequence matches a known command pattern.
        Returns match result with confidence.
        """
        tokens_lower = [t.lower() for t in tokens]

        best_match = None
        best_score = 0.0

        for category, grammar in self.COMMAND_GRAMMAR.items():
            for pattern in grammar['patterns']:
                score = self._match_pattern(tokens_lower, pattern)
                if score > best_score:
                    best_score = score
                    best_match = {
                        'category': category,
                        'pattern': pattern,
                        'description': grammar['description'],
                    }

        return {
            'valid': best_score > 0.5,
            'confidence': best_score,
            'match': best_match,
            'tokens': tokens_lower,
        }

    def get_valid_commands(self) -> List[Dict]:
        """Get all valid command patterns."""
        commands = []
        for category, grammar in self.COMMAND_GRAMMAR.items():
            for pattern in grammar['patterns']:
                commands.append({
                    'category': category,
                    'pattern': ' '.join(pattern),
                    'description': grammar['description'],
                })
        return commands

    def _build_ngram_model(self):
        """Build n-gram model from command grammar patterns."""
        all_sequences = []

        for category, grammar in self.COMMAND_GRAMMAR.items():
            for pattern in grammar['patterns']:
                concrete = [t for t in pattern if not t.startswith('<')]
                if concrete:
                    all_sequences.append(concrete)
                    for _ in range(10):
                        all_sequences.append(concrete)

        for seq in all_sequences:
            for token in seq:
                self._unigrams[token] = self._unigrams.get(token, 0) + 1

            for i in range(len(seq) - 1):
                bigram = (seq[i], seq[i+1])
                self._bigrams[bigram] = self._bigrams.get(bigram, 0) + 1
                self._transition_probs[seq[i]][seq[i+1]] = \
                    self._transition_probs[seq[i]].get(seq[i+1], 0) + 1

            for i in range(len(seq) - 2):
                trigram = (seq[i], seq[i+1], seq[i+2])
                self._trigrams[trigram] = self._trigrams.get(trigram, 0) + 1

        total_unigrams = sum(self._unigrams.values()) or 1
        for key in self._unigrams:
            self._unigrams[key] /= total_unigrams

        total_bigrams = sum(self._bigrams.values()) or 1
        for key in self._bigrams:
            self._bigrams[key] /= total_bigrams

        total_trigrams = sum(self._trigrams.values()) or 1
        for key in self._trigrams:
            self._trigrams[key] /= total_trigrams

        for from_token in self._transition_probs:
            total = sum(self._transition_probs[from_token].values())
            if total > 0:
                for to_token in self._transition_probs[from_token]:
                    self._transition_probs[from_token][to_token] /= total

    def _match_pattern(self, tokens: List[str], pattern: List[str]) -> float:
        """Score how well tokens match a command pattern."""
        if not tokens or not pattern:
            return 0.0

        concrete_pattern = [t for t in pattern if not t.startswith('<')]
        if not concrete_pattern:
            return 0.5

        matches = 0
        pattern_idx = 0

        for token in tokens:
            if pattern_idx >= len(concrete_pattern):
                break
            if token == concrete_pattern[pattern_idx]:
                matches += 1
                pattern_idx += 1
            elif pattern_idx < len(pattern) and pattern[pattern_idx].startswith('<'):
                pattern_idx += 1

        return matches / max(len(concrete_pattern), 1)
