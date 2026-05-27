"""Textual TUI for agentseq."""


def main():
    from .app import AgentSeqApp

    app = AgentSeqApp()
    app.run()
