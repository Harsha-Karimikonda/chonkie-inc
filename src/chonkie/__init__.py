"""Main package for Chonkie."""

from .chunker import (
    BaseChunker,
    CodeChunker,
    LateChunker,
    RecursiveChunker,
    SDPMChunker,
    SemanticChunker,
    SentenceChunker,
    SlumberChunker,
    TokenChunker,
)
from .embeddings import (
    AutoEmbeddings,
    BaseEmbeddings,
    CohereEmbeddings,
    JinaEmbeddings,
    Model2VecEmbeddings,
    OpenAIEmbeddings,
    SentenceTransformerEmbeddings,
)
from .genie import (
    BaseGenie,
    GeminiGenie,
)
from .refinery import (
    BaseRefinery,
    EmbeddingsRefinery,
    OverlapRefinery,
)
from .tokenizer import CharacterTokenizer, Tokenizer, WordTokenizer
from .types import (
    Chunk,
    CodeChunk,
    Context,
    LateChunk,
    RecursiveChunk,
    RecursiveLevel,
    RecursiveRules,
    SemanticChunk,
    SemanticSentence,
    Sentence,
    SentenceChunk,
)
from .utils import (
    Hubbie,
    Visualizer,
)

# This hippo grows with every release 🦛✨~
__version__ = "1.0.6a0"
__name__ = "chonkie"
__author__ = "🦛 Chonkie Inc"

# Add basic package metadata to __all__
__all__ = [
    "__name__",
    "__version__",
    "__author__",
]

# Add all data classes to __all__
__all__ += [
    "Context",
    "Chunk",
    "RecursiveChunk",
    "RecursiveLevel",
    "RecursiveRules",
    "SentenceChunk",
    "SemanticChunk",
    "Sentence",
    "SemanticSentence",
    "LateChunk",
    "CodeChunk",
]

# Add all tokenizer classes to __all__
__all__ += [
    "Tokenizer",
    "CharacterTokenizer",
    "WordTokenizer",
]

# Add all chunker classes to __all__
__all__ += [
    "BaseChunker",
    "TokenChunker",
    "SentenceChunker",
    "SemanticChunker",
    "SDPMChunker",
    "RecursiveChunker",
    "LateChunker",
    "CodeChunker",
    "SlumberChunker",
]

# Add all embeddings classes to __all__
__all__ += [
    "BaseEmbeddings",
    "Model2VecEmbeddings",
    "SentenceTransformerEmbeddings",
    "OpenAIEmbeddings",
    "CohereEmbeddings",
    "AutoEmbeddings",
    "JinaEmbeddings",
]

# Add all refinery classes to __all__
__all__ += [
    "BaseRefinery",
    "OverlapRefinery",
    "EmbeddingsRefinery",
]

# Add all utils classes to __all__
__all__ += [
    "Hubbie",
    "Visualizer",
]

# Add all genie classes to __all__
__all__ += [
    "BaseGenie",
    "GeminiGenie",
]