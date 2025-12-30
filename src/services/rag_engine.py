# src/services/rag_engine.py (SIMPLE & PRACTICAL VERSION)
from typing import List, Dict, Any
import yaml
from datetime import datetime

from src.services.vector_store_flexible import FlexibleVectorStore as VectorStore
from src.services.knowledge_base import KnowledgeBase
from src.utils.parser import LogParser

class RAGEngine:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.vector_store = VectorStore(config_path=config_path)
        self.knowledge_base = KnowledgeBase(config_path=config_path)
        self.parser = LogParser()
        
        print(f"🧠 RAG Engine initialized")
        print(f"📚 Knowledge Base: {len(self.knowledge_base.entries)} entries")
        print(f"📊 Vector Store: {self.vector_store.size()} documents")
    
    def find_exact_matches(self, query: str, log_text: str) -> List[str]:
        """Find exact error messages matching the query"""
        matches = []
        lines = log_text.split('\n')
        
        # Simple case-insensitive search
        query_lower = query.lower()
        
        for line in lines:
            if query_lower in line.lower() and 'ERROR' in line:
                matches.append(line)
        
        return matches
    
    def find_similar_errors(self, query: str, log_text: str) -> List[str]:
        """Find similar errors (fallback if no exact matches)"""
        similar = []
        lines = log_text.split('\n')
        
        # Keywords to look for
        keywords = ['connection', 'timeout', 'failed', 'error', 'drop', 'crash']
        query_words = query.lower().split()
        
        for line in lines:
            if 'ERROR' in line:
                line_lower = line.lower()
                # Check if any keyword matches
                for word in query_words + keywords:
                    if word in line_lower and len(word) > 3:
                        similar.append(line)
                        break
        
        return list(set(similar))  # Remove duplicates
    
    def get_relevant_solutions(self, error_lines: List[str]) -> List[Dict]:
        """Get KB solutions for the found errors"""
        solutions = []
        
        for line in error_lines[:5]:  # Check first 5 errors
            # Extract error code if present
            import re
            code_match = re.search(r'Code=([A-Z_]+)', line)
            
            if code_match:
                error_code = code_match.group(1)
                # Search KB using search_solutions (not search_similar_issues)
                kb_results = self.knowledge_base.search_solutions(error_code)
                if kb_results:
                    for kb_sol in kb_results[:1]:  # Take first solution
                        # Convert to the format expected by your app
                        solution_text = "\n".join(kb_sol.get('solution_steps', ['No steps provided']))
                        solutions.append({
                            "error": kb_sol.get('error_type', error_code),
                            "solution": solution_text,
                            "exact_match": True,
                            "source_line": line[:100] + "..." if len(line) > 100 else line
                        })
                else:
                    # Also try search_similar_issues as fallback
                    similar_issues = self.knowledge_base.search_similar_issues(error_code, top_k=1)
                    if similar_issues:
                        solutions.append({
                            "error": similar_issues[0]['issue'],
                            "solution": similar_issues[0]['solution'],
                            "exact_match": False,
                            "source_line": line[:100] + "..." if len(line) > 100 else line
                        })
        
        return solutions
    
    def process_query(self, query: str, log_data: Dict, zone: str = None, client: str = None) -> Dict:
        """Simple, practical RCA analysis"""
        if not log_data or 'raw' not in log_data:
            return {"error": "No log data available"}
        
        log_text = log_data['raw']
        
        # Step 1: Look for EXACT matches first
        exact_matches = self.find_exact_matches(query, log_text)
        
        # Step 2: If no exact matches, look for similar errors
        error_lines = exact_matches if exact_matches else self.find_similar_errors(query, log_text)
        
        # Step 3: Get solutions from KB
        solutions = self.get_relevant_solutions(error_lines)
        
        # Step 4: Count total errors in logs (for dashboard)
        all_error_lines = [line for line in log_text.split('\n') if 'ERROR' in line]
        
        # Extract unique components
        import re
        all_components = set()
        for line in all_error_lines:
            match = re.search(r'Component=([A-Za-z]+)', line)
            if match:
                all_components.add(match.group(1))
        
        # Step 5: Generate simple RCA
        rca = self._generate_simple_rca(query, log_data, error_lines, solutions)
        
        return {
            "rca": rca,
            "exact_matches": exact_matches,
            "similar_errors": error_lines if not exact_matches else [],
            "solutions": solutions,
            # Consistent keys for dashboard
            "log_stats": {
                "total_errors": len(all_error_lines),  # Now this exists!
                "file_count": log_data.get('file_count', 0),
                "unique_components": len(all_components),
                "query_matches": len(error_lines)
            }
        }
    
    def _generate_simple_rca(self, query: str, log_data: Dict, error_lines: List[str], solutions: List[Dict]) -> str:
        """Generate simple, understandable RCA"""
        
        if not error_lines:
            return f"❌ No errors found matching '{query}' in the logs."
        
        # Count unique errors
        import re
        error_codes = []
        for line in error_lines:
            match = re.search(r'Code=([A-Z_]+)', line)
            if match:
                error_codes.append(match.group(1))
        
        unique_errors = set(error_codes)
        
        rca = f"""
# 🔍 TROUBLESHOOTING RESULTS

## 📋 **What You Asked**
**Query**: "{query}"

## 📊 **What We Found**
**Logs Checked**: {log_data.get('zone', 'N/A')}/{log_data.get('client', 'N/A')}/{log_data.get('app', 'N/A')}
**Total Error Lines**: {len(error_lines)}
**Unique Error Types**: {len(unique_errors)}

## 🚨 **Errors Found**
"""
        
        # Show first 3 errors
        for i, line in enumerate(error_lines[:3], 1):
            # Clean up the line for display
            clean_line = line.replace(' - ERROR - ', ' | ').replace(' - App=', ' | App: ')
            rca += f"{i}. `{clean_line[:80]}...`\n"
        
        rca += "\n## 🛠️ **Recommended Fix**\n"
        
        if solutions:
            for i, sol in enumerate(solutions, 1):
                rca += f"\n**{sol['error']}**\n"
                # Format solution as bullet points
                solution_lines = sol['solution'].split('\n')
                for step in solution_lines:
                    if step.strip():
                        rca += f"• {step.strip()}\n"
        else:
            rca += "No specific solution in KB. Check the error details above.\n"
        
        rca += f"\n---\n*Analyzed at {datetime.now().strftime('%H:%M:%S')}*"
        
        return rca