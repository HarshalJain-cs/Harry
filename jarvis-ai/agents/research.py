"""
JARVIS Research Agent - Information gathering and synthesis.

Specialized agent for web research, summarization, and fact-finding.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json

from .base import Agent, AgentResult, AgentState


@dataclass
class ResearchFinding:
    """A research finding."""
    topic: str
    summary: str
    sources: List[str]
    confidence: float


@dataclass
class ResearchReport:
    """A complete research report."""
    query: str
    findings: List[ResearchFinding]
    synthesis: str
    sources_used: List[str]


class ResearchAgent(Agent):
    """
    Agent specialized for research tasks.
    
    Features:
    - Web searching
    - Content extraction
    - Summarization
    - Source tracking
    - Fact synthesis
    """
    
    SYSTEM_PROMPT = """You are a research agent that finds and synthesizes information.

Your process:
1. Break the query into searchable sub-questions
2. Search for each sub-question
3. Extract key facts from results
4. Synthesize findings into a coherent answer

Always cite sources and indicate confidence levels.

For each step, respond with JSON:
{"action": "search|extract|synthesize|complete", "params": {...}, "reasoning": "..."}

When synthesizing, combine all findings into a comprehensive answer."""
    
    def __init__(
        self,
        name: str = "researcher",
        max_searches: int = 5,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.max_searches = max_searches
        self.findings: List[ResearchFinding] = []
        self.sources: List[str] = []
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def research(self, query: str, depth: str = "normal") -> ResearchReport:
        """
        Conduct research on a query.
        
        Args:
            query: Research question
            depth: "quick", "normal", or "deep"
            
        Returns:
            ResearchReport with findings
        """
        self._init_components()
        
        self.findings.clear()
        self.sources.clear()
        
        self.log(f"Researching: {query}")
        self.log(f"Depth: {depth}")
        
        # Determine search count based on depth
        search_count = {
            "quick": 2,
            "normal": 4,
            "deep": 8,
        }.get(depth, 4)
        
        search_count = min(search_count, self.max_searches)
        
        # Step 1: Generate sub-questions
        sub_questions = self._generate_sub_questions(query, search_count)
        self.log(f"Sub-questions: {len(sub_questions)}")
        
        # Step 2: Search for each question
        for q in sub_questions:
            self._search_and_extract(q)
        
        # Step 3: Synthesize findings
        synthesis = self._synthesize_findings(query)
        
        return ResearchReport(
            query=query,
            findings=self.findings,
            synthesis=synthesis,
            sources_used=list(set(self.sources)),
        )
    
    def _generate_sub_questions(self, query: str, count: int) -> List[str]:
        """Break query into searchable sub-questions."""
        prompt = f"""Break this research query into {count} specific, searchable questions:

Query: {query}

Respond with JSON: {{"questions": ["question1", "question2", ...]}}"""
        
        response = self.think(prompt)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("questions", [query])[:count]
        except:
            pass
        
        return [query]
    
    def _search_and_extract(self, question: str):
        """Search and extract findings for a question."""
        try:
            # Use web search tool
            result = self.tools.execute("web_search", {"query": question})
            
            if result and result.success:
                # Extract key facts using LLM
                content = str(result.output)[:2000]
                
                prompt = f"""Extract key facts from this search result:

Question: {question}
Result: {content}

Respond with JSON: {{"facts": ["fact1", "fact2"], "confidence": 0.8}}"""
                
                response = self.think(prompt)
                
                try:
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        
                        facts = data.get("facts", [])
                        confidence = data.get("confidence", 0.7)
                        
                        if facts:
                            self.findings.append(ResearchFinding(
                                topic=question,
                                summary="; ".join(facts[:3]),
                                sources=["web_search"],
                                confidence=confidence,
                            ))
                except:
                    pass
        
        except Exception as e:
            self.log(f"Search failed: {e}")
    
    def _synthesize_findings(self, original_query: str) -> str:
        """Synthesize all findings into a comprehensive answer."""
        if not self.findings:
            return "No findings were collected during research."
        
        findings_text = []
        for f in self.findings:
            findings_text.append(f"- {f.topic}: {f.summary}")
        
        prompt = f"""Synthesize these research findings into a comprehensive answer:

Original question: {original_query}

Findings:
{chr(10).join(findings_text)}

Provide a well-organized, factual answer. If there are conflicting findings, note them."""
        
        response = self.think(prompt)
        return response
    
    def run(self, task: str, context: Dict = None) -> AgentResult:
        """Run research on a task."""
        import time
        start_time = time.time()
        
        depth = "normal"
        if context:
            depth = context.get("depth", "normal")
        
        report = self.research(task, depth)
        
        return AgentResult(
            success=len(report.findings) > 0,
            output=report,
            steps=self.steps,
            total_time=time.time() - start_time,
        )


if __name__ == "__main__":
    print("Testing Research Agent...")
    
    researcher = ResearchAgent(name="researcher", verbose=True)
    
    query = "What are the benefits of Python type hints?"
    
    print(f"\nQuery: {query}")
    print("\nResearching (this requires web access)...")
    
    try:
        result = researcher.run(query, {"depth": "quick"})
        report = result.output
        
        print(f"\n--- Research Report ---")
        print(f"Query: {report.query}")
        print(f"Findings: {len(report.findings)}")
        
        for f in report.findings:
            print(f"\n  Topic: {f.topic}")
            print(f"  Summary: {f.summary[:100]}...")
        
        print(f"\nSynthesis: {report.synthesis[:200]}...")
    except Exception as e:
        print(f"Error (may need LLM/tools): {e}")
    
    print("\nResearch agent test complete!")
