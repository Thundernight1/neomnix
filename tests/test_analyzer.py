import asyncio
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.agents.cross_mapping_analyzer import CrossMappingAnalyzer

async def test():
    print("Initializing Analyzer...")
    analyzer = CrossMappingAnalyzer("compliance_rules.json")
    print(f"Rules Loaded: {len(analyzer.rules)} triggers found.")
    
    query = "path traversal"
    print(f"Analyzing: {query}")
    result = await analyzer.analyze(query)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(test())
