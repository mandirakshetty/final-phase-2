import json
import os
from typing import List, Dict, Any
from src.models.knowledge_entry import KnowledgeEntry
from src.services.vector_store import VectorStore
from src.utils.chunker import LogChunker

class KnowledgeBase:
    def __init__(self, kb_path: str = None, config_path="config.yaml"):
        self.kb_path = kb_path or "./data/kb/fixes.json"
        self.entries = []
        self.vector_store = VectorStore(index_name="kb_index", config_path=config_path)
        self.chunker = LogChunker()
        
        self.load_kb()
        self.index_kb()
    
    def load_kb(self):
        """Load knowledge base from JSON file"""
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r') as f:
                data = json.load(f)
                self.entries = [KnowledgeEntry(**entry) for entry in data]
        else:
            # Create default KB entries
            self.entries = [
                KnowledgeEntry(
                    issue="Database connection timeout",
                    root_cause="Connection pool exhausted or network latency",
                    solution="Increase connection pool size, check network connectivity",
                    affected_components=["Database", "API"],
                    tags=["database", "timeout", "connection"]
                ),
                KnowledgeEntry(
                    issue="API 500 Internal Server Error",
                    root_cause="Application code error or missing dependency",
                    solution="Check application logs, verify dependencies, restart service",
                    affected_components=["API", "Application Server"],
                    tags=["api", "500", "server"]
                ),
                KnowledgeEntry(
                    issue="Configuration mismatch",
                    root_cause="Version mismatch between services or incorrect settings",
                    solution="Verify configuration files, ensure version compatibility",
                    affected_components=["All"],
                    tags=["config", "version", "settings"]
                )
            ]
            self.save_kb()
    
    def save_kb(self):
        """Save knowledge base to JSON file"""
        os.makedirs(os.path.dirname(self.kb_path), exist_ok=True)
        with open(self.kb_path, 'w') as f:
            json.dump([entry.__dict__ for entry in self.entries], f, indent=2)
    
    def index_kb(self):
        """Index KB entries in vector store"""
        texts = []
        metadatas = []
        
        for i, entry in enumerate(self.entries):
            # Create text representation for embedding
            text = f"Issue: {entry.issue}\nRoot Cause: {entry.root_cause}\nSolution: {entry.solution}"
            texts.append(text)
            
            metadata = {
                "id": i,
                "issue": entry.issue,
                "root_cause": entry.root_cause,
                "solution": entry.solution,
                "affected_components": entry.affected_components,
                "tags": entry.tags,
                "type": "kb_fix"
            }
            metadatas.append(metadata)
        
        self.vector_store.add_documents(texts, metadatas)
    
    def search_similar_issues(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for similar issues in KB"""
        results = self.vector_store.search(query, top_k)
        
        formatted_results = []
        for similarity, metadata in results:
            formatted_results.append({
                "similarity": round(similarity, 3),
                "issue": metadata["issue"],
                "root_cause": metadata["root_cause"],
                "solution": metadata["solution"],
                "affected_components": metadata["affected_components"],
                "confidence": "High" if similarity > 0.8 else "Medium" if similarity > 0.6 else "Low"
            })
        
        return formatted_results
    
    def add_fix(self, issue: str, root_cause: str, solution: str, 
                affected_components: List[str], tags: List[str]):
        """Add new fix to KB"""
        new_entry = KnowledgeEntry(
            issue=issue,
            root_cause=root_cause,
            solution=solution,
            affected_components=affected_components,
            tags=tags
        )
        self.entries.append(new_entry)
        self.save_kb()
        self.index_kb()  # Re-index
    
    
    # ... existing code ...
    
    def search_solutions(self, error_code: str) -> List[Dict]:
        """Search for solutions by error code - now searches both mock data and vector store"""
        solutions = []
        
        # Check mock data first
        mock_solutions = {
            "ERR-001": [
                {
                    'error_type': 'Database Connection Timeout',
                    'component': 'Database',
                    'confidence': 'High',
                    'root_cause': 'Connection pool exhaustion or network latency',
                    'solution_steps': [
                        'Increase connection pool size in application.properties',
                        'Check database server resources',
                        'Verify network connectivity',
                        'Add connection timeout retry logic'
                    ],
                    'prevention': 'Monitor connection pool metrics regularly',
                    'resources': ['DB Connection Guide', 'Troubleshooting Handbook']
                }
            ],
            "ERR-002": [
                {
                    'error_type': 'Memory Overflow',
                    'component': 'JVM',
                    'confidence': 'Medium',
                    'root_cause': 'Memory leak in application code',
                    'solution_steps': [
                        'Increase heap size with -Xmx parameter',
                        'Run memory profiler to identify leaks',
                        'Check for infinite loops',
                        'Review recent code changes'
                    ],
                    'prevention': 'Regular memory profiling and code reviews',
                    'resources': ['JVM Tuning Guide', 'Memory Management']
                }
            ]
        }
        
        # Return mock solutions if found
        if error_code in mock_solutions:
            return mock_solutions[error_code]
        
        # Fallback to vector search
        vector_results = self.search_similar_issues(error_code, top_k=2)
        for result in vector_results:
            solutions.append({
                'error_type': result['issue'],
                'component': result['affected_components'][0] if result['affected_components'] else 'Unknown',
                'confidence': result['confidence'],
                'root_cause': result['root_cause'],
                'solution_steps': [step.strip() for step in result['solution'].split('.') if step.strip()],
                'prevention': 'Regular monitoring and maintenance',
                'resources': ['Knowledge Base Entry']
            })
        
        return solutions
    
    def search_by_component(self, component: str) -> List[Dict]:
        """Search for solutions by component"""
        # Mock data - replace with actual KB lookup
        component_solutions = {
            "Database": [
                {
                    'error_type': 'Connection Issues',
                    'component': 'Database',
                    'confidence': 'High',
                    'root_cause': 'Connection pool configuration',
                    'solution_steps': [
                        'Check database connection string',
                        'Verify database credentials',
                        'Test network connectivity',
                        'Review connection pool settings'
                    ]
                }
            ],
            "API": [
                {
                    'error_type': 'Rate Limiting',
                    'component': 'API',
                    'confidence': 'Medium',
                    'root_cause': 'Too many requests to external service',
                    'solution_steps': [
                        'Implement request throttling',
                        'Add circuit breaker pattern',
                        'Cache API responses',
                        'Contact API provider for quota increase'
                    ]
                }
            ]
        }
        
        return component_solutions.get(component, [])