"""Simplified TUI Evolution Demo - Manual trigger with 'e' key.

Run: python core/examples/simple_tui_demo.py

Then press 'e' to trigger evolution and see the diff!
"""
import argparse
import asyncio
import tempfile

from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.goal import Goal
from framework.graph.node import NodeSpec
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.tui.app import AdenTUI


class StubGuard:
    def snapshot(self, graph):
        return "snap-demo"

    async def probation_run(self, snapshot_id, candidate_graph, steps=10):
        await asyncio.sleep(0.3)
        return type("VR", (), {"passed": True, "violations": [], "metrics": {}})()

    def approve(self, result):
        return bool(result.passed)

    def rollback(self, snapshot_id):
        return None

    def audit_log(self, entry):
        pass


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-path", type=str, default=None)
    args = parser.parse_args()

    storage_path = args.storage_path or tempfile.gettempdir()

    # Initial graph
    initial_graph = GraphSpec(
        id="demo-v1",
        goal_id="demo-goal",
        entry_node="start",
        nodes=[
            NodeSpec(id="start", name="Start", description="Entry", node_type="function"),
            NodeSpec(
                id="analyzer",
                name="Analyzer",
                description="Analyze",
                node_type="event_loop",
            ),
            NodeSpec(
                id="responder",
                name="Responder",
                description="Respond",
                node_type="event_loop",
            ),
        ],
        edges=[
            EdgeSpec(id="e1", source="start", target="analyzer", condition="always"),
            EdgeSpec(id="e2", source="analyzer", target="responder", condition="always"),
        ],
        terminal_nodes=["responder"],
    )

    goal = Goal(id="demo-goal", name="Demo", description="Visual diff demo")

    runtime = create_agent_runtime(
        graph=initial_graph,
        goal=goal,
        storage_path=storage_path,
        entry_points=[
            EntryPointSpec(
                id="demo",
                name="Demo",
                entry_node="start",
                trigger_type="manual",
                isolation_level="shared",
            )
        ],
        evolution_guard=StubGuard(),
        enable_logging=False,
    )

    runtime.greeting = (
        "[bold cyan]Graph Evolution Visual Diff Demo[/bold cyan]\n\n"
        "[yellow]Evolution will trigger in 2 seconds![/yellow]\n\n"
        "After evolution, you'll see:\n"
        "  • [green]Green[/green] for added nodes/edges\n"
        "  • [yellow]Yellow[/yellow] for modified nodes\n"
        "  • Property-level diffs\n\n"
        "Controls:\n"
        "  • [cyan]d[/cyan] - Toggle diff mode\n"
        "  • [cyan]↑/↓[/cyan] - Navigate modified nodes\n"
        "  • [cyan]Enter[/cyan] - Show full diff\n"
        "  • [cyan]q[/cyan] - Quit\n"
    )

    await runtime.start()

    # Create evolved graph for manual trigger
    evolved_graph = GraphSpec(
        id="demo-v2-evolved",
        goal_id="demo-goal",
        entry_node="start",
        nodes=[
            NodeSpec(id="start", name="Start", description="Entry", node_type="function"),
            NodeSpec(
                id="analyzer",
                name="Analyzer",
                description="Analyze",
                node_type="event_loop",
            ),
            NodeSpec(
                id="responder",
                name="Responder",
                description="Respond",
                node_type="event_loop",
            ),
            NodeSpec(
                id="validator",
                name="Validator",
                description="Validate",
                node_type="function",
            ),
        ],
        edges=[
            EdgeSpec(id="e1", source="start", target="analyzer", condition="always"),
            EdgeSpec(id="e2", source="analyzer", target="responder", condition="always"),
            EdgeSpec(id="e3", source="responder", target="validator", condition="always"),
        ],
        terminal_nodes=["validator"],
    )

    # Trigger evolution automatically after 2 seconds
    async def trigger_after_delay():
        await asyncio.sleep(2)
        await runtime.update_graph(evolved_graph, correlation_id="auto-trigger")

    tui = AdenTUI(runtime=runtime)

    # Run TUI with evolution trigger
    async def run_with_trigger():
        task = asyncio.create_task(trigger_after_delay())
        try:
            await tui.run_async()
        finally:
            if not task.done():
                task.cancel()

    await run_with_trigger()
    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
