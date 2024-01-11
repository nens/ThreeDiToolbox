from ThreeDiToolbox.tool_result_selection import result_selection

import mock


def test_result_selection_tool_init():
    iface = mock.Mock()
    result_selection_tool = result_selection.ThreeDiResultSelection(
        iface, None
    )
    assert "icon_add_datasource.png" in result_selection_tool.icon_path
