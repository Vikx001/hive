"""TUI Evolution Demo - Visual demonstration of graph evolution diff mode.

This demo launches the full TUI and triggers a graph evolution so you can see
the visual diff mode in action.

Run with:
    source .venv/bin/activate
    python core/examples/tui_evolution_demo.py

Usage:
    - The TUI will launch showing the initial graph
    - After a few seconds, a GRAPH_EVOLUTION_REQUEST will be emitted
    - The runtime will propose and apply a candidate graph
    - The TUI will automatically enter DIFF MODE showing:
      * Green nodes/edges (added)
      * Red nodes/edges (removed)
      * Yellow nodes (modified) with property-level diffs

Keyboard controls:
    - 'd' - Toggle between diff mode and live graph view
    - '↑/↓' - Navigate through modified nodes in diff mode
    - 'Enter' - Show full diff for selected modified node
    - 'q' - Quit
"""
import argparse
import asyncio
import tempfile

from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.goal import Goal
from framework.graph.node import NodeSpec
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec
from framework.tui.app import AdenTUI


# Simple stub guard that always approves
class StubGuardApprove:
    def snapshot(self, graph):
        return "snap-demo"

    async def probation_run(self, snapshot_id, candidate_graph, steps=10):
        # Simulate some validation work
        await asyncio.sleep(0.5)
        return type("VR", (), {"passed": True, "violations": [], "metrics": {}})()

    def approve(self, result):
        return bool(result.passed)

    def rollback(self, snapshot_id):
        return None

    def audit_log(self, entry):
        pass  # Silent for TUI demo


async def trigger_evolution_after_delay(runtime: AgentRuntime, delay_seconds: float = 3.0):
    """After a delay, emit evolution request and apply a candidate graph."""
    await asyncio.sleep(delay_seconds)

    # Create a more interesting candidate graph with visible changes
    old_graph = runtime.graph

    candidate = GraphSpec(
        id="evolved-graph-v2",
        goal_id=old_graph.goal_id,
        entry_node="start",
        nodes=[
            NodeSpec(
                id="start",
                name="Start Node",
                description="Entry point",
                node_type="function",
            ),
            NodeSpec(
                id="analyzer",
                name="Analyzer",
                description="Analyze the input",
                node_type="event_loop",
            ),
            NodeSpec(
                id="responder",
                name="Responder",
                description="Generate response",
                node_type="event_loop",
            ),
            NodeSpec(
                id="validator",
                name="Validator",
                description="Validate output",
                node_type="function",
            ),  # NEW
        ],
        edges=[
            EdgeSpec(id="e1", source="start", target="analyzer", condition="always"),
            EdgeSpec(id="e2", source="analyzer", target="responder", condition="always"),
            EdgeSpec(id="e3", source="responder", target="validator", condition="always"),  # NEW
        ],
        terminal_nodes=["validator"],  # Changed from ["responder"]
    )

    # Emit evolution request (simulating aggregator)
    await runtime.event_bus.emit_graph_evolution_request(
        stream_id="tui_demo",
        context={"reason": "demo - showing visual diff", "timestamp": "now"},
        correlation_id="tui-demo-evolution",
    )

    # Small delay so the request event is visible
    await asyncio.sleep(0.5)

    # Apply the evolution (runtime will emit GRAPH_EVOLVED event)
    await runtime.update_graph(
        new_graph=candidate,
        correlation_id="tui-demo-evolution",
        probation_steps=5,
    )


async def main():
    parser = argparse.ArgumentParser(description="TUI Evolution Demo")
    parser.add_argument(
        "--storage-path",
        type=str,
        default=None,
        help="Storage path for runtime data",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay in seconds before triggering evolution (default: 3.0)",
    )
    args = parser.parse_args()

    storage_path = args.storage_path or tempfile.gettempdir()

    # Create initial graph
    initial_graph = GraphSpec(
        id="demo-graph-v1",
        goal_id="demo-goal",
        entry_node="start",
        nodes=[
            NodeSpec(
                id="start",
                name="Start Node",
                description="Entry point",
                node_type="function",
            ),
            NodeSpec(
                id="analyzer",
                name="Analyzer",
                description="Analyze the input",
                node_type="event_loop",
            ),
            NodeSpec(
                id="responder",
                name="Responder",
                description="Generate response",
                node_type="event_loop",
            ),
        ],
        edges=[
            EdgeSpec(id="e1", source="start", target="analyzer", condition="always"),
            EdgeSpec(id="e2", source="analyzer", target="responder", condition="always"),
        ],
        terminal_nodes=["responder"],
    )

    goal = Goal(
        id="demo-goal",
        name="Demo Goal",
        description="Demonstrate graph evolution visual diff",
    )

    # Create runtime with evolution guard
    guard = StubGuardApprove()
    runtime = create_agent_runtime(
        graph=initial_graph,
        goal=goal,
        storage_path=storage_path,
        entry_points=[
            EntryPointSpec(
                id="demo",
                name="Demo Entry",
                entry_node="start",
                trigger_type="manual",
                isolation_level="shared",
            )
        ],
        evolution_guard=guard,
        enable_logging=False,  # Quiet for demo
    )

    # Set a greeting message for the TUI
    runtime.greeting = (
        "[bold cyan]🔄 Graph Evolution Visual Diff Demo[/bold cyan]\n\n"
        "This demo shows the TUI's visual diff mode for self-evolving graphs.\n\n"
        "[yellow]What will happen:[/yellow]\n"
        f"  • In {args.delay} seconds, the graph will evolve\n"
        "  • The TUI will automatically enter DIFF MODE\n"
        "  • You'll see:\n"
        "    [green]+ Green[/green] for added nodes/edges\n"
        "    [red]- Red[/red] for removed nodes/edges\n"
        "    [yellow]~ Yellow[/yellow] for modified nodes\n\n"
        "[bold]Keyboard controls:[/bold]\n"
        "  • [cyan]d[/cyan] - Toggle diff mode on/off\n"
        "  • [cyan]↑/↓[/cyan] - Navigate modified nodes\n"
        "  • [cyan]Enter[/cyan] - Show full diff for selected node\n"
        "  • [cyan]q[/cyan] - Quit\n\n"
        "[dim]Waiting for evolution to trigger...[/dim]"
    )

    # Start the runtime
    await runtime.start()

    # Launch the TUI
    tui = AdenTUI(runtime=runtime)

    # Schedule the evolution to happen after delay (in the TUI's event loop)
    async def run_tui_with_evolution():
        # Start the evolution task
        evolution_task = asyncio.create_task(trigger_evolution_after_delay(runtime, args.delay))

        # Run the TUI
        try:
            await tui.run_async()
        finally:
            # Cancel evolution task if still running
            if not evolution_task.done():
                evolution_task.cancel()
                try:
                    await evolution_task
                except asyncio.CancelledError:
                    pass

    await run_tui_with_evolution()

    # Cleanup
    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
