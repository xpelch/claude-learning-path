"""Claude API lab: hybrid retrieval exercise (claude-learning-path). No API key needed.

Implement the three TODO functions, then run:  python retrieval_exercise.py
The self-checks at the bottom must all print "ok".
"""
import math
import re
from collections import Counter

REPORT = """## Section 1: Medical Research
This year saw progress on XDR-47, a bug we had not seen before.

## Section 2: Software Engineering
The team closed incident INC-2023-Q4-011 after hardening the distributed sync service.

## Section 3: Financial Analysis
Revenue grew 12 percent while infrastructure costs stayed flat.

## Section 4: Cybersecurity
Incident INC-2023-Q4-011 began with a leaked token; access was revoked within an hour.

## Section 5: Legal
Two contracts were renegotiated and one patent was filed."""


def chunk_by_section(text):
    """TODO: split the Markdown report into one chunk per '## ' section (keep the heading)."""
    raise NotImplementedError


def tokenize(text):
    return re.findall(r"[a-z0-9-]+", text.lower())


class BM25Index:
    """Provided: a small BM25 lexical index with add_document/search."""

    def __init__(self, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = [], k1, b

    def add_document(self, doc):
        self.docs.append((doc, Counter(tokenize(doc["content"]))))

    def search(self, query, k=3):
        n = len(self.docs)
        avg = sum(sum(c.values()) for _, c in self.docs) / n
        scores = []
        for doc, counts in self.docs:
            length, score = sum(counts.values()), 0.0
            for term in tokenize(query):
                df = sum(1 for _, c in self.docs if term in c)
                if not df:
                    continue
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                tf = counts[term]
                score += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / avg))
            scores.append((doc, score))
        return sorted(scores, key=lambda x: -x[1])[:k]


def rrf_scores(rankings, k=60):
    """TODO: Reciprocal Rank Fusion.

    rankings: list of ranked lists of document ids (best first), one list per index.
    Return {doc_id: sum over lists of 1 / (k + rank)} with rank starting at 1.
    """
    raise NotImplementedError


def fuse(rankings, k=60):
    """TODO: return document ids sorted by descending RRF score."""
    raise NotImplementedError


if __name__ == "__main__":
    chunks = chunk_by_section(REPORT)
    print("ok" if len(chunks) == 5 and chunks[1].lstrip("# ").startswith("Section 2") else "FAIL chunking")

    s = rrf_scores([["s2", "s7", "s6"], ["s6", "s2", "s7"]], k=1)
    print("ok" if round(s["s2"], 3) == 0.833 and round(s["s6"], 3) == 0.75 and round(s["s7"], 3) == 0.583
          else f"FAIL rrf {s}")
    print("ok" if fuse([["s2", "s7", "s6"], ["s6", "s2", "s7"]], k=1) == ["s2", "s6", "s7"] else "FAIL fuse")

    index = BM25Index()
    for i, c in enumerate(chunks):
        index.add_document({"id": f"s{i + 1}", "content": c})
    top = [d["id"] for d, _ in index.search("What happened with INC-2023-Q4-011?", k=2)]
    print("ok" if set(top) == {"s2", "s4"} else f"FAIL bm25 {top}")
