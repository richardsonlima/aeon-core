"""
MCP YouTube Extractor Example

Extract video transcripts using the YouTube MCP server.

Setup:
    1. Get YouTube API key from https://console.cloud.google.com
    2. export YOUTUBE_API_KEY="your_key"
    3. python mcp_youtube_extractor.py
"""

import asyncio
import os
from aeon import Agent


class YouTubeTranscriptExtractor:
    """Extract transcripts from YouTube videos"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_transcript(self, video_id: str) -> str:
        """Get transcript for a YouTube video"""
        # In real implementation, this would use the YouTube MCP server
        # For now, we'll simulate it
        print(f"  Fetching transcript for video: {video_id}")
        
        # Simulate transcript
        transcript = """
        Hello everyone! Today we're talking about AI and machine learning.
        
        Machine learning is a subset of artificial intelligence that enables
        computers to learn from data without being explicitly programmed.
        
        There are three main types:
        1. Supervised learning - labeled data
        2. Unsupervised learning - unlabeled data
        3. Reinforcement learning - learning from feedback
        
        The key components are:
        - Data collection
        - Feature engineering
        - Model training
        - Evaluation
        - Deployment
        """
        
        return transcript.strip()

    async def summarize_transcript(self, agent: Agent, transcript: str) -> str:
        """Summarize a transcript using the agent"""
        prompt = f"""Summarize this YouTube transcript in 3-4 bullet points:
        
{transcript}

Focus on the key insights."""
        
        return agent.cortex.plan_action(
            system_prompt=agent.system_prompt,
            user_input=prompt,
            tools=[]
        )

    async def extract_key_topics(self, agent: Agent, transcript: str) -> list:
        """Extract key topics from transcript"""
        prompt = f"""Extract the 5 most important topics from this transcript:
        
{transcript}

Return as a comma-separated list."""
        
        response = agent.cortex.plan_action(
            system_prompt=agent.system_prompt,
            user_input=prompt,
            tools=[]
        )
        return [topic.strip() for topic in str(response).split(",")]


async def main():
    print("=" * 60)
    print("Æon Framework - YouTube Transcript Extractor")
    print("=" * 60)

    api_key = os.getenv("YOUTUBE_API_KEY", "demo_key")
    
    # Initialize agent
    agent = Agent(
        name="YouTubeAnalyzer",
        model="ollama/phi3.5",
        protocols=[]
    )

    # Initialize YouTube extractor
    youtube = YouTubeTranscriptExtractor(api_key=api_key)

    # Example video IDs
    videos = [
        ("dQw4w9WgXcQ", "Machine Learning Basics"),
        ("jNgP6d9HraI", "AI Introduction"),
    ]

    for video_id, title in videos:
        print(f"\\n[Processing] {title}")
        print("-" * 60)

        # Get transcript
        transcript = await youtube.get_transcript(video_id)
        print(f"Transcript preview: {transcript[:100]}...\\n")

        # Summarize
        print("Generating summary...")
        summary = await youtube.summarize_transcript(agent, transcript)
        print(f"Summary:\\n{summary}\\n")

        # Extract topics
        print("Extracting key topics...")
        topics = await youtube.extract_key_topics(agent, transcript)
        print(f"Topics: {', '.join(topics)}\\n")


if __name__ == "__main__":
    asyncio.run(main())
