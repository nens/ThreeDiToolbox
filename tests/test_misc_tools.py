from threedi_results_analysis import misc_tools

import mock


def test_show_logfile():
    iface = mock.Mock()
    show_logfile_action = misc_tools.ShowLogfile(iface)
    with mock.patch.object(misc_tools, "pop_up_info") as mock_pop_up_info:
        show_logfile_action.run()
        args, kwargs = mock_pop_up_info.call_args
        message = args[0]
        assert "threedi-qgis-log.txt" in message

    show_logfile_action.on_unload()  # Doesn't do anything, used for coverage.


def test_about():
    iface = mock.Mock()
    show_about_action = misc_tools.About(iface)
    with mock.patch.object(misc_tools, "pop_up_info") as mock_pop_up_info:
        show_about_action.run()
        args, kwargs = mock_pop_up_info.call_args
        message = args[0]
        assert "version" in message

    show_about_action.on_unload()  # Doesn't do anything, used for coverage.
