#!/usr/bin/env python3
"""
JARVIS - Local AI Operating Layer
==================================

A voice-controlled AI assistant with 235+ features.

Usage:
    python main.py              # Start with voice
    python main.py --text       # Text-only mode
    python main.py --test       # Run tests
"""

import os
import sys
import argparse


def setup_paths():
    """Setup Python path for imports."""
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    dependencies = [
        ("ollama", "ollama"),
        ("pyaudio", "pyaudio"),
        ("numpy", "numpy"),
        ("psutil", "psutil"),
    ]
    
    for module, pip_name in dependencies:
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    return True


def run_voice_mode():
    """Run JARVIS with voice control."""
    from core.agent import JarvisAgent
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║        ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗           ║
    ║        ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝           ║
    ║        ██║███████║██████╔╝██║   ██║██║███████╗           ║
    ║   ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║           ║
    ║   ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║           ║
    ║    ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝           ║
    ║                                                           ║
    ║           Local AI Operating Layer v1.0.0                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    agent = JarvisAgent()
    agent.run()


def run_text_mode():
    """Run JARVIS in text-only mode (no voice)."""
    from core.agent import JarvisAgent
    
    print("JARVIS Text Mode")
    print("Type commands or 'quit' to exit\n")
    
    agent = JarvisAgent()
    
    while True:
        try:
            command = input("You: ").strip()
            
            if command.lower() in ["quit", "exit", "bye"]:
                print("Goodbye!")
                break
            
            if not command:
                continue
            
            result = agent.process_text_command(command)
            print(f"JARVIS: {result.response}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    agent.shutdown()


def run_tests():
    """Run component tests."""
    print("Running JARVIS tests...\n")
    
    # Test LLM
    print("1. Testing LLM...")
    try:
        from ai.llm import LLMClient
        llm = LLMClient()
        response = llm.generate("Say 'test passed' in 3 words or less")
        print(f"   LLM Response: {response.content}")
        print("   ✓ LLM OK")
    except Exception as e:
        print(f"   ✗ LLM Error: {e}")
    
    # Test Intent Parser
    print("\n2. Testing Intent Parser...")
    try:
        from core.intent_parser import IntentParser
        parser = IntentParser()
        result = parser.parse("open chrome")
        print(f"   Intent: {result.intent}, Entities: {result.entities}")
        print("   ✓ Intent Parser OK")
    except Exception as e:
        print(f"   ✗ Intent Parser Error: {e}")
    
    # Test Tool Registry
    print("\n3. Testing Tool Registry...")
    try:
        from tools.registry import get_registry
        registry = get_registry()
        tools = list(registry.tools.keys())
        print(f"   Registered tools: {len(tools)}")
        print(f"   Tools: {tools[:5]}...")
        print("   ✓ Tool Registry OK")
    except Exception as e:
        print(f"   ✗ Tool Registry Error: {e}")
    
    # Test Memory
    print("\n4. Testing Memory System...")
    try:
        from core.memory import MemorySystem
        memory = MemorySystem(
            db_path="./storage/test.db",
            chroma_path="./storage/test_chroma",
        )
        memory.log_command("test", "test_intent", {}, True, 0.1)
        commands = memory.get_recent_commands(1)
        print(f"   Logged command: {commands[0]['command']}")
        memory.close()
        print("   ✓ Memory System OK")
    except Exception as e:
        print(f"   ✗ Memory System Error: {e}")
    
    # Test Confidence Scorer
    print("\n5. Testing Confidence Scorer...")
    try:
        from core.confidence import ConfidenceScorer
        scorer = ConfidenceScorer()
        result = scorer.score(0.9, "low")
        print(f"   Score: {result.score:.2f}, Mode: {result.mode.value}")
        print("   ✓ Confidence Scorer OK")
    except Exception as e:
        print(f"   ✗ Confidence Scorer Error: {e}")
    
    print("\n" + "="*50)
    print("Tests complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JARVIS - Local AI Operating Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--text", "-t",
        action="store_true",
        help="Run in text-only mode (no voice)",
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run component tests",
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="JARVIS v1.0.0",
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_paths()
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install missing dependencies first.")
        sys.exit(1)
    
    # Run appropriate mode
    if args.test:
        run_tests()
    elif args.text:
        run_text_mode()
    else:
        run_voice_mode()


if __name__ == "__main__":
    main()
