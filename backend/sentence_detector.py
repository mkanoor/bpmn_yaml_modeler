"""
Sentence Boundary Detection for LLM Streaming

Detects sentence boundaries in streaming LLM output by buffering tokens
and checking for sentence-ending patterns.

Uses a conservative approach: better to send longer chunks than to split incorrectly.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class SentenceDetector:
    """
    Detects sentence boundaries in streaming text.

    Uses a conservative approach - only splits when we're confident it's
    a real sentence boundary. Better to send a longer chunk than to split
    in the middle of an abbreviation.
    """

    def __init__(self):
        self.buffer = ""

        # Common abbreviations that should NOT trigger sentence end
        self.abbreviations = {
            'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
            'inc', 'ltd', 'corp', 'co',
            'etc', 'vs', 'e.g', 'i.e', 'p.s',
            'st', 'ave', 'blvd', 'rd',
            'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            'u.s', 'u.k', 'u.s.a', 'ph.d', 'm.d', 'b.a', 'm.a', 'a.m', 'p.m'
        }

    def add_chunk(self, chunk: str) -> List[str]:
        """
        Add a streaming chunk and return any completed sentences.

        Args:
            chunk: New text chunk from LLM stream

        Returns:
            List of completed sentences (may be empty if no sentence ended yet)
        """
        self.buffer += chunk

        sentences = []

        # Look for clear sentence endings
        # Pattern: [.!?] followed by whitespace AND capital letter
        # This is conservative - requires both whitespace and capital
        search_pos = 0  # Track where to start searching to avoid re-checking false positives

        while True:
            # Find sentence-ending punctuation followed by space (but NOT newline) + capital
            # \s matches any whitespace including \n, so we use [ \t] to match only space/tab
            match = re.search(r'([.!?]+)[ \t]+([A-Z])', self.buffer[search_pos:])

            if not match:
                # No clear sentence boundary found
                break

            # Adjust positions based on search offset
            actual_start = search_pos + match.start()
            actual_end = search_pos + match.end()

            # Extract potential sentence (up to and including the punctuation)
            sentence_end_pos = actual_start + len(match.group(1))
            potential_sentence = self.buffer[:sentence_end_pos].strip()

            # Check if this looks like a false positive
            if self._is_false_positive(potential_sentence):
                # This is not a real sentence boundary
                # Move search position past this match to look for the next one
                # Don't modify the buffer - just skip this false positive
                search_pos = actual_end - 1  # Move past the punctuation but before the capital
                continue

            # This is a real sentence!
            sentences.append(potential_sentence)

            # Remove sentence from buffer (keep the space + capital for next sentence)
            self.buffer = self.buffer[sentence_end_pos:].lstrip()

            # Reset search position since we modified the buffer
            search_pos = 0

        return sentences

    def flush(self) -> str:
        """
        Flush remaining buffer as final sentence.

        Call this when stream is complete to get any remaining text.

        Returns:
            Remaining buffered text as final sentence
        """
        final_sentence = self.buffer.strip()
        self.buffer = ""
        return final_sentence

    def _is_false_positive(self, text: str) -> bool:
        """
        Check if sentence ending is a false positive (abbreviation, decimal, etc.)

        Args:
            text: Potential sentence text

        Returns:
            True if this is likely a false positive
        """
        # Get the last word before the period
        words = text.split()
        if not words:
            return True  # Empty text is not a sentence

        last_word = words[-1].lower().rstrip('.!?')

        # Check if last word is a known abbreviation
        if last_word in self.abbreviations:
            return True

        # Check for single-letter abbreviations (F., K., etc.)
        if re.match(r'^[a-z]$', last_word):
            return True

        # Check for numbered list items: "1.", "2.", etc.
        if re.match(r'^\d+$', last_word):
            return True

        # Check for numbered list items with single letter: "1. F", "2. K", etc.
        # This catches patterns like "1. F" where the sentence would be just "1. F"
        if len(words) == 2 and re.match(r'^\d+$', words[0].rstrip('.')) and re.match(r'^[a-z]$', last_word):
            return True

        # Check for decimal numbers: ends with digit (e.g., "4.99")
        if re.search(r'\d$', last_word):
            return True

        # Check if sentence is too short (likely incomplete)
        # Require at least 10 characters OR at least 2 words
        # Exception: if it has strong punctuation (!?) it's probably real
        has_strong_punctuation = bool(re.search(r'[!?]', text))
        if not has_strong_punctuation:
            if len(text.strip()) < 10 and len(words) < 2:
                return True

        # Check for common patterns that indicate this is NOT a sentence end
        # - Ends with single capital letter: "John F."
        if re.search(r'\b[A-Z]\.$', text):
            return True

        # - Contains colon near the end (section header): "PROCESS:"
        if re.search(r':\s*[.!?]*$', text):
            return True

        # - Colon followed by numbered list: "Steps: 1." or "Steps: 1. Parse logs carefully."
        # Check if text contains colon followed by number+period pattern
        if re.search(r':\s+\d+\.', text):
            return True

        return False

    def reset(self):
        """Reset the buffer"""
        self.buffer = ""


def test_sentence_detector():
    """Test the sentence detector with various cases"""
    detector = SentenceDetector()

    test_cases = [
        # Normal sentences
        ("Hello world. Next sentence here. ", ["Hello world."]),
        ("This is a test. Another sentence follows. ", ["This is a test."]),

        # Abbreviations (should NOT break)
        ("Mr. Smith went to the store. He bought milk. ", ["Mr. Smith went to the store."]),
        ("The U.S.A. is large. It has many states. ", ["The U.S.A. is large."]),

        # Decimals (should NOT break)
        ("The price is $4.99 today. Sale ends tomorrow. ", ["The price is $4.99 today."]),

        # Single letter abbreviations (should NOT break)
        ("John F. Kennedy was president. He was young. ", ["John F. Kennedy was president."]),
        ("F. Scott Fitzgerald wrote books. Great books. ", ["F. Scott Fitzgerald wrote books."]),

        # Numbered lists (should NOT break on the number)
        ("Steps: 1. Parse logs carefully. Then analyze. ", []),  # Wait - no clear boundary yet
        ("1. Analyze the log file carefully. Then review results. ", ["1. Analyze the log file carefully."]),

        # Very short text (should NOT break - wait for more context)
        ("Hi. ", []),  # Too short
        ("Hello there. How are you? ", ["Hello there."]),

        # Multiple punctuation
        ("What?! Really amazing. ", ["What?!"]),

        # Newlines
        ("First line.\nSecond line here.\n", []),  # Newline doesn't have capital after space

        # Real-world cases
        ("Found errors. Next step is analysis. ", ["Found errors."]),

        # Edge case: Sentence at buffer end (no capital after)
        ("This is complete.", []),  # Wait for more to confirm
    ]

    print("Testing SentenceDetector:")
    passed = 0
    failed = 0

    for input_text, expected in test_cases:
        detector.reset()

        # Simulate streaming (add one char at a time)
        sentences = []
        for char in input_text:
            result = detector.add_chunk(char)
            sentences.extend(result)

        # DON'T flush - we're testing real-time detection
        # In production, flush() is only called at the very end

        success = sentences == expected
        status = "✅" if success else "❌"
        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} Input: {repr(input_text)}")
        print(f"   Expected: {expected}")
        print(f"   Got:      {sentences}")
        if not success:
            print(f"   MISMATCH!")
        print()

    print(f"Results: {passed} passed, {failed} failed")


if __name__ == "__main__":
    test_sentence_detector()
