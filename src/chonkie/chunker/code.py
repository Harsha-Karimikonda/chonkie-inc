"""Module containing CodeChunker class.

This module provides a CodeChunker class for splitting code into chunks of a specified size.

"""

from bisect import bisect_left
from itertools import accumulate
from typing import Any, List, Literal, Tuple, Union

from chonkie.chunker.base import BaseChunker
from chonkie.tokenizer import Tokenizer
from chonkie.types.code import CodeChunk


class CodeChunker(BaseChunker):
    """Chunker that recursively splits the code based on code context."""

    def __init__(self,
                 tokenizer_or_token_counter: Union[str, List, Any] = "gpt2",
                 chunk_size: int = 512,
                 language: str = "python",
                 return_type: Literal["chunks", "texts"] = "chunks") -> None:
        """Initialize a CodeChunker object."""
        # Lazy import dependencies to avoid importing them when not needed
        self._import_dependencies()

        # Initialize all the values
        self.tokenizer = Tokenizer(tokenizer_or_token_counter)
        self.chunk_size = chunk_size
        self.return_type = return_type

        # TODO: Check if this is one of the supported languages
        self.language = language 

        # Initialize a Parser based on the language
        self.parser: Parser = get_parser(language) 

    def _import_dependencies(self) -> None:
        """Import the dependencies for the CodeChunker."""
        # Lazy import dependencies to avoid importing them when not needed
        try:
            global Node, Parser, Tree, get_parser
            from tree_sitter import Node, Parser, Tree
            from tree_sitter_language_pack import get_parser
        except ImportError:
            raise ImportError("tree-sitter and tree-sitter-language-pack are not installed" + 
                             "Please install them using `pip install chonkie[code]`.")

    def _merge_node_groups(self, node_groups: List[List[Node]]) -> List[Node]:
        merged_node_group = []
        for group in node_groups: 
            merged_node_group.extend(group)
        return merged_node_group
        
    def _group_child_nodes(self, node: Node) -> Tuple[List[List[Node]], List[int]]:
        """Group the nodes together based on their token_counts."""
        # Some edge cases to break the recursion
        if len(node.children) == 0:
            return ([], []) # TODO: Think more about this case!
            
        # Initialize the node groups and group token counts
        node_groups = []
        group_token_counts = []

        # Have a current group and a current token count to keep track
        current_token_count = 0
        current_node_group = []
        for child in node.children:
            child_text = child.text.decode()
            token_count: int = self.tokenizer.count_tokens(child_text)
            # If the child itself is larger than chunk size then we need to split and group it
            if token_count > self.chunk_size:
                # Add whatever was there already
                if current_node_group:
                    node_groups.append(current_node_group)
                    group_token_counts.append(current_token_count)

                    current_node_group = []
                    current_token_count = 0
                    
                # Recursively, add the child groups
                child_groups, child_token_counts = self._group_child_nodes(child)
                node_groups.extend(child_groups)
                group_token_counts.extend(child_token_counts)
                
            elif current_token_count + token_count > self.chunk_size:
                # Add the current_node_group and token_count to the total
                node_groups.append(current_node_group)
                group_token_counts.append(current_token_count)

                # Re-init the current_node_group and token_count
                current_node_group = [child]
                current_token_count = token_count
            else:
                # Just add the child to the current_node_group
                current_node_group.append(child)
                current_token_count += token_count

        # Finally, if there's something still in the current_node_group, 
        # Add it as the last group
        if current_node_group:
            node_groups.append(current_node_group)
            group_token_counts.append(current_token_count)


        cumulative_group_token_counts = list(accumulate([0] + group_token_counts))
        # print(f"Initial Groups: {len(node_groups)}, Counts: {group_token_counts}, Cumulative: {cumulative_group_token_counts}") # Debugging Statement
        
        merged_node_groups: List[List[Node]] = [] # Explicit type hint
        merged_token_counts: List[int] = []      # Explicit type hint
        pos = 0
        while pos < len(node_groups):
            # Calculate the target cumulative count based on the start of the current position
            start_cumulative_count = cumulative_group_token_counts[pos]
            # We want to find the end point 'index' such that the sum from pos to index-1 is <= chunk_size
            # Or, cumulative[index] - cumulative[pos] should be <= chunk_size ideally,
            # but bisect helps find the boundary where it *exceeds* it.
            required_cumulative_target = start_cumulative_count + self.chunk_size

            # Find the first index where the cumulative sum meets or exceeds the target
            # Search only in the relevant part of the list: from pos + 1 onwards
            # lo=pos ensures we handle the case where the group at 'pos' itself exceeds chunk_size
            index = bisect_left(cumulative_group_token_counts, required_cumulative_target, lo=pos) - 1

            # If the group at pos itself meets/exceeds the target, bisect_left returns pos.
            # If bisect_left returns pos, it means the single group node_groups[pos]
            # should form its own merged group. We need index to be at least pos + 1
            # to form a valid slice node_groups[pos:index].
            if index == pos:
                 # Handle the case where the single group at pos is >= chunk_size
                 # or if it's the very last group.
                 index = pos + 1 # Take at least this one group

            # Clamp index to be within the bounds of node_groups slicing
            index = min(index, len(node_groups))

            # Ensure we always make progress
            if index <= pos:
                # This might happen if cumulative_group_token_counts has issues or
                # if bisect_left returns something unexpected. Force progress.
                index = pos + 1

            # Slice the original node_groups and merge them
            groups_to_merge = node_groups[pos:index]
            if not groups_to_merge:
                # Should not happen if index is always > pos, but safety check
                break
            merged_node_groups.append(self._merge_node_groups(groups_to_merge))

            # Calculate the token count for this merged group
            actual_merged_count = cumulative_group_token_counts[index] - cumulative_group_token_counts[pos]
            merged_token_counts.append(actual_merged_count)

            # Move the position marker to the start of the next potential merged group
            pos = index

        # print(f"Node: {node.type}, Merged Groups: {len(merged_node_groups)}, Merged Counts: {merged_token_counts}") # Debugging
        return (merged_node_groups, merged_token_counts)

    def _get_texts_from_node_groups(self,
                                    node_groups: List[List[Node]],
                                    original_text_bytes: bytes) -> List[str]:
        """Reconstructs the text for each node group using original byte offsets.

        This method ensures that whitespace and formatting between nodes
        within a group are preserved correctly.

        Args:
            node_groups: A list where each element is a list of Nodes
                         representing a chunk.
            original_text_bytes: The original source code encoded as bytes.

        Returns:
            A list of strings, where each string is the reconstructed text
            of the corresponding node group.

        """
        chunk_texts: List[str] = []
        if not original_text_bytes:
            return [] # Return empty list if original text was empty

        for i, group in enumerate(node_groups):
            if not group:
                # Skip if an empty group was somehow generated
                continue

            # Determine the start byte of the first node in the group
            start_node = group[0]
            start_byte = start_node.start_byte

            # Determine the end byte of the last node in the group
            end_node = group[-1]
            end_byte = end_node.end_byte

            # Basic validation for byte offsets
            if start_byte > end_byte:
                print(f"Warning: Skipping group due to invalid byte order. Start: {start_byte}, End: {end_byte}")
                continue
            if start_byte < 0 or end_byte > len(original_text_bytes):
                 print(f"Warning: Skipping group due to out-of-bounds byte offsets. Start: {start_byte}, End: {end_byte}, Text Length: {len(original_text_bytes)}")
                 continue
                
            # Add the gap bytes if this is not the last node_group
            if i < len(node_groups)-1:
                end_byte = node_groups[i+1][0].start_byte

            # Extract the slice from the original bytes
            chunk_bytes = original_text_bytes[start_byte:end_byte]

            # Decode the bytes into a string
            try:
                text = chunk_bytes.decode("utf-8", errors="ignore") # Or 'replace'
                chunk_texts.append(text)
            except Exception as e:
                print(f"Warning: Error decoding bytes for chunk ({start_byte}-{end_byte}): {e}")
                # Append an empty string or placeholder if decoding fails
                chunk_texts.append("")                

        # Post-processing to add any missing bytes between the node_groups and the original_text_bytes
        # If the starting point of the first node group doesn't start with 0, add the initial bytes
        if node_groups[0][0].start_byte != 0:
            chunk_texts[0] = original_text_bytes[:node_groups[0][0].start_byte].decode("utf-8", errors="ignore") + chunk_texts[0]
        # If the ending point of the last node group doesn't match with last point of the original_text_bytes, add the remaining bytes
        if node_groups[-1][-1].end_byte != len(original_text_bytes):
            chunk_texts[-1] = chunk_texts[-1] + original_text_bytes[node_groups[-1][-1].end_byte:].decode("utf-8", errors="ignore")
            
        return chunk_texts

    def _create_chunks(self,
                       texts: List[str],
                       token_counts: List[int],
                       node_groups: List[List[Node]]) -> List[CodeChunk]:
        """Create Code Chunks."""
        chunks = []
        current_index = 0
        for (token_count, (text, node_group)) in zip(token_counts, zip(texts, node_groups)): 
            chunks.append(CodeChunk(text=text, 
                                    start_index=current_index, 
                                    end_index=current_index + len(text),
                                    token_count=token_count,
                                    nodes=node_group))
            current_index += len(text)
        return chunks
        
    def chunk(self, text: str) -> Union[List[CodeChunk], List[str]]:
        """Recursively chunks the code based on context from tree-sitter."""
        if not text.strip(): # Handle empty or whitespace-only input
            return []

        original_text_bytes = text.encode("utf-8") # Store bytes

        # Create the parsing tree for the current code
        tree: Tree = self.parser.parse(original_text_bytes) # type: ignore
        root_node: Node = tree.root_node # type: ignore

        # Get the node_groups 
        node_groups, token_counts = self._group_child_nodes(root_node)
        texts: List[str] = self._get_texts_from_node_groups(node_groups, original_text_bytes)
        
        if self.return_type == "texts":
            return texts
        else:
            chunks = self._create_chunks(texts, token_counts, node_groups)
            return chunks 
        
    