package simhash

import (
	"hash/fnv"
	"strings"
	"unicode"
)

// Hash computes a 64-bit simhash for the given text.
// It tokenizes the text, hashes each token, and combines them
// using the simhash algorithm (sum bit-weight vectors, threshold at 0).
func Hash(text string) uint64 {
	tokens := tokenize(text)
	if len(tokens) == 0 {
		return 0
	}

	var v [64]int
	for _, token := range tokens {
		h := hashToken(token)
		for i := 0; i < 64; i++ {
			if h&(1<<uint(i)) != 0 {
				v[i]++
			} else {
				v[i]--
			}
		}
	}

	var result uint64
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			result |= 1 << uint(i)
		}
	}
	return result
}

// Distance returns the Hamming distance between two simhashes.
func Distance(a, b uint64) int {
	x := a ^ b
	count := 0
	for x != 0 {
		count++
		x &= x - 1
	}
	return count
}

// tokenize splits text into lowercase word tokens,
// stripping timestamps, numbers, and short noise tokens to improve clustering.
func tokenize(text string) []string {
	// Strip common timestamp prefixes: ISO8601, syslog-style
	text = stripTimestamps(text)
	text = strings.ToLower(text)

	var tokens []string
	var current strings.Builder

	for _, r := range text {
		if unicode.IsLetter(r) || r == '_' {
			current.WriteRune(r)
		} else {
			if current.Len() > 1 { // skip single-char tokens
				tokens = append(tokens, current.String())
			}
			current.Reset()
		}
	}
	if current.Len() > 1 {
		tokens = append(tokens, current.String())
	}

	return tokens
}

// stripTimestamps removes common timestamp patterns from log lines.
func stripTimestamps(text string) string {
	// ISO8601: 2026-03-19T12:00:01Z or 2026-03-19T12:00:01.123+09:00
	// Also: [2026-03-19 12:00:01] style
	result := text
	// Find first non-timestamp content by looking for log level keywords
	for _, prefix := range []string{"FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"} {
		idx := strings.Index(result, prefix)
		if idx > 0 && idx < 60 {
			result = result[idx:]
			break
		}
	}
	// Also try lowercase
	lower := strings.ToLower(result)
	for _, prefix := range []string{"fatal", "error", "warn", "info", "debug", "trace"} {
		idx := strings.Index(lower, prefix)
		if idx > 0 && idx < 60 {
			result = result[idx:]
			break
		}
	}
	return result
}

func hashToken(token string) uint64 {
	h := fnv.New64a()
	h.Write([]byte(token))
	return h.Sum64()
}
