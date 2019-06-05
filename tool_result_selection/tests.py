from ThreeDiToolbox.models.datasources import TimeseriesDatasourceModel
from ThreeDiToolbox.tool_result_selection import log_in_dialog
from ThreeDiToolbox.tool_result_selection import result_downloader
from ThreeDiToolbox.tool_result_selection import result_selection

import mock


def test_log_in_dialog(qtbot):
    # Smoke test: just call it.
    log_in_dialog.LoginDialog()


def test_get_valid_filename():
    assert "johns_portrait_in_2004.jpg" == result_selection.get_valid_filename(
        "john's portrait in 2004.jpg"
    )


def test_download_result_model():
    # Smoke test, just initialize it.
    result_downloader.DownloadResultModel()


def test_result_selection_tool_init():
    iface = mock.Mock()
    ts_datasource = TimeseriesDatasourceModel()
    result_selection_tool = result_selection.ThreeDiResultSelection(
        iface, ts_datasource
    )
    assert "icon_add_datasource.png" in result_selection_tool.icon_path