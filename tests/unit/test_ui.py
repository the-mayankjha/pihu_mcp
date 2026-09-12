import pytest
from pihu.ui.input import PihuCommandSuggester
from pihu.ui.renderer import TextualConsoleAdapter
from pihu.ui.phase_renderer import PhaseRenderer, ToolExecutionCard, get_server_icon_color
from pihu.ui.modals import ModelSelectModal, MCPListModal, ToolListModal, CommandPaletteModal
from pihu.ui.widgets import PihuFooterWidget
from pihu.mcp.manager import MCPManager
from rich.text import Text


@pytest.mark.asyncio
async def test_command_suggester():
    suggester = PihuCommandSuggester()
    s1 = await suggester.get_suggestion("/h")
    assert s1 == "/help"

    s2 = await suggester.get_suggestion("/m")
    assert s2 in ("/mcp", "/model", "/model gemini-3.6-flash")

    s3 = await suggester.get_suggestion("hello")
    assert s3 is None


def test_console_adapter_write():
    class DummyRichLog:
        def __init__(self):
            self.items = []

        def write(self, item):
            self.items.append(item)

    log = DummyRichLog()
    adapter = TextualConsoleAdapter(log)
    adapter.print("Hello world")
    assert len(log.items) == 1


def test_phase_renderer_and_tool_cards():
    icon, color = get_server_icon_color("pihu-file-mcp")
    assert icon == "◫"
    assert color == "#89b4fa"

    card = ToolExecutionCard(
        server="pihu-file-mcp",
        tool_name="write_file",
        elapsed_sec=0.022,
        output_summary="File written successfully",
        success=True,
    )
    rendered_card = card.render_row()
    assert rendered_card is not None

    panel = PhaseRenderer.render_grouped_tools([card])
    assert panel is not None

    phase_panel = PhaseRenderer.render_phase("Understanding", "Analyzing user request")
    assert phase_panel is not None


def test_console_adapter_render_tool_group():
    class DummyRichLog:
        def __init__(self):
            self.items = []

        def write(self, item):
            self.items.append(item)

    log = DummyRichLog()
    adapter = TextualConsoleAdapter(log)
    card = ToolExecutionCard("pihu-system-mcp", "run_shell", 0.45, "Executed command", True)
    adapter.render_tool_group([card])
    assert len(log.items) == 1


def test_modals_instantiation():
    mcp_mgr = MCPManager()
    modal1 = ModelSelectModal()
    modal2 = MCPListModal(mcp_mgr)
    modal3 = ToolListModal(mcp_mgr)
    modal4 = CommandPaletteModal()
    assert modal1 is not None
    assert modal2 is not None
    assert modal3 is not None
    assert modal4 is not None


def test_pihu_footer_widget():
    footer = PihuFooterWidget()
    footer.update_footer("gemini:gemini-3.6-flash", False)
    assert footer is not None
