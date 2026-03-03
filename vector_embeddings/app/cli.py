"""
Command-line interface for the embedding application.

Single Responsibility: Handle user interaction and display results.
"""

from typing import List, Tuple, Dict

from app.application import EmbeddingApp


class CLI:
    """
    Command-line interface for the embedding demo.
    
    Provides a simple loop for user interaction with the EmbeddingApp.
    """
    
    def __init__(self, app: EmbeddingApp):
        """
        Initialize the CLI with an application instance.
        
        Args:
            app: The EmbeddingApp to use for processing queries.
        """
        self.app = app
    
    def display_welcome(self) -> None:
        """Display welcome message and usage instructions."""
        print("=" * 70)
        print("Vector Embedding Demo")
        print("=" * 70)
        print()
        print("This application demonstrates:")
        print("  • Generating text embeddings using OpenAI")
        print("  • Storing embeddings in a vector database (ChromaDB)")
        print("  • Finding nearest neighbors via TWO methods:")
        print("    - Cosine Similarity (measures angle between vectors)")
        print("    - Euclidean Distance / k-NN (measures geometric distance)")
        print()
        print("Each prompt you enter will be:")
        print("  1. Embedded using OpenAI's embedding model")
        print("  2. Stored in the local vector database")
        print("  3. Searched using BOTH similarity methods in parallel")
        print()
        print("Type 'exit' to quit.")
        print("=" * 70)
        print()
    
    def format_cosine_results(
        self, 
        results: List[Tuple[str, float, float, str]]
    ) -> str:
        """
        Format cosine similarity search results for display.
        
        Args:
            results: List of (id, distance, similarity, text) tuples.
            
        Returns:
            Formatted string for terminal output.
        """
        if not results:
            return "No results found."
        
        output = "\n📊 COSINE SIMILARITY SEARCH:\n"
        output += "   (Measures angle between vectors - higher similarity = more similar)\n"
        for i, (doc_id, distance, similarity, text) in enumerate(results, 1):
            # Truncate long texts for display
            display_text = text if len(text) <= 55 else f"{text[:52]}..."
            output += f"  {i}. similarity={similarity:.4f} (dist={distance:.4f}) \"{display_text}\"\n"
        
        return output
    
    def format_knn_results(
        self, 
        results: List[Tuple[str, float, str]]
    ) -> str:
        """
        Format k-NN (Euclidean distance) search results for display.
        
        Args:
            results: List of (id, euclidean_distance, text) tuples.
            
        Returns:
            Formatted string for terminal output.
        """
        if not results:
            return "No results found."
        
        output = "\n📏 K-NEAREST NEIGHBORS (Euclidean Distance):\n"
        output += "   (Measures geometric distance - lower distance = more similar)\n"
        for i, (doc_id, euclidean_dist, text) in enumerate(results, 1):
            # Truncate long texts for display
            display_text = text if len(text) <= 55 else f"{text[:52]}..."
            output += f"  {i}. distance={euclidean_dist:.4f} \"{display_text}\"\n"
        
        return output
    
    def run(self) -> None:
        """
        Run the main CLI loop.
        
        Continuously prompts the user for input, processes queries,
        and displays results until the user types 'exit'.
        """
        self.display_welcome()
        
        while True:
            try:
                # Prompt user for input
                user_input = input("\nEnter a prompt (or 'exit' to quit): ").strip()
                
                # Check for exit command
                if user_input.lower() == 'exit':
                    print("\nGoodbye!")
                    break
                
                # Skip empty inputs
                if not user_input:
                    print("Please enter a non-empty prompt.")
                    continue
                
                # Process the query
                print("\nProcessing...")
                query_id, results = self.app.process_query(user_input, k=3)
                
                # Display results
                print(f"\n✓ Stored with ID: {query_id}")
                print(self.format_cosine_results(results['cosine']))
                print(self.format_knn_results(results['knn']))
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n✗ Error: {e}")
                print("Please try again or type 'exit' to quit.")
