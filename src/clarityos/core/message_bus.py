 '*': Matches any sequence of characters within a single topic level
        - '#': Matches any number of topic levels (including zero)
        
        Examples:
        - 'system.cpu.*' matches 'system.cpu.usage' but not 'system.cpu.core.0.usage'
        - 'system.#' matches 'system.cpu.usage' and 'system.memory.free'
        
        Args:
            topic: Topic to check
            pattern: Pattern to match against
        
        Returns:
            True if the topic matches the pattern, False otherwise
        """
        # Split into parts
        topic_parts = topic.split('.')
        pattern_parts = pattern.split('.')
        
        # Simple check for exact match
        if pattern == topic:
            return True
        
        i, j = 0, 0
        while i < len(topic_parts) and j < len(pattern_parts):
            if pattern_parts[j] == '#':
                # '#' matches any number of levels, including zero
                return True
            elif pattern_parts[j] == '*':
                # '*' matches exactly one level
                i += 1
                j += 1
            elif pattern_parts[j] == topic_parts[i]:
                # Exact match for this level
                i += 1
                j += 1
            else:
                # No match
                return False
        
        # If we've consumed all of both topic and pattern, it's a match
        return i == len(topic_parts) and j == len(pattern_parts)